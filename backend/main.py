import os
import json
import re
import time
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

from backend.enem_prompt import SYSTEM_PROMPT, CHAT_PROMPT

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="Corretor ENEM IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit simples em memória: 10 req/min por IP para /api/corrigir e /api/chat
RATE_LIMIT = 10
WINDOW_SEC = 60
_hits = defaultdict(deque)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/corrigir") or request.url.path.startswith("/api/chat"):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        q = _hits[ip]
        # remove antigos
        while q and q[0] < now - WINDOW_SEC:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return JSONResponse(status_code=429, content={"detail": f"Limite de {RATE_LIMIT} requisições por minuto atingido. Aguarde {int(q[0] + WINDOW_SEC - now)}s."})
        q.append(now)
    return await call_next(request)

# Configuração da IA - suporta OpenAI, Groq, Gemini (via OpenAI-compatible) ou Ollama local
# Defina no .env: OPENAI_API_KEY, OPENAI_BASE_URL (opcional), MODEL
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # ex: https://api.groq.com/openai/v1 para Groq
MODEL = os.getenv("MODEL", "gpt-4o-mini")

client = None
if API_KEY:
    kwargs = {"api_key": API_KEY}
    if BASE_URL:
        kwargs["base_url"] = BASE_URL
    client = OpenAI(**kwargs)

class RedacaoRequest(BaseModel):
    texto: str
    tema: str = ""

class ChatRequest(BaseModel):
    mensagem: str
    historico: list = []

def chamar_ia(system: str, user: str, json_mode: bool = False) -> str:
    if not client:
        raise HTTPException(status_code=500, detail="API_KEY não configurada. Crie um arquivo .env com OPENAI_API_KEY (veja .env.example). Você pode usar OpenAI, Groq (grátis) ou Gemini.")
    
    extra = {}
    if json_mode:
        extra["response_format"] = {"type": "json_object"}
    
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.3,
        max_tokens=2500,
        **extra
    )
    return resp.choices[0].message.content

def mock_correcao(texto: str):
    """Fallback para testes sem API key - retorna correção simulada"""
    palavras = len(texto.split())
    return {
        "nota_final": 720,
        "competencias": {
            "c1": {"nota": 120, "justificativa": "Presença de desvios gramaticais e de pontuação. Ex: falta de crase e vírgulas.", "erros": ["Exemplo: 'a sociedade' -> 'à sociedade' (crase)"]},
            "c2": {"nota": 160, "justificativa": "Compreende o tema mas repertório pouco produtivo. Faltou legitimação com dados/autor.", "erros": []},
            "c3": {"nota": 120, "justificativa": f"Texto com {palavras} palavras. Argumentação pouco desenvolvida, parágrafos desbalanceados.", "erros": []},
            "c4": {"nota": 120, "justificativa": "Repertório coesivo repetitivo (uso excessivo de 'além disso', 'portanto'). Faltam conectivos variados.", "erros": []},
            "c5": {"nota": 160, "justificativa": "Proposta presente mas incompleta. Falta detalhamento do meio ou efeito.", "elementos_presentes": ["Agente", "Ação", "Meio"]}
        },
        "comentario_geral": "MODO DEMO (sem API key). Redação na média nacional. Para correção real com IA, configure sua chave no arquivo .env. Sua estrutura está correta mas precisa refinar gramática, repertório e proposta completa.",
        "pontos_fortes": ["Estrutura dissertativa-argumentativa respeitada", "Tema compreendido"],
        "pontos_a_melhorar": ["Diversificar conectivos", "Aprofundar repertório com dados", "Completar os 5 elementos da C5"],
        "reescrita_trechos": [{"original": texto[:80]+"...", "sugestao": "Reescreva a introdução com tese + 2 argumentos + repertório legitimado", "motivo": "Tese pouco clara"}],
        "dica_para_nota_1000": "Estude propostas nota 1000 e memorize 5 conectivos coringas por parágrafo. Configure a API para correção real."
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL, "api_configurada": bool(API_KEY), "rate_limit": f"{RATE_LIMIT}/min"}

@app.get("/api/config")
def config():
    # endpoint para verificar deploy sem expor a key
    return {"model": MODEL, "base_url": BASE_URL or "https://api.openai.com/v1", "demo": not bool(API_KEY)}

@app.post("/api/corrigir")
def corrigir(req: RedacaoRequest):
    texto = req.texto.strip()
    if len(texto) < 50:
        raise HTTPException(status_code=400, detail="Redação muito curta. Envie pelo menos 5 linhas.")
    
    # Detecta se é tentativa de chat e não redação
    if len(texto.split()) < 40 and "?" in texto:
        # Trata como chat
        try:
            resposta = chamar_ia(CHAT_PROMPT, texto)
            return {"tipo": "chat", "resposta": resposta}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    tema_str = f"\nTEMA: {req.tema}" if req.tema else ""
    user_prompt = f"{tema_str}\n\nREDAÇÃO PARA CORRIGIR:\n{texto}\n\nCorrija rigorosamente no formato JSON especificado."

    # Se não tem API key, retorna mock para demonstração
    if not client:
        return {"tipo": "correcao", "resultado": mock_correcao(texto), "demo": True}

    try:
        raw = chamar_ia(SYSTEM_PROMPT, user_prompt, json_mode=True)
        # Extrai JSON mesmo se vier com markdown
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        resultado = json.loads(raw)
        return {"tipo": "correcao", "resultado": resultado, "demo": False}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Erro ao interpretar JSON da IA: {raw[:500]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat(req: ChatRequest):
    if not client:
        # Resposta demo sem IA
        respostas_demo = {
            "conectivo": "Use: 'Ademais', 'Outrossim', 'Depreende-se', 'Dessa forma', 'Por conseguinte', 'Em primeira análise', 'Em segunda análise'. Varie por parágrafo!",
            "estrutura": "Estrutura ENEM: 1) Introdução (contexto + tese + 2 argumentos), 2) D1 (argumento 1 + repertório), 3) D2 (argumento 2 + repertório), 4) Conclusão (Agente + Ação + Meio + Efeito + Detalhamento).",
            "default": "MODO DEMO: Configure sua API key no .env para chat com IA real. Enquanto isso, me pergunte sobre estrutura, conectivos, repertório ou C5!"
        }
        msg = req.mensagem.lower()
        if "conect" in msg:
            return {"resposta": respostas_demo["conectivo"], "demo": True}
        if "estrutura" in msg or "paragrafo" in msg:
            return {"resposta": respostas_demo["estrutura"], "demo": True}
        return {"resposta": respostas_demo["default"], "demo": True}

    try:
        historico_txt = "\n".join([f"{m['role']}: {m['content']}" for m in req.historico[-6:]])
        prompt = f"Histórico:\n{historico_txt}\n\nUsuário: {req.mensagem}"
        resposta = chamar_ia(CHAT_PROMPT, prompt)
        return {"resposta": resposta, "demo": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Servir frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

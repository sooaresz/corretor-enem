import os  # acesso a variáveis de ambiente e caminhos de arquivos
import json  # converte resposta da IA (texto JSON) em dict Python
import re  # extrai JSON mesmo se vier com markdown ```json
import time  # mede janela de tempo do rate limit
from collections import defaultdict, deque  # armazena timestamps por IP para rate limit
from fastapi import FastAPI, HTTPException, Request  # framework da API + erros HTTP + dados da requisição
from fastapi.middleware.cors import CORSMiddleware  # libera acesso do frontend (outra origem)
from fastapi.staticfiles import StaticFiles  # serve HTML/CSS/JS da pasta frontend
from fastapi.responses import JSONResponse  # resposta custom para erro 429 (rate limit)
from pydantic import BaseModel  # valida JSON de entrada (texto da redação)
from dotenv import load_dotenv  # lê arquivo .env com chaves da IA
from openai import OpenAI  # cliente compatível com OpenAI/Groq/Gemini

from backend.enem_prompt import SYSTEM_PROMPT, CHAT_PROMPT  # prompts que ensinam a IA a corrigir no padrão ENEM

# Carrega .env de 3 lugares possíveis (raiz, backend/.env, cwd) — garante que acha a key no Render e local
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Cria app FastAPI — titulo aparece em /docs (Swagger)
app = FastAPI(title="Corretor ENEM IA")

# CORS liberado — permite frontend em outro domínio (ex: Render) acessar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # * = qualquer origem pode chamar
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST etc
    allow_headers=["*"],
)

# --- RATE LIMIT: proteção contra abuso (10 correções por minuto por IP) ---
# Evita que alguém gaste sua cota Groq com flood
RATE_LIMIT = 10  # tamanho: 10 requisições
WINDOW_SEC = 60  # tamanho: janela de 60 segundos
_hits = defaultdict(deque)  # dict IP -> fila de timestamps

@app.middleware("http")  # executa em toda requisição antes de chegar no endpoint
async def rate_limit_middleware(request: Request, call_next):
    # Só limita /api/corrigir e /api/chat (health fica livre)
    if request.url.path.startswith("/api/corrigir") or request.url.path.startswith("/api/chat"):
        ip = request.client.host if request.client else "unknown"  # identifica usuário
        now = time.time()
        q = _hits[ip]
        # remove timestamps antigos (>60s)
        while q and q[0] < now - WINDOW_SEC:
            q.popleft()
        if len(q) >= RATE_LIMIT:  # estourou limite -> retorna 429
            return JSONResponse(status_code=429, content={"detail": f"Limite de {RATE_LIMIT} requisições por minuto atingido. Aguarde {int(q[0] + WINDOW_SEC - now)}s."})
        q.append(now)  # registra hit atual
    return await call_next(request)  # segue para o endpoint normal

# --- CONFIG DA IA: lê env vars (defina no .env ou no painel do Render) ---
API_KEY = os.getenv("OPENAI_API_KEY", "")  # tamanho: string com gsk_... (Groq) ou sk-... (OpenAI)
BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # tamanho: URL base, ex https://api.groq.com/openai/v1
MODEL = os.getenv("MODEL", "gpt-4o-mini")  # tamanho: nome do modelo, ex openai/gpt-oss-20b

# Inicializa cliente OpenAI/Groq com tratamento de erro (não derruba o servidor se key falhar)
client = None
client_init_error = None  # guarda erro para mostrar em /api/health
if API_KEY:
    try:
        kwargs = {"api_key": API_KEY.strip()}  # strip remove espaços que quebram no Render
        if BASE_URL:
            kwargs["base_url"] = BASE_URL.strip()
        client = OpenAI(**kwargs)
        print(f"[init] OpenAI client OK - model={MODEL} base_url={BASE_URL or 'default'}")
    except Exception as e:
        client_init_error = str(e)
        print(f"[init] OpenAI client FAILED: {e}")
        client = None
else:
    print("[init] No API_KEY -> modo DEMO")  # sem key cai no mock (nota 720 fixa)

# Modelos de entrada validados pelo Pydantic
class RedacaoRequest(BaseModel):
    texto: str  # tamanho: redação completa (mín 50 caracteres)
    tema: str = ""  # tamanho: tema opcional, ex "Desinformação nas redes"

class ChatRequest(BaseModel):
    mensagem: str  # tamanho: pergunta do aluno, ex "Como fazer C5?"
    historico: list = []  # tamanho: últimas mensagens para contexto

def chamar_ia(system: str, user: str, json_mode: bool = False) -> str:
    """Chama Groq/OpenAI com prompt de sistema + usuário. json_mode=True força JSON puro."""
    if not client:
        raise HTTPException(status_code=500, detail="API_KEY não configurada. Crie um arquivo .env com OPENAI_API_KEY (veja .env.example). Você pode usar OpenAI, Groq (grátis) ou Gemini.")
    
    extra = {}
    if json_mode:
        extra["response_format"] = {"type": "json_object"}  # tamanho: força JSON válido (sem texto extra)
    
    resp = client.chat.completions.create(
        model=MODEL,  # tamanho: modelo configurado no .env
        messages=[
            {"role": "system", "content": system},  # tamanho: instruções do corretor ENEM
            {"role": "user", "content": user}  # tamanho: redação + tema
        ],
        temperature=0.3,  # tamanho: 0.3 = mais determinístico/rigoroso (0=criativo, 1=variado)
        max_tokens=2500,  # tamanho: limite de tokens da resposta (cobre JSON completo)
        **extra
    )
    return resp.choices[0].message.content

def mock_correcao(texto: str):
    """Fallback DEMO: retorna nota simulada quando não há API key (para testar layout sem gastar cota)"""
    palavras = len(texto.split())  # tamanho: conta palavras para justificativa C3
    return {
        "nota_final": 720,  # tamanho: nota fixa demo
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

@app.get("/api/health")  # endpoint de saúde: frontend e Render verificam se API está OK
def health():
    return {"status": "ok", "model": MODEL, "api_configurada": bool(API_KEY) and client is not None, "client_error": client_init_error, "rate_limit": f"{RATE_LIMIT}/min"}

@app.get("/api/config")  # endpoint público sem expor a key, só mostra modelo e base_url
def config():
    return {"model": MODEL, "base_url": BASE_URL or "https://api.openai.com/v1", "demo": not bool(API_KEY)}

@app.post("/api/corrigir")  # endpoint principal: recebe redação, chama IA, retorna JSON C1-C5
def corrigir(req: RedacaoRequest):
    texto = req.texto.strip()
    if len(texto) < 50:  # tamanho mínimo: evita texto vazio/curto que a IA não consegue avaliar
        raise HTTPException(status_code=400, detail="Redação muito curta. Envie pelo menos 5 linhas.")
    
    # Se for pergunta curta com "?" (ex: "como fazer C5?"), trata como chat em vez de correção
    if len(texto.split()) < 40 and "?" in texto:
        try:
            resposta = chamar_ia(CHAT_PROMPT, texto)
            return {"tipo": "chat", "resposta": resposta}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    tema_str = f"\nTEMA: {req.tema}" if req.tema else ""  # inclui tema se enviado
    user_prompt = f"{tema_str}\n\nREDAÇÃO PARA CORRIGIR:\n{texto}\n\nCorrija rigorosamente no formato JSON especificado."

    if not client:  # sem key -> retorna mock demo (não chama IA)
        return {"tipo": "correcao", "resultado": mock_correcao(texto), "demo": True}

    try:
        raw = chamar_ia(SYSTEM_PROMPT, user_prompt, json_mode=True)  # chama IA em modo JSON
        # Extrai JSON mesmo se vier com ```json ... ``` (markdown)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        resultado = json.loads(raw)  # tamanho: JSON com c1-c5, nota_final, etc
        return {"tipo": "correcao", "resultado": resultado, "demo": False}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Erro ao interpretar JSON da IA: {raw[:500]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")  # endpoint de dúvidas: tira dúvidas sobre ENEM sem corrigir redação
def chat(req: ChatRequest):
    if not client:  # modo demo: respostas fixas sem IA
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
        historico_txt = "\n".join([f"{m['role']}: {m['content']}" for m in req.historico[-6:]])  # tamanho: últimas 6 msgs para contexto
        prompt = f"Histórico:\n{historico_txt}\n\nUsuário: {req.mensagem}"
        resposta = chamar_ia(CHAT_PROMPT, prompt)
        return {"resposta": resposta, "demo": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve o frontend (HTML/CSS/JS) na raiz "/" — quando acessa https://seusite.com abre o index.html
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")  # tamanho: pasta frontend ao lado de backend
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

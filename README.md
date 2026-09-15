# Corretor ENEM PRO — Chatbot IA

Chatbot que corrige redações modelo ENEM na régua oficial do INEP (C1-C5, 0-1000) + tira dúvidas por chat.

## Como rodar (2 minutos)

### 1. Instalar dependências
```powershell
cd C:\Users\seu_user\Documents\corretor-enem\backend
pip install -r requirements.txt
```

### 2. Configurar IA (escolha 1 opção)

Copie `.env.example` para `backend\.env` ou na raiz `.env`:

**Opção A - Groq (GRÁTIS e rápido - recomendado):**
1. Crie conta em https://console.groq.com/keys
2. Crie API Key
3. No `.env`:
```
OPENAI_API_KEY=gsk_...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
MODEL=llama-3.1-70b-versatile
```

**Opção B - OpenAI:**
```
OPENAI_API_KEY=sk-proj-...
MODEL=gpt-4o-mini
```

Sem API key o app roda em **MODO DEMO** (correção simulada).

### 3. Rodar
```powershell
uvicorn backend.main:app --reload --port 8000
# ou
python -m uvicorn backend.main:app --reload --port 8000
```
Acesse: http://localhost:8000

## O que ele faz
-  Nota por competência (C1-C5 em 0/40/80/120/160/200)
-  Nota final 0-1000
-  Erros gramaticais apontados
-  Análise de repertório, coesão e proposta de intervenção (5 elementos)
-  Reescrita de trechos
-  Dica para 1000
-  Chat para dúvidas (conectivos, estrutura, temas)

## Estrutura ENEM ensinada
Introdução (contextualização + tese + 2 argumentos) → D1 → D2 → Conclusão (Agente + Ação + Meio + Efeito + Detalhamento)

## Deploy
- Backend: Render, Railway, Fly.io (`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`)
- Frontend já é servido pelo FastAPI (pasta frontend)

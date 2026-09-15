# Deploy - Corretor ENEM para público

## Opção Render (recomendado, grátis)

1. Crie repo no GitHub:
   - Vá em https://github.com/new -> nome `corretor-enem` -> Create (sem README)
   - No PowerShell:
     ```powershell
     cd C:\Users\danra\Documents\corretor-enem
     git branch -M main
     git remote add origin https://github.com/SEU_USUARIO/corretor-enem.git
     git push -u origin main
     ```

2. Deploy no Render:
   - Acesse https://dashboard.render.com -> New + -> Web Service -> Connect seu repo `corretor-enem`
   - Render detecta `render.yaml` automaticamente. Se pedir manualmente:
     - Build: `pip install -r backend/requirements.txt`
     - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Em Environment -> Add:
     ```
     OPENAI_API_KEY = gsk_... (sua key Groq)
     OPENAI_BASE_URL = https://api.groq.com/openai/v1
     MODEL = openai/gpt-oss-20b
     ```
   - Create Web Service -> aguarde 2-3 min -> link: `https://corretor-enem.onrender.com`

3. Teste:
   ```
   https://corretor-enem.onrender.com/api/health -> {"api_configurada": true}
   ```

## Segurança já aplicada
- `.gitignore` bloqueia `.env` (verificado com `git check-ignore`)
- `render.yaml` usa `sync: false` para key não ir pro Git
- Rate limit 10/min por IP em `backend/main.py:25`
- `/api/config` não expõe a key

## Alternativa Railway/ Fly.io
Mesmo startCommand: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

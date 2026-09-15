const API = ""; // tamanho: string vazia = mesmo host (usa /api/corrigir no mesmo domínio, funciona local e Render)

// TROCA DE ABAS: alterna entre Corrigir e Tirar Dúvidas, tamanho: 2 abas
function switchTab(t){
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active')); // remove ativo de todas abas
  document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active')); // esconde todos conteúdos
  document.getElementById('tab-'+t).classList.add('active'); // mostra aba clicada
  event.target.classList.add('active'); // marca botão como ativo
}

// CONTADOR: conta palavras e linhas em tempo real, tamanho: atualiza a cada tecla
const ta = document.getElementById('redacao'); // tamanho: textarea 360px altura
const cont = document.getElementById('contador'); // tamanho: span 12px ao lado do label
ta.addEventListener('input', ()=>{
  const palavras = ta.value.trim() ? ta.value.trim().split(/\s+/).length : 0; // tamanho: split por espaços
  const linhas = ta.value ? ta.value.split('\n').length : 0; // tamanho: conta \n
  cont.textContent = `${palavras} palavras • ${linhas} linhas`;
});

// NOVA CORREÇÃO: limpa tema, redação e resultado sem recarregar página, tamanho: reseta 3 campos
function novaCorrecao(){
  document.getElementById('tema').value = ""; // tamanho: limpa input tema
  document.getElementById('redacao').value = ""; // tamanho: limpa textarea 360px
  document.getElementById('contador').textContent = "0 palavras • 0 linhas"; // tamanho: reseta contador 12px
  // restaura estado vazio original (🎯 + lista 20px)
  document.getElementById('resultado').innerHTML = `<div class="empty"><div class="empty-icon">🎯</div><h3>Sua correção aparecerá aqui</h3><p>Nota por competência (C1-C5), comentários, reescrita de trechos e dica para 1000.</p><ul><li>✅ C1: Gramática e norma culta</li><li>✅ C2: Tema e repertório</li><li>✅ C3: Argumentação</li><li>✅ C4: Coesão</li><li>✅ C5: Proposta de intervenção</li></ul></div>`;
  document.getElementById('redacao').focus(); // tamanho: foca no textarea para digitar nova
}

// EXEMPLO: carrega redação nota 1000 pronta, tamanho: tema + redação com 361 palavras aprox
function exemplo(){
  document.getElementById('tema').value = "Desafios para o enfrentamento da invisibilidade do trabalho de cuidado realizado pela mulher no Brasil";
  document.getElementById('redacao').value = `No filme "A Escolha Perfeita", é retratada a sobrecarga feminina ao conciliar carreira e afazeres domésticos. Fora da ficção, no Brasil, a invisibilidade do trabalho de cuidado realizado pela mulher é um desafio persistente, fruto da cultura patriarcal e da insuficiência de políticas públicas. Dessa forma, é imprescindível analisar as causas e propor medidas para mitigar o problema.

Em primeira análise, a cultura patriarcal enraizada na sociedade brasileira é um fator determinante. Segundo Simone de Beauvoir, "ninguém nasce mulher, torna-se mulher", evidenciando como papéis de gênero são socialmente construídos. Nesse sentido, desde a infância, meninas são ensinadas a cuidar, enquanto meninos são incentivados à vida pública. Consequentemente, naturaliza-se que o cuidado com crianças, idosos e lar seja responsabilidade feminina, trabalho não remunerado e desvalorizado, o que perpetua a desigualdade.

Ademais, a insuficiência de políticas públicas agrava a situação. De acordo com dados do IBGE, mulheres dedicam quase o dobro de horas semanais aos afazeres domésticos em relação aos homens. No entanto, o Estado não oferece creches em tempo integral, licenças parentais equitativas ou remuneração para cuidadoras. Assim, muitas mulheres abandonam o mercado de trabalho ou enfrentam dupla jornada exaustiva, sem reconhecimento social ou econômico.

Portanto, é necessário que o Ministério da Mulher, em conjunto com o Ministério do Trabalho, promova políticas de valorização do cuidado, por meio da ampliação de creches públicas integrais e da criação de auxílio financeiro para cuidadoras, a fim de reconhecer economicamente esse trabalho. Além disso, o Ministério da Educação deve implementar campanhas escolares sobre igualdade de gênero, com palestras e materiais didáticos, para desconstruir estereótipos desde a base. Assim, o Brasil poderá tornar visível e valorizado o essencial trabalho de cuidado feminino.`;
  ta.dispatchEvent(new Event('input')); // dispara contador após preencher
}

// CORRIGIR: envia redação para /api/corrigir, tamanho: POST JSON com texto+tema, espera JSON C1-C5
async function corrigir(){
  const texto = document.getElementById('redacao').value.trim(); // tamanho: texto mínimo 50 caracteres
  const tema = document.getElementById('tema').value.trim(); // tamanho: tema opcional
  if(texto.length < 50){ alert("Cole uma redação mais completa (mínimo 50 caracteres)"); return; }
  
  const btn = document.getElementById('btnCorrigir'); // tamanho: botão azul 15px
  const resDiv = document.getElementById('resultado'); // tamanho: painel direito 16px raio
  btn.disabled = true; btn.textContent = "Corrigindo..."; // tamanho: desativa botão durante chamada
  resDiv.innerHTML = '<div class="loader"></div><p style="text-align:center;color:#6b7280;font-size:13px">Analisando C1-C5 com IA...</p>'; // tamanho: loader 24px + texto 13px

  try{
    const r = await fetch('/api/corrigir', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({texto, tema})
    });
    const data = await r.json();
    if(!r.ok) throw new Error(data.detail || 'Erro');
    
    if(data.tipo === 'chat'){ // tamanho: se for pergunta curta, mostra como chat
      resDiv.innerHTML = `<div class="card"><h4>💬 Resposta</h4><p>${data.resposta.replace(/\n/g,'<br>')}</p></div>`;
    } else {
      renderResultado(data.resultado, data.demo); // tamanho: renderiza nota final + C1-C5
    }
  }catch(e){
    resDiv.innerHTML = `<div class="card" style="border:1px solid #fecaca;background:#fef2f2"><h4>❌ Erro</h4><p>${e.message}</p><p style="margin-top:8px;font-size:12px">Dica: Se for erro de API_KEY, crie o arquivo <b>backend/.env</b> a partir do .env.example</p></div>`;
  }finally{
    btn.disabled = false; btn.textContent = "⚡ Corrigir com IA";
  }
}

// RENDERIZA RESULTADO: monta HTML da nota final (42px), competencias (18px nota), cards 13px
function renderResultado(r, isDemo){
  const nivel = (n) => n>=160?'ok': n>=120?'media':'ruim'; // tamanho: define cor borda (verde/laranja/vermelho)
  const demoHtml = isDemo ? '<div class="demo-aviso">⚠️ Modo DEMO — sem API key. Configure o .env para correção real com IA (Groq é grátis).</div>' : '';
  
  let html = demoHtml;
  html += `<div class="nota-total"><div class="label">NOTA FINAL</div><div class="num">${r.nota_final}</div><div class="label">de 1000 pontos</div></div>`; // tamanho: num 42px
  
  html += '<div class="competencias">';
  const nomes = {c1:"C1 - Norma culta", c2:"C2 - Tema e repertório", c3:"C3 - Argumentação", c4:"C4 - Coesão", c5:"C5 - Intervenção"};
  for(let k of ['c1','c2','c3','c4','c5']){
    const c = r.competencias[k];
    html += `<div class="comp ${nivel(c.nota)}"><div><b>${nomes[k]}</b><br><span style="font-size:12px;color:#6b7280">${c.justificativa.slice(0,120)}...</span></div><div class="nota">${c.nota}</div></div>`; // tamanho: nota 18px à direita
  }
  html += '</div>';

  html += `<div class="card"><h4>📋 Comentário Geral</h4><p>${r.comentario_geral}</p></div>`;
  
  if(r.pontos_fortes) html += `<div class="card"><h4>✅ Pontos fortes</h4><ul>${r.pontos_fortes.map(p=>`<li>${p}</li>`).join('')}</ul></div>`;
  if(r.pontos_a_melhorar) html += `<div class="card"><h4>🎯 Pontos a melhorar</h4><ul>${r.pontos_a_melhorar.map(p=>`<li>${p}</li>`).join('')}</ul></div>`;
  
  if(r.reescrita_trechos) html += `<div class="card"><h4>✏️ Reescrita de trechos</h4>${r.reescrita_trechos.map(t=>`<div class="reescrita"><p><b>Original:</b> <i>"${t.original}"</i></p><p><b>Sugestão:</b> ${t.sugestao}</p><p style="font-size:12px;color:#6b7280">Motivo: ${t.motivo}</p></div>`).join('')}</div>`;
  
  if(r.dica_para_nota_1000) html += `<div class="card" style="background:#eff6ff;border:1px solid #bfdbfe"><h4>💡 Dica para 1000</h4><p>${r.dica_para_nota_1000}</p></div>`;

  // mostra JSON completo para debug, tamanho: pre 11px
  html += `<details style="margin-top:12px"><summary style="cursor:pointer;font-size:13px;font-weight:600">Ver JSON completo</summary><pre style="font-size:11px;background:#1f2937;color:#e5e7eb;padding:12px;border-radius:8px;overflow:auto;margin-top:8px">${JSON.stringify(r,null,2)}</pre></details>`;

  // adiciona botão Nova correção dentro do resultado também (facilita no celular), tamanho: botão ghost 12px
  html += `<button class="ghost" onclick="novaCorrecao()" style="width:100%;margin-top:12px">🔄 Nova correção</button>`;
  document.getElementById('resultado').innerHTML = html;
}

// CHAT: tira dúvidas sobre ENEM, tamanho: histórico últimos 6 msgs
let historico = [];
async function enviarChat(){
  const inp = document.getElementById('chatMsg'); // tamanho: input chat
  const txt = inp.value.trim();
  if(!txt) return;
  addMsg(txt, 'user'); // tamanho: msg azul 14px à direita
  historico.push({role:'user', content: txt});
  inp.value = "";
  
  const box = document.getElementById('chatBox'); // tamanho: box 420px altura
  const loading = document.createElement('div'); loading.className='msg bot'; loading.textContent='Digitando...'; loading.id='loading'; box.appendChild(loading); box.scrollTop=box.scrollHeight;

  try{
    const r = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mensagem: txt, historico})});
    const data = await r.json();
    document.getElementById('loading').remove();
    addMsg(data.resposta, 'bot'); // tamanho: msg cinza 14px à esquerda
    historico.push({role:'assistant', content: data.resposta});
  }catch(e){
    document.getElementById('loading')?.remove();
    addMsg("Erro: "+e.message, 'bot');
  }
}
function chatSugestao(t){ document.getElementById('chatMsg').value=t; enviarChat(); } // tamanho: botões pílula 12px
function addMsg(t, quem){
  const box = document.getElementById('chatBox');
  const d = document.createElement('div'); d.className='msg '+quem; d.innerHTML = t.replace(/\n/g,'<br>');
  box.appendChild(d); box.scrollTop=box.scrollHeight; // tamanho: auto-scroll para última msg
}

"""
Alex — Rotas FastAPI + Interface Web de Onboarding
"""

import uuid
import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

router = APIRouter()

# ══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.post("/api/v1/alex/iniciar")
async def alex_iniciar(request: Request):
    """Inicia ou retoma uma sessão de onboarding."""
    from nucleo.alex.agente import iniciar_conversa
    data = await request.json()
    tenant_id = data.get("tenant_id") or str(uuid.uuid4())
    resultado = await iniciar_conversa(tenant_id)
    return {"ok": True, "tenant_id": tenant_id, **resultado}


@router.post("/api/v1/alex/responder")
async def alex_responder(request: Request):
    """Processa uma resposta do usuário no diagnóstico."""
    from nucleo.alex.agente import processar_resposta
    data = await request.json()
    tenant_id = data.get("tenant_id", "")
    mensagem   = data.get("mensagem", "").strip()
    if not tenant_id or not mensagem:
        return JSONResponse({"ok": False, "erro": "tenant_id e mensagem são obrigatórios"}, status_code=400)
    resultado = await processar_resposta(tenant_id, mensagem)
    return {"ok": True, "tenant_id": tenant_id, **resultado}


@router.get("/api/v1/alex/sessao/{tenant_id}")
async def alex_sessao(tenant_id: str):
    """Retorna o estado atual da sessão de onboarding."""
    from nucleo.alex.agente import carregar_sessao
    sessao = carregar_sessao(tenant_id)
    return {"ok": True, "sessao": sessao}


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page():
    """Interface web do Agente Alex."""
    return HTMLResponse(ONBOARDING_HTML)


# ══════════════════════════════════════════════════════════════════
# INTERFACE HTML DO ALEX
# ══════════════════════════════════════════════════════════════════

ONBOARDING_HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nucleo Empreende — Setup com Alex</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #060910;
    --surface: #0c1018;
    --card: #101620;
    --border: #1c2a3a;
    --accent: #00d4a0;
    --accent2: #0088ff;
    --warn: #ff6b35;
    --text: #e4eaf2;
    --muted: #4a6070;
    --bubble-alex: #0f1e30;
    --bubble-user: #0d2b1f;
  }
  * { margin:0; padding:0; box-sizing:border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at 20% 50%, rgba(0,212,160,0.04) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 20%, rgba(0,136,255,0.04) 0%, transparent 60%);
    pointer-events: none;
  }

  /* Header */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.5rem;
    height: 60px;
    background: rgba(6,9,16,0.95);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 10;
  }
  .logo { display: flex; align-items: center; gap: 10px; }
  .logo-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px;
    display: grid; place-items: center;
    font-size: 16px;
  }
  .logo-text { font-weight: 800; font-size: 0.95rem; letter-spacing: -0.3px; }
  .logo-sub { font-size: 0.6rem; color: var(--muted); font-family: 'JetBrains Mono'; }

  .progress-wrap { display: flex; align-items: center; gap: 12px; }
  .progress-label { font-size: 0.7rem; color: var(--muted); font-family: 'JetBrains Mono'; }
  .progress-bar-track {
    width: 160px; height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 2px;
    transition: width 0.6s ease;
    width: 0%;
  }
  .progress-pct { font-size: 0.7rem; color: var(--accent); font-family: 'JetBrains Mono'; min-width: 30px; }

  /* Layout */
  .layout {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* Sidebar */
  .sidebar {
    width: 260px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    padding: 1.5rem 1rem;
    flex-shrink: 0;
    overflow-y: auto;
  }
  @media (max-width: 700px) { .sidebar { display: none; } }

  .sidebar-title {
    font-size: 0.6rem;
    font-family: 'JetBrains Mono';
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--muted);
    margin-bottom: 1rem;
  }
  .agent-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
    opacity: 0.35;
    transition: all 0.3s;
  }
  .agent-item.ativo { opacity: 1; background: rgba(0,212,160,0.08); }
  .agent-icon {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: var(--card);
    display: grid; place-items: center;
    font-size: 18px;
    flex-shrink: 0;
  }
  .agent-nome { font-size: 0.75rem; font-weight: 600; }
  .agent-cargo { font-size: 0.6rem; color: var(--muted); font-family: 'JetBrains Mono'; }
  .agent-status {
    font-size: 0.55rem;
    color: var(--accent);
    font-family: 'JetBrains Mono';
    margin-top: 2px;
  }

  /* Chat */
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    max-width: 780px;
    margin: 0 auto;
    width: 100%;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }

  .bubble {
    max-width: 82%;
    padding: 14px 18px;
    border-radius: 16px;
    font-size: 0.88rem;
    line-height: 1.6;
    animation: fadeUp 0.3s ease both;
    white-space: pre-wrap;
    word-break: break-word;
  }
  @keyframes fadeUp {
    from { opacity:0; transform:translateY(10px); }
    to   { opacity:1; transform:translateY(0); }
  }
  .bubble.alex {
    background: var(--bubble-alex);
    border: 1px solid var(--border);
    border-bottom-left-radius: 4px;
    align-self: flex-start;
  }
  .bubble.user {
    background: var(--bubble-user);
    border: 1px solid rgba(0,212,160,0.2);
    border-bottom-right-radius: 4px;
    align-self: flex-end;
    color: #c8f0e0;
  }

  .bubble-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .bubble-avatar {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    display: grid; place-items: center;
    font-size: 14px;
    flex-shrink: 0;
  }
  .bubble-name { font-size: 0.7rem; font-weight: 700; color: var(--accent); }

  /* Typing indicator */
  .typing {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 14px 18px;
    background: var(--bubble-alex);
    border: 1px solid var(--border);
    border-radius: 16px;
    border-bottom-left-radius: 4px;
    align-self: flex-start;
    display: none;
  }
  .typing.show { display: flex; }
  .typing-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent);
    animation: blink 1.2s infinite;
  }
  .typing-dot:nth-child(2) { animation-delay: 0.2s; }
  .typing-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink {
    0%,100% { opacity:0.3; transform:scale(0.8); }
    50%      { opacity:1;   transform:scale(1); }
  }

  /* Input */
  .input-area {
    padding: 1rem 1.5rem;
    background: rgba(6,9,16,0.95);
    border-top: 1px solid var(--border);
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }
  textarea {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 16px;
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 0.88rem;
    resize: none;
    outline: none;
    line-height: 1.5;
    max-height: 120px;
    transition: border-color 0.2s;
  }
  textarea:focus { border-color: rgba(0,212,160,0.4); }
  textarea::placeholder { color: var(--muted); }

  .send-btn {
    width: 44px; height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border: none;
    cursor: pointer;
    display: grid; place-items: center;
    font-size: 18px;
    transition: transform 0.1s, opacity 0.2s;
    flex-shrink: 0;
  }
  .send-btn:hover { transform: scale(1.05); }
  .send-btn:active { transform: scale(0.95); }
  .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  /* Conclusão */
  .concluido-badge {
    text-align: center;
    padding: 1rem;
    background: rgba(0,212,160,0.08);
    border: 1px solid rgba(0,212,160,0.3);
    border-radius: 12px;
    margin: 1rem;
    font-size: 0.8rem;
    color: var(--accent);
  }

  /* Bold parsing */
  .bold { font-weight: 700; }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">⬡</div>
    <div>
      <div class="logo-text">NUCLEO EMPREENDE</div>
      <div class="logo-sub">ONBOARDING COM ALEX</div>
    </div>
  </div>
  <div class="progress-wrap">
    <span class="progress-label">diagnóstico</span>
    <div class="progress-bar-track">
      <div class="progress-bar-fill" id="progress-bar"></div>
    </div>
    <span class="progress-pct" id="progress-pct">0%</span>
  </div>
</header>

<div class="layout">

  <!-- Sidebar: agentes que serão ativados -->
  <aside class="sidebar">
    <div class="sidebar-title">Sua Equipe de IA</div>

    <div class="agent-item" id="ag-lucas">
      <div class="agent-icon">👔</div>
      <div>
        <div class="agent-nome">Lucas</div>
        <div class="agent-cargo">CEO</div>
        <div class="agent-status" id="st-lucas">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-pedro">
      <div class="agent-icon">💰</div>
      <div>
        <div class="agent-nome">Pedro</div>
        <div class="agent-cargo">CFO</div>
        <div class="agent-status" id="st-pedro">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-mariana">
      <div class="agent-icon">📣</div>
      <div>
        <div class="agent-nome">Mariana</div>
        <div class="agent-cargo">CMO</div>
        <div class="agent-status" id="st-mariana">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-carla">
      <div class="agent-icon">⚙️</div>
      <div>
        <div class="agent-nome">Carla</div>
        <div class="agent-cargo">COO</div>
        <div class="agent-status" id="st-carla">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-rafael">
      <div class="agent-icon">🚀</div>
      <div>
        <div class="agent-nome">Rafael</div>
        <div class="agent-cargo">CPO</div>
        <div class="agent-status" id="st-rafael">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-diana">
      <div class="agent-icon">🔍</div>
      <div>
        <div class="agent-nome">Diana</div>
        <div class="agent-cargo">CNO</div>
        <div class="agent-status" id="st-diana">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-dani">
      <div class="agent-icon">📊</div>
      <div>
        <div class="agent-nome">Dani</div>
        <div class="agent-cargo">Dados</div>
        <div class="agent-status" id="st-dani">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-ze">
      <div class="agent-icon">🎯</div>
      <div>
        <div class="agent-nome">Zé</div>
        <div class="agent-cargo">Coach</div>
        <div class="agent-status" id="st-ze">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-beto">
      <div class="agent-icon">💡</div>
      <div>
        <div class="agent-nome">Beto</div>
        <div class="agent-cargo">Otimizador</div>
        <div class="agent-status" id="st-beto">aguardando...</div>
      </div>
    </div>
    <div class="agent-item" id="ag-ana">
      <div class="agent-icon">🧘</div>
      <div>
        <div class="agent-nome">Ana</div>
        <div class="agent-cargo">CHRO</div>
        <div class="agent-status" id="st-ana">aguardando...</div>
      </div>
    </div>
  </aside>

  <!-- Chat -->
  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="typing show" id="typing">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>

    <div class="input-area">
      <textarea
        id="input"
        placeholder="Digite sua resposta aqui..."
        rows="1"
        disabled
      ></textarea>
      <button class="send-btn" id="send-btn" disabled onclick="enviar()">➤</button>
    </div>
  </div>

</div>

<script>
// ── Estado ────────────────────────────────────────────────────────
let tenantId = localStorage.getItem('nucleo_tenant_id') || '';
let fase = 'diagnostico';
let enviando = false;

// ── Init ──────────────────────────────────────────────────────────
window.addEventListener('load', async () => {
  await iniciar();
  setupTextarea();
});

async function iniciar() {
  try {
    const body = tenantId ? {tenant_id: tenantId} : {};
    const r = await fetch('/api/v1/alex/iniciar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    const d = await r.json();
    tenantId = d.tenant_id;
    localStorage.setItem('nucleo_tenant_id', tenantId);

    document.getElementById('typing').classList.remove('show');
    adicionarBubble('alex', d.mensagem);
    setProgresso(d.progresso || 0);
    fase = d.fase || 'diagnostico';
    habilitarInput();

    if (fase === 'concluido') mostrarConcluido();
  } catch(e) {
    document.getElementById('typing').classList.remove('show');
    adicionarBubble('alex', '❌ Erro ao iniciar. Recarregue a página.');
  }
}

async function enviar() {
  const input = document.getElementById('input');
  const msg = input.value.trim();
  if (!msg || enviando) return;

  enviando = true;
  input.value = '';
  input.style.height = 'auto';
  adicionarBubble('user', msg);

  // Mostra typing
  const typing = document.getElementById('typing');
  typing.classList.add('show');
  scrollDown();

  try {
    const r = await fetch('/api/v1/alex/responder', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({tenant_id: tenantId, mensagem: msg})
    });
    const d = await r.json();

    typing.classList.remove('show');

    if (d.ok) {
      adicionarBubble('alex', d.mensagem);
      setProgresso(d.progresso || 0);
      fase = d.fase || fase;

      // Ativa agentes conforme progresso
      ativarAgentes(d.progresso || 0, fase);

      if (fase === 'concluido') {
        mostrarConcluido();
        document.getElementById('input').disabled = true;
        document.getElementById('send-btn').disabled = true;
      }
    } else {
      adicionarBubble('alex', '❌ Erro: ' + (d.erro || 'Tente novamente'));
    }
  } catch(e) {
    typing.classList.remove('show');
    adicionarBubble('alex', '❌ Erro de conexão. Tente novamente.');
  }

  enviando = false;
  scrollDown();
}

function adicionarBubble(tipo, texto) {
  const messages = document.getElementById('messages');
  const bubble = document.createElement('div');
  bubble.className = `bubble ${tipo}`;

  if (tipo === 'alex') {
    const header = document.createElement('div');
    header.className = 'bubble-header';
    header.innerHTML = '<div class="bubble-avatar">🤖</div><span class="bubble-name">ALEX · Consultor de IA</span>';
    bubble.appendChild(header);
  }

  const content = document.createElement('div');
  content.innerHTML = formatarTexto(texto);
  bubble.appendChild(content);

  const typing = document.getElementById('typing');
  messages.insertBefore(bubble, typing);
  scrollDown();
}

function formatarTexto(texto) {
  return texto
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n---\n/g, '<hr style="border-color:var(--border);margin:12px 0">')
    .replace(/\n/g, '<br>');
}

function setProgresso(pct) {
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-pct').textContent = pct + '%';
}

function ativarAgentes(progresso, fase) {
  const agentes = ['lucas','pedro','mariana','carla','rafael','diana','dani','ze','beto','ana'];

  if (fase === 'concluido') {
    agentes.forEach(a => {
      document.getElementById('ag-' + a).classList.add('ativo');
      document.getElementById('st-' + a).textContent = 'configurando...';
    });
    setTimeout(() => {
      agentes.forEach(a => {
        document.getElementById('st-' + a).textContent = '✅ ativo';
      });
    }, 3000);
    return;
  }

  // Ativa progressivamente conforme o diagnóstico avança
  const qtd = Math.floor((progresso / 100) * agentes.length);
  agentes.slice(0, qtd).forEach(a => {
    document.getElementById('ag-' + a).classList.add('ativo');
    document.getElementById('st-' + a).textContent = 'sendo configurado...';
  });
}

function mostrarConcluido() {
  const messages = document.getElementById('messages');
  const badge = document.createElement('div');
  badge.className = 'concluido-badge';
  badge.innerHTML = '✅ Onboarding concluído! Sua equipe está operacional. <a href="/mural" style="color:var(--accent)">Ver Mural →</a>';
  messages.appendChild(badge);
  ativarAgentes(100, 'concluido');
}

function habilitarInput() {
  document.getElementById('input').disabled = false;
  document.getElementById('send-btn').disabled = false;
  document.getElementById('input').focus();
}

function scrollDown() {
  const m = document.getElementById('messages');
  m.scrollTop = m.scrollHeight;
}

function setupTextarea() {
  const ta = document.getElementById('input');
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  });
  ta.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  });
}
</script>
</body>
</html>'''

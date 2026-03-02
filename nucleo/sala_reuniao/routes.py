"""
Sala de Reunião — Rotas FastAPI + WebSocket
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from .backend import criar_sala, obter_sala, injetar_no_whatsapp, salas_ativas, VOZES

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent

@router.post("/api/v1/sala/criar")
async def criar_sala_endpoint(request: Request):
    data = await request.json()
    tema    = data.get("tema", "Reunião estratégica")
    agentes = data.get("agentes", ["lucas", "diana", "pedro", "mariana"])
    # Garantir Lucas sempre presente como moderador
    if "lucas" not in agentes:
        agentes = ["lucas"] + agentes
    sala = criar_sala(tema, agentes)
    url  = f"/reuniao/{sala.id}"
    return {
        "ok": True,
        "sala_id": sala.id,
        "url": url,
        "tema": tema,
        "agentes": [{
            "id": a,
            "nome": VOZES[a]["nome"],
            "cargo": VOZES[a]["cargo"],
            "genero": VOZES[a]["genero"]
        } for a in agentes if a in VOZES]
    }

@router.post("/api/v1/sala/{sala_id}/iniciar")
async def iniciar_reuniao(sala_id: str):
    sala = obter_sala(sala_id)
    if not sala:
        return {"erro": "Sala não encontrada"}
    if sala.status != "aguardando":
        return {"erro": f"Sala está: {sala.status}"}
    asyncio.create_task(sala.conduzir_reuniao())
    return {"ok": True, "status": "iniciando"}

@router.post("/api/v1/sala/{sala_id}/mensagem")
async def mensagem_whatsapp(sala_id: str, request: Request):
    data = await request.json()
    msg  = data.get("mensagem", "")
    ok   = injetar_no_whatsapp(sala_id, msg)
    return {"ok": ok, "injetado": msg if ok else None}

@router.get("/api/v1/sala/{sala_id}/status")
async def status_sala(sala_id: str):
    sala = obter_sala(sala_id)
    if not sala:
        # Tentar carregar do arquivo
        f = BASE_DIR / "nucleo" / "data" / "salas" / f"{sala_id}.json"
        if f.exists():
            import json
            return json.loads(f.read_text())
        return {"erro": "Sala não encontrada"}
    return sala.to_dict()

@router.websocket("/ws/sala/{sala_id}")
async def websocket_sala(websocket: WebSocket, sala_id: str):
    await websocket.accept()
    sala = obter_sala(sala_id)
    if not sala:
        await websocket.send_text('{"erro":"Sala não encontrada"}')
        await websocket.close()
        return
    sala.ws_connections.add(websocket)
    # Enviar histórico existente para reconexões
    if sala.historico:
        import json
        await websocket.send_text(json.dumps({
            "tipo": "historico",
            "historico": sala.historico,
            "status": sala.status,
            "tema": sala.tema
        }))
    try:
        while True:
            await websocket.receive_text()  # mantém conexão viva
    except WebSocketDisconnect:
        sala.ws_connections.discard(websocket)

@router.get("/reuniao/{sala_id}", response_class=HTMLResponse)
async def pagina_sala(sala_id: str):
    """Página HTML da sala de reunião."""
    sala = obter_sala(sala_id)
    agentes_json = "[]"
    tema = "Reunião"
    if sala:
        import json
        agentes_info = [{
            "id": a,
            "nome": VOZES[a]["nome"],
            "cargo": VOZES[a]["cargo"],
            "genero": VOZES[a]["genero"]
        } for a in sala.agentes if a in VOZES]
        agentes_json = json.dumps(agentes_info)
        tema = sala.tema

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sala de Reunião — Nucleo Empreende</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0a0f;
    --surface: #12121a;
    --border: #1e1e2e;
    --gold: #c9a84c;
    --gold2: #f0d080;
    --text: #e8e8f0;
    --muted: #666680;
    --green: #4caf7d;
    --female: #e879a0;
    --male: #5b9cf6;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  /* Header */
  .header {{
    padding: 20px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, #0a0a0f 0%, #12101a 100%);
  }}
  .logo {{ font-family:'Playfair Display',serif; font-size:18px; color:var(--gold); }}
  .badge-live {{
    display: flex; align-items: center; gap: 8px;
    background: rgba(76,175,125,0.15);
    border: 1px solid var(--green);
    border-radius: 20px; padding: 4px 14px;
    font-size: 12px; color: var(--green);
  }}
  .dot-live {{
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--green);
    animation: pulse 1.5s infinite;
  }}
  @keyframes pulse {{
    0%,100% {{ opacity:1; transform:scale(1); }}
    50% {{ opacity:0.4; transform:scale(0.8); }}
  }}

  /* Tema */
  .tema-bar {{
    padding: 16px 24px;
    background: rgba(201,168,76,0.06);
    border-bottom: 1px solid var(--border);
    font-size: 13px; color: var(--muted);
  }}
  .tema-bar strong {{ color: var(--gold); font-size: 15px; }}

  /* Mesa */
  .mesa-container {{
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  .mesa-titulo {{
    font-size: 11px; letter-spacing: 2px;
    text-transform: uppercase; color: var(--muted);
    text-align: center;
  }}
  .mesa {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    padding: 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    position: relative;
  }}
  .mesa::before {{
    content: '';
    position: absolute;
    inset: 30px;
    border: 1px dashed var(--border);
    border-radius: 8px;
    pointer-events: none;
  }}

  /* Avatar */
  .avatar {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
    transition: all 0.3s;
    cursor: default;
    min-width: 70px;
    position: relative;
    z-index: 1;
  }}
  .avatar.falando {{
    background: rgba(201,168,76,0.12);
    border: 1px solid var(--gold);
    transform: scale(1.05);
  }}
  .avatar.aguardando {{ opacity: 0.5; }}
  .avatar-pic {{
    width: 52px; height: 52px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    border: 2px solid transparent;
    transition: border-color 0.3s;
    position: relative;
  }}
  .avatar.falando .avatar-pic {{
    border-color: var(--gold);
    box-shadow: 0 0 20px rgba(201,168,76,0.3);
  }}
  .avatar-pic.feminino {{ background: rgba(232,121,160,0.15); }}
  .avatar-pic.masculino {{ background: rgba(91,156,246,0.15); }}

  /* Ondas de voz */
  .voice-waves {{
    position: absolute;
    bottom: -4px;
    left: 50%;
    transform: translateX(-50%);
    display: flex; gap: 2px; align-items: flex-end;
    height: 12px; opacity: 0;
    transition: opacity 0.3s;
  }}
  .avatar.falando .voice-waves {{ opacity: 1; }}
  .wave-bar {{
    width: 3px; border-radius: 2px;
    background: var(--gold);
    animation: wave 0.8s infinite ease-in-out;
  }}
  .wave-bar:nth-child(1) {{ height: 5px; animation-delay: 0s; }}
  .wave-bar:nth-child(2) {{ height: 10px; animation-delay: 0.15s; }}
  .wave-bar:nth-child(3) {{ height: 7px; animation-delay: 0.3s; }}
  .wave-bar:nth-child(4) {{ height: 10px; animation-delay: 0.45s; }}
  .wave-bar:nth-child(5) {{ height: 5px; animation-delay: 0.6s; }}
  @keyframes wave {{
    0%,100% {{ transform: scaleY(1); }}
    50% {{ transform: scaleY(1.8); }}
  }}

  .avatar-nome {{ font-size: 11px; font-weight: 500; text-align: center; }}
  .avatar-cargo {{ font-size: 10px; color: var(--muted); }}

  /* Fala atual */
  .fala-atual {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin: 0 24px;
    min-height: 80px;
    transition: all 0.4s;
  }}
  .fala-nome {{
    font-size: 11px; color: var(--gold);
    letter-spacing: 1px; text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .fala-texto {{
    font-size: 15px; line-height: 1.6;
    color: var(--text);
  }}
  .fala-texto.digitando::after {{
    content: '▋';
    animation: blink 1s infinite;
  }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0}} }}

  /* Histórico */
  .historico {{
    margin: 0 24px;
    display: flex; flex-direction: column; gap: 8px;
    max-height: 300px; overflow-y: auto;
  }}
  .historico::-webkit-scrollbar {{ width: 4px; }}
  .historico::-webkit-scrollbar-track {{ background: var(--bg); }}
  .historico::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
  
  .hist-item {{
    display: flex; gap: 10px;
    padding: 10px 14px;
    background: var(--surface);
    border-radius: 8px;
    border: 1px solid var(--border);
    animation: slideIn 0.3s ease;
  }}
  @keyframes slideIn {{
    from {{ opacity:0; transform:translateY(8px); }}
    to {{ opacity:1; transform:translateY(0); }}
  }}
  .hist-cargo {{
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    white-space: nowrap;
    height: fit-content;
    margin-top: 2px;
  }}
  .hist-cargo.F {{ background: rgba(232,121,160,0.15); color: var(--female); }}
  .hist-cargo.M {{ background: rgba(91,156,246,0.15); color: var(--male); }}
  .hist-fala {{ font-size: 13px; line-height: 1.5; flex: 1; }}
  .hist-ts {{ font-size: 10px; color: var(--muted); white-space: nowrap; }}

  /* Decisão final */
  .decisao {{
    margin: 16px 24px;
    padding: 20px;
    background: linear-gradient(135deg, rgba(201,168,76,0.1), rgba(201,168,76,0.05));
    border: 1px solid var(--gold);
    border-radius: 12px;
    display: none;
  }}
  .decisao.visivel {{ display: block; animation: fadeIn 0.5s ease; }}
  @keyframes fadeIn {{ from{{opacity:0}} to{{opacity:1}} }}
  .decisao-titulo {{
    font-family: 'Playfair Display', serif;
    font-size: 14px; color: var(--gold);
    margin-bottom: 10px;
  }}
  .decisao-texto {{ font-size: 14px; line-height: 1.7; }}

  /* Chat externo */
  .chat-externo {{
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 12px 16px;
    display: flex; gap: 10px;
  }}
  .chat-input {{
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    outline: none;
  }}
  .chat-input:focus {{ border-color: var(--gold); }}
  .chat-btn {{
    background: var(--gold);
    color: var(--bg);
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
    cursor: pointer;
    font-size: 13px;
  }}
  .chat-btn:hover {{ background: var(--gold2); }}

  /* Status */
  .status-bar {{
    padding: 8px 24px;
    font-size: 11px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
  }}

  /* Padding bottom para o chat fixo */
  .pb {{ padding-bottom: 80px; }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">⬡ Nucleo Empreende</div>
  <div class="badge-live" id="badge">
    <div class="dot-live"></div>
    <span id="badge-text">Aguardando</span>
  </div>
  <button id="audio-btn" onclick="desbloquearAudio()" style="background:var(--gold);color:var(--bg);border:none;border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;">🔊 Ativar Áudio</button>
</div>

<div class="tema-bar">
  Pauta: <strong id="tema-display">{tema}</strong>
</div>

<div class="status-bar" id="status-bar">Conectando à sala...</div>

<div class="mesa-container">
  <div class="mesa-titulo">Mesa de Diretoria</div>
  <div class="mesa" id="mesa"></div>
</div>

<div class="fala-atual" id="fala-atual">
  <div class="fala-nome" id="fala-nome">—</div>
  <div class="fala-texto" id="fala-texto">Aguardando início da reunião...</div>
</div>

<div style="padding:12px 24px; font-size:11px; color:var(--muted); letter-spacing:1px; text-transform:uppercase;">
  Discussão
</div>

<div class="historico pb" id="historico"></div>

<div class="decisao" id="decisao">
  <div class="decisao-titulo">✦ Decisão Final do CEO</div>
  <div class="decisao-texto" id="decisao-texto"></div>
</div>

<div class="chat-externo">
  <input class="chat-input" id="chat-input" placeholder="Dar uma direção para a reunião..." />
  <button class="chat-btn" onclick="enviarDirecao()">Enviar</button>
</div>

<script>
const SALA_ID = "{sala_id}";
const agentes = {agentes_json};
let audioQueue = [];
let tocandoAudio = false;

// Renderizar mesa
const mesa = document.getElementById('mesa');
agentes.forEach(a => {{
  const emoji = a.genero === 'F' ? '👩' : '👨';
  mesa.innerHTML += `
    <div class="avatar aguardando" id="av-${{a.id}}">
      <div class="avatar-pic ${{a.genero === 'F' ? 'feminino' : 'masculino'}}">
        ${{emoji}}
        <div class="voice-waves">
          <div class="wave-bar"></div><div class="wave-bar"></div>
          <div class="wave-bar"></div><div class="wave-bar"></div>
          <div class="wave-bar"></div>
        </div>
      </div>
      <div class="avatar-nome">${{a.nome.split(' ')[0]}}</div>
      <div class="avatar-cargo">${{a.cargo}}</div>
    </div>`;
}});

// WebSocket
const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${{wsProto}}://${{location.host}}/ws/sala/${{SALA_ID}}`);
let audioDesbloqueado = false;
let audioCtx = null;

function desbloquearAudio() {{
  try {{
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    audioDesbloqueado = true;
    document.getElementById('audio-btn').innerHTML = '🔊 Áudio Ativo';
    document.getElementById('audio-btn').style.background = 'var(--green)';
    document.getElementById('status-bar').textContent = '🔊 Áudio ativado!';
    if (audioQueue.length > 0) tocarProximoAudio();
  }} catch(e) {{
    // fallback sem AudioContext
    audioDesbloqueado = true;
    if (audioQueue.length > 0) tocarProximoAudio();
  }}
}}

function tocarProximoAudio() {{
  if (audioQueue.length === 0) {{ tocandoAudio = false; return; }}
  if (!audioDesbloqueado) {{ tocandoAudio = false; return; }}
  tocandoAudio = true;
  const b64 = audioQueue.shift();
  const audio = new Audio();
  audio.src = 'data:audio/mpeg;base64,' + b64;
  audio.onended = tocarProximoAudio;
  audio.onerror = (e) => {{ console.log('Audio error:', e); tocarProximoAudio(); }};
  audio.play().catch(e => {{ console.log('Play failed:', e); tocarProximoAudio(); }});
}}

ws.onopen = () => {{
  document.getElementById('status-bar').textContent = 'Conectado. Aguardando início...';
  // Auto-iniciar reunião
  fetch(`/api/v1/sala/${{SALA_ID}}/iniciar`, {{method:'POST'}});
}};

ws.onmessage = (e) => {{
  const ev = JSON.parse(e.data);
  
  if (ev.tipo === 'inicio') {{
    document.getElementById('badge-text').textContent = 'AO VIVO';
    document.getElementById('status-bar').textContent = `Reunião iniciada — ${{ev.agentes?.length || ''}} participantes`;
  }}
  
  if (ev.tipo === 'fala') {{
    ativarAgente(ev.agente, ev.nome, ev.cargo, ev.texto, ev.audio, ev.ts);
  }}
  
  if (ev.tipo === 'historico') {{
    ev.historico.forEach(h => adicionarHistorico(h));
  }}
  
  if (ev.tipo === 'mensagem_cliente') {{
    document.getElementById('status-bar').textContent = ev.texto;
  }}
  
  if (ev.tipo === 'encerramento') {{
    document.getElementById('badge-text').textContent = 'Encerrada';
    document.getElementById('status-bar').textContent = 'Reunião encerrada';
    document.getElementById('fala-texto').classList.remove('digitando');
    if (ev.decisao) {{
      document.getElementById('decisao-texto').textContent = ev.decisao;
      document.getElementById('decisao').classList.add('visivel');
    }}
    // Desativar todos avatares
    agentes.forEach(a => {{
      const av = document.getElementById(`av-${{a.id}}`);
      if (av) {{ av.className = 'avatar aguardando'; }}
    }});
  }}
}};

ws.onerror = () => {{
  document.getElementById('status-bar').textContent = 'Erro de conexão. Tentando reconectar...';
}};

function ativarAgente(id, nome, cargo, texto, audio, ts) {{
  // Desativar todos
  agentes.forEach(a => {{
    const av = document.getElementById(`av-${{a.id}}`);
    if (av) av.className = 'avatar aguardando';
  }});
  
  // Ativar este
  const av = document.getElementById(`av-${{id}}`);
  if (av) av.className = 'avatar falando';
  
  // Atualizar fala atual
  document.getElementById('fala-nome').textContent = `${{nome}} — ${{cargo}}`;
  const ft = document.getElementById('fala-texto');
  ft.textContent = texto;
  ft.classList.add('digitando');
  setTimeout(() => ft.classList.remove('digitando'), 3000);
  
  // Adicionar ao histórico
  adicionarHistorico({{agente:id, nome, cargo, genero: agentes.find(a=>a.id===id)?.genero||'M', fala:texto, ts}});
  
  // Reproduzir áudio
  if (audio) {{
    audioQueue.push(audio);
    if (!tocandoAudio && audioDesbloqueado) tocarProximoAudio();
  }}
}}

function adicionarHistorico(h) {{
  const hist = document.getElementById('historico');
  const div = document.createElement('div');
  div.className = 'hist-item';
  div.innerHTML = `
    <div class="hist-cargo ${{h.genero || 'M'}}">${{h.cargo}}</div>
    <div class="hist-fala"><strong>${{h.nome?.split(' ')[0] || h.agente}}:</strong> ${{h.fala}}</div>
    <div class="hist-ts">${{h.ts || ''}}</div>`;
  hist.appendChild(div);
  hist.scrollTop = hist.scrollHeight;
}}

function enviarDirecao() {{
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  fetch(`/api/v1/sala/${{SALA_ID}}/mensagem`, {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{mensagem: msg}})
  }});
  input.value = '';
  document.getElementById('status-bar').textContent = `Sua direção foi enviada: "${{msg}}"`;
}}

document.getElementById('chat-input').addEventListener('keydown', e => {{
  if (e.key === 'Enter') enviarDirecao();
}});
</script>
</body>
</html>"""
    return HTMLResponse(html)

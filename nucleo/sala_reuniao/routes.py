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
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Sala Executiva — Nucleo Empreende</title>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&family=Exo+2:wght@200;300;400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #060810;
  --surface: #0d1117;
  --neon: #00e5ff;
  --neon2: #00b8d4;
  --neon-glow: rgba(0,229,255,0.15);
  --neon-strong: rgba(0,229,255,0.4);
  --gold: #ffd54f;
  --text: #cdd6f4;
  --muted: #45475a;
  --dim: rgba(6,8,16,0.7);
  --female-color: #f48fb1;
  --male-color: #80cbc4;
  --radius: 50%;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ height:100%; overflow:hidden; background:var(--bg); color:var(--text); font-family:'Exo 2', sans-serif; }}

/* Starfield background */
body::before {{
  content:'';
  position:fixed; inset:0;
  background: 
    radial-gradient(ellipse at 20% 50%, rgba(0,229,255,0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(100,50,255,0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 100%, rgba(0,229,255,0.02) 0%, transparent 40%);
  pointer-events:none; z-index:0;
}}

/* Grid lines */
body::after {{
  content:'';
  position:fixed; inset:0;
  background-image: 
    linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events:none; z-index:0;
}}

/* ── HEADER ── */
.header {{
  position:relative; z-index:10;
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 20px;
  border-bottom: 1px solid rgba(0,229,255,0.1);
  background: rgba(6,8,16,0.9);
  backdrop-filter: blur(10px);
}}
.logo {{
  font-family:'Rajdhani',sans-serif;
  font-size:16px; font-weight:600;
  color:var(--neon); letter-spacing:3px; text-transform:uppercase;
  display:flex; align-items:center; gap:8px;
}}
.logo-icon {{ width:20px; height:20px; position:relative; }}
.logo-icon::before, .logo-icon::after {{
  content:''; position:absolute;
  border: 1px solid var(--neon);
  border-radius:50%;
  animation: rotate 4s linear infinite;
}}
.logo-icon::before {{ inset:0; }}
.logo-icon::after {{ inset:4px; animation-direction:reverse; opacity:0.5; }}
@keyframes rotate {{ to {{ transform:rotate(360deg); }} }}

.badge-live {{
  display:flex; align-items:center; gap:6px;
  padding:5px 12px; border-radius:2px;
  border: 1px solid var(--neon);
  background: rgba(0,229,255,0.05);
  font-family:'Rajdhani',sans-serif;
  font-size:11px; letter-spacing:2px; color:var(--neon);
}}
.dot {{ width:6px; height:6px; border-radius:50%; background:var(--neon); }}
.dot.pulse {{ animation: dotpulse 1.2s ease-in-out infinite; }}
@keyframes dotpulse {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:0.3;transform:scale(0.7)}} }}

.btn-audio {{
  padding:6px 14px; border-radius:2px;
  border: 1px solid var(--gold);
  background: rgba(255,213,79,0.08);
  color:var(--gold); font-family:'Rajdhani',sans-serif;
  font-size:11px; letter-spacing:2px; cursor:pointer;
  transition: all 0.2s;
}}
.btn-audio:hover {{ background:rgba(255,213,79,0.15); }}
.btn-audio.active {{ border-color:var(--neon); color:var(--neon); background:rgba(0,229,255,0.08); }}

/* ── TEMA ── */
.tema-bar {{
  position:relative; z-index:10;
  padding:10px 20px;
  background: rgba(0,229,255,0.03);
  border-bottom: 1px solid rgba(0,229,255,0.08);
  font-size:12px; color:var(--muted); letter-spacing:1px;
}}
.tema-bar strong {{ color:var(--text); font-weight:400; }}

/* ── ARENA (círculo) ── */
.arena {{
  position:relative; z-index:5;
  flex:1;
  display:flex; align-items:center; justify-content:center;
}}
.arena-inner {{
  position:relative;
  width: min(70vw, 380px);
  height: min(70vw, 380px);
}}

/* Mesa central */
.mesa-center {{
  position:absolute;
  inset:25%;
  border-radius:50%;
  background: radial-gradient(circle, rgba(0,229,255,0.04) 0%, transparent 70%);
  border: 1px solid rgba(0,229,255,0.08);
  display:flex; align-items:center; justify-content:center;
  flex-direction:column; gap:4px;
}}
.mesa-label {{
  font-family:'Rajdhani',sans-serif;
  font-size:9px; letter-spacing:3px; color:rgba(0,229,255,0.3);
  text-transform:uppercase;
}}
.mesa-logo {{
  font-family:'Rajdhani',sans-serif;
  font-size:11px; letter-spacing:2px; color:rgba(0,229,255,0.2);
}}

/* Orbit ring */
.orbit-ring {{
  position:absolute; inset:0;
  border-radius:50%;
  border: 1px dashed rgba(0,229,255,0.06);
}}
.orbit-ring-2 {{
  position:absolute; inset:-8%;
  border-radius:50%;
  border: 1px solid rgba(0,229,255,0.04);
}}

/* Linha de conexão (SVG) */
.connection-svg {{
  position:absolute; inset:0;
  width:100%; height:100%;
  pointer-events:none;
}}
.beam {{
  stroke:var(--neon);
  stroke-width:1;
  stroke-dasharray:4 4;
  fill:none;
  opacity:0;
  animation: beamanim 0.6s ease forwards;
}}
@keyframes beamanim {{
  from {{ opacity:0; stroke-dashoffset:20; }}
  to   {{ opacity:0.4; stroke-dashoffset:0; }}
}}

/* Avatar no círculo */
.avatar-node {{
  position:absolute;
  display:flex; flex-direction:column; align-items:center; gap:5px;
  transform:translate(-50%, -50%);
  transition: all 0.4s cubic-bezier(0.34,1.56,0.64,1);
  cursor:default;
}}
.avatar-ring {{
  width:64px; height:64px;
  border-radius:50%;
  position:relative;
  transition: all 0.4s;
}}
.avatar-ring::before {{
  content:'';
  position:absolute; inset:-3px;
  border-radius:50%;
  border: 2px solid transparent;
  transition: all 0.4s;
}}
.avatar-ring::after {{
  content:'';
  position:absolute; inset:-8px;
  border-radius:50%;
  border: 1px solid transparent;
  transition: all 0.4s;
}}
.avatar-pic {{
  width:64px; height:64px;
  border-radius:50%;
  background: var(--surface);
  border: 2px solid rgba(255,255,255,0.05);
  display:flex; align-items:center; justify-content:center;
  font-size:28px;
  overflow:hidden;
  transition: all 0.4s;
  position:relative; z-index:2;
}}
.avatar-pic.F {{ background: radial-gradient(135deg, #1a0a14 0%, #0d0a14 100%); }}
.avatar-pic.M {{ background: radial-gradient(135deg, #0a1214 0%, #0a0d14 100%); }}

.avatar-info {{ text-align:center; }}
.avatar-nome {{
  font-family:'Rajdhani',sans-serif;
  font-size:11px; font-weight:600; letter-spacing:1px;
  color:var(--muted);
  transition: color 0.3s;
  white-space:nowrap;
}}
.avatar-cargo {{
  font-size:9px; letter-spacing:2px; color:rgba(100,100,120,0.6);
  text-transform:uppercase;
  transition: color 0.3s;
}}

/* Estado: aguardando */
.avatar-node.aguardando {{ opacity:0.35; transform:translate(-50%,-50%) scale(0.92); }}

/* Estado: falando */
.avatar-node.falando {{ opacity:1; transform:translate(-50%,-50%) scale(1.1); z-index:10; }}
.avatar-node.falando .avatar-ring::before {{
  border-color:var(--neon);
  box-shadow: 0 0 20px var(--neon-strong), inset 0 0 10px rgba(0,229,255,0.1);
  animation: ringpulse 1.5s ease-in-out infinite;
}}
.avatar-node.falando .avatar-ring::after {{
  border-color:rgba(0,229,255,0.2);
  animation: ringpulse2 2s ease-in-out infinite;
}}
.avatar-node.falando.F .avatar-ring::before {{ border-color:var(--female-color); box-shadow: 0 0 20px rgba(244,143,177,0.4); }}
.avatar-node.falando.F .avatar-ring::after {{ border-color:rgba(244,143,177,0.2); }}
.avatar-node.falando .avatar-nome {{ color:var(--neon); }}
.avatar-node.falando.F .avatar-nome {{ color:var(--female-color); }}
.avatar-node.falando .avatar-cargo {{ color:rgba(0,229,255,0.5); letter-spacing:3px; }}
@keyframes ringpulse {{
  0%,100%{{box-shadow:0 0 15px var(--neon-strong),inset 0 0 8px rgba(0,229,255,0.1)}}
  50%{{box-shadow:0 0 35px var(--neon-strong),0 0 60px rgba(0,229,255,0.1),inset 0 0 15px rgba(0,229,255,0.15)}}
}}
@keyframes ringpulse2 {{
  0%,100%{{transform:scale(1);opacity:1}} 50%{{transform:scale(1.1);opacity:0.4}}
}}

/* Ondas de voz */
.voz-waves {{
  position:absolute; bottom:-16px; left:50%; transform:translateX(-50%);
  display:flex; gap:2px; align-items:flex-end; height:14px;
  opacity:0; transition:opacity 0.3s;
}}
.avatar-node.falando .voz-waves {{ opacity:1; }}
.voz-bar {{
  width:3px; border-radius:2px;
  background:var(--neon);
  animation:voicewave 0.7s ease-in-out infinite;
}}
.avatar-node.falando.F .voz-bar {{ background:var(--female-color); }}
.voz-bar:nth-child(1){{height:4px;animation-delay:0s}}
.voz-bar:nth-child(2){{height:10px;animation-delay:.1s}}
.voz-bar:nth-child(3){{height:7px;animation-delay:.2s}}
.voz-bar:nth-child(4){{height:12px;animation-delay:.05s}}
.voz-bar:nth-child(5){{height:5px;animation-delay:.15s}}
@keyframes voicewave{{0%,100%{{transform:scaleY(1)}}50%{{transform:scaleY(1.8)}}

/* ── FALA ATUAL ── */
.fala-panel {{
  position:relative; z-index:10;
  margin:0 16px;
  padding:14px 16px;
  background: rgba(13,17,23,0.95);
  border: 1px solid rgba(0,229,255,0.1);
  border-left: 2px solid var(--neon);
  border-radius:0 4px 4px 0;
  min-height:70px;
  backdrop-filter:blur(10px);
}}
.fala-panel.F {{ border-left-color:var(--female-color); }}
.fala-speaker {{
  font-family:'Rajdhani',sans-serif;
  font-size:10px; letter-spacing:3px; text-transform:uppercase;
  color:var(--neon); margin-bottom:8px;
}}
.fala-panel.F .fala-speaker {{ color:var(--female-color); }}
.fala-texto {{
  font-size:14px; line-height:1.6; color:var(--text); font-weight:300;
}}
.cursor {{ display:inline-block; width:2px; height:14px; background:var(--neon); margin-left:2px; vertical-align:middle; animation:blink 1s infinite; }}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}

/* ── STATUS ── */
.status-line {{
  position:relative; z-index:10;
  padding:6px 16px;
  font-size:10px; letter-spacing:2px; color:var(--muted);
  text-transform:uppercase;
  border-top:1px solid rgba(0,229,255,0.05);
}}

/* ── HISTÓRICO ── */
.hist-container {{
  position:relative; z-index:10;
  overflow-y:auto;
  padding:8px 16px;
  flex:1;
  max-height:140px;
}}
.hist-container::-webkit-scrollbar{{width:2px}}
.hist-container::-webkit-scrollbar-thumb{{background:rgba(0,229,255,0.2);border-radius:1px}}
.hist-item {{
  display:flex; gap:8px; align-items:flex-start;
  padding:6px 10px; margin-bottom:4px;
  background:rgba(13,17,23,0.6);
  border: 1px solid rgba(0,229,255,0.05);
  border-radius:2px;
  animation:slidein 0.3s ease;
}}
@keyframes slidein{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:translateY(0)}}
.hist-badge {{
  font-family:'Rajdhani',sans-serif;
  font-size:9px; letter-spacing:1px;
  padding:2px 6px; border-radius:1px;
  white-space:nowrap; flex-shrink:0;
  margin-top:1px;
}}
.hist-badge.M{{background:rgba(128,203,196,0.1);color:var(--male-color);border:1px solid rgba(128,203,196,0.2)}}
.hist-badge.F{{background:rgba(244,143,177,0.1);color:var(--female-color);border:1px solid rgba(244,143,177,0.2)}}
.hist-fala{{font-size:12px;color:rgba(205,214,244,0.7);font-weight:300;flex:1;line-height:1.4}}
.hist-ts{{font-size:9px;color:var(--muted);white-space:nowrap}}

/* ── DECISÃO ── */
.decisao-panel {{
  display:none;
  margin:8px 16px;
  padding:14px 16px;
  background:rgba(255,213,79,0.04);
  border:1px solid rgba(255,213,79,0.3);
  border-radius:2px;
  animation:fadein 0.6s ease;
}}
.decisao-panel.show{{display:block}}
@keyframes fadein{{from{{opacity:0}}to{{opacity:1}}
.decisao-title {{
  font-family:'Rajdhani',sans-serif;
  font-size:11px; letter-spacing:3px; color:var(--gold);
  text-transform:uppercase; margin-bottom:8px;
}}
.decisao-texto{{font-size:13px;line-height:1.6;font-weight:300}}

/* ── CHAT INPUT ── */
.chat-bar {{
  position:relative; z-index:10;
  display:flex; gap:8px; padding:10px 16px;
  background:rgba(6,8,16,0.95);
  border-top:1px solid rgba(0,229,255,0.08);
  backdrop-filter:blur(10px);
}}
.chat-input {{
  flex:1; background:rgba(13,17,23,0.8);
  border:1px solid rgba(0,229,255,0.12);
  border-radius:2px; padding:9px 14px;
  color:var(--text); font-family:'Exo 2',sans-serif; font-size:12px;
  outline:none; letter-spacing:0.5px;
  transition:border-color 0.2s;
}}
.chat-input:focus{{border-color:rgba(0,229,255,0.4)}}
.chat-input::placeholder{{color:var(--muted);font-size:11px;letter-spacing:1px}}
.chat-send {{
  background:rgba(0,229,255,0.1);
  border:1px solid rgba(0,229,255,0.3);
  border-radius:2px; padding:9px 16px;
  color:var(--neon); font-family:'Rajdhani',sans-serif;
  font-size:11px; letter-spacing:2px; cursor:pointer;
  transition:all 0.2s;
}}
.chat-send:hover{{background:rgba(0,229,255,0.2);border-color:var(--neon)}}

/* Layout flex vertical */
.page {{ display:flex; flex-direction:column; height:100vh; }}
.arena-wrap {{ flex:0 0 auto; display:flex; justify-content:center; align-items:center; padding:12px 0; }}
</style>
</head>
<body>
<div class="page">

<!-- HEADER -->
<div class="header">
  <div class="logo">
    <div class="logo-icon"></div>
    NUCLEO
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <div class="badge-live">
      <div class="dot pulse" id="dot-live"></div>
      <span id="badge-txt">STANDBY</span>
    </div>
    <button class="btn-audio" id="btn-audio" onclick="ativarAudio()">⬡ ATIVAR</button>
  </div>
</div>

<!-- TEMA -->
<div class="tema-bar">
  <span style="letter-spacing:2px;font-size:10px">PAUTA</span> &nbsp;
  <strong id="tema-txt">{tema}</strong>
</div>

<!-- ARENA CIRCULAR -->
<div class="arena-wrap">
  <div class="arena-inner" id="arena">
    <div class="orbit-ring-2"></div>
    <div class="orbit-ring"></div>
    <div class="mesa-center">
      <div class="mesa-label">SALA</div>
      <div class="mesa-logo">⬡ NE</div>
    </div>
    <!-- SVG para linhas de conexão -->
    <svg class="connection-svg" id="conn-svg" viewBox="0 0 380 380"></svg>
    <!-- Avatares serão inseridos via JS -->
  </div>
</div>

<!-- FALA ATUAL -->
<div class="fala-panel" id="fala-panel">
  <div class="fala-speaker" id="fala-speaker">—</div>
  <div class="fala-texto" id="fala-texto">Aguardando início<span class="cursor" id="cursor"></span></div>
</div>

<!-- STATUS -->
<div class="status-line" id="status-line">CONECTANDO...</div>

<!-- HISTÓRICO -->
<div class="hist-container" id="historico"></div>

<!-- DECISÃO -->
<div class="decisao-panel" id="decisao-panel">
  <div class="decisao-title">⬡ DECISÃO EXECUTIVA</div>
  <div class="decisao-texto" id="decisao-texto"></div>
</div>

<!-- CHAT -->
<div class="chat-bar">
  <input class="chat-input" id="chat-input" placeholder="DIREÇÃO PARA A REUNIÃO..." />
  <button class="chat-send" onclick="enviarDirecao()">ENVIAR</button>
</div>

</div><!-- /page -->

<script>
const SALA_ID = "{sala_id}";
const AGENTES = {agentes_json};

let audioDesbloqueado = false;
let audioCtx = null;
let audioQueue = [];
let tocandoAudio = false;

// ── Posicionar avatares em círculo ──────────────────────────────
function posicionarAvatares() {{
  const arena = document.getElementById('arena');
  const n = AGENTES.length;
  const cx = 50, cy = 50, r = 38; // % do container

  AGENTES.forEach((ag, i) => {{
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);

    const node = document.createElement('div');
    node.className = `avatar-node aguardando ${{ag.genero}}`;
    node.id = `av-${{ag.id}}`;
    node.style.left = `${{x}}%`;
    node.style.top = `${{y}}%`;

    const emoji = ag.genero === 'F' ? '👩‍💼' : '👨‍💼';
    node.innerHTML = `
      <div class="avatar-ring">
        <div class="avatar-pic ${{ag.genero}}">${{emoji}}
          <div class="voz-waves">
            <div class="voz-bar"></div><div class="voz-bar"></div>
            <div class="voz-bar"></div><div class="voz-bar"></div>
            <div class="voz-bar"></div>
          </div>
        </div>
      </div>
      <div class="avatar-info">
        <div class="avatar-nome">${{ag.nome.split(' ')[0].toUpperCase()}}</div>
        <div class="avatar-cargo">${{ag.cargo}}</div>
      </div>`;
    arena.appendChild(node);
  }});
}}

// ── Linha de conexão entre quem fala e o centro ─────────────────
function desenharBeam(agenteId) {{
  const svg = document.getElementById('conn-svg');
  svg.innerHTML = '';
  const node = document.getElementById(`av-${{agenteId}}`);
  if (!node) return;

  const arena = document.getElementById('arena');
  const aRect = arena.getBoundingClientRect();
  const nRect = node.getBoundingClientRect();

  const cx = (aRect.width / 2);
  const cy = (aRect.height / 2);
  const nx = nRect.left - aRect.left + nRect.width / 2;
  const ny = nRect.top - aRect.top + nRect.height / 2;

  const scale = 380 / aRect.width;
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  line.setAttribute('class', 'beam');
  line.setAttribute('x1', nx * scale);
  line.setAttribute('y1', ny * scale);
  line.setAttribute('x2', cx * scale);
  line.setAttribute('y2', cy * scale);
  svg.appendChild(line);
}}

// ── Ativar agente falando ────────────────────────────────────────
function ativarAgente(id, nome, cargo, genero, texto, audio, ts) {{
  // Desativar todos
  AGENTES.forEach(a => {{
    const av = document.getElementById(`av-${{a.id}}`);
    if (av) av.className = `avatar-node aguardando ${{a.genero}}`;
  }});
  // Ativar este
  const av = document.getElementById(`av-${{id}}`);
  if (av) av.className = `avatar-node falando ${{genero}}`;

  desenharBeam(id);

  // Fala panel
  const panel = document.getElementById('fala-panel');
  panel.className = `fala-panel ${{genero}}`;
  document.getElementById('fala-speaker').textContent = `${{nome.toUpperCase()}} — ${{cargo}}`;
  document.getElementById('fala-texto').innerHTML = texto + '<span class="cursor" id="cursor"></span>';
  setTimeout(() => {{
    const c = document.getElementById('cursor');
    if (c) c.remove();
  }}, 4000);

  adicionarHistorico({{agente:id, nome, cargo, genero, fala:texto, ts}});

  if (audio) {{
    audioQueue.push(audio);
    if (audioDesbloqueado && !tocandoAudio) tocarProximo();
  }}
}}

// ── Histórico ────────────────────────────────────────────────────
function adicionarHistorico(h) {{
  const el = document.getElementById('historico');
  const div = document.createElement('div');
  div.className = 'hist-item';
  div.innerHTML = `
    <div class="hist-badge ${{h.genero}}">${{h.cargo}}</div>
    <div class="hist-fala"><strong>${{h.nome.split(' ')[0]}}:</strong> ${{h.fala}}</div>
    <div class="hist-ts">${{h.ts||''}}</div>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}}

// ── Audio ────────────────────────────────────────────────────────
function ativarAudio() {{
  try {{
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
  }} catch(e) {{}}
  audioDesbloqueado = true;
  const btn = document.getElementById('btn-audio');
  btn.textContent = '✓ AO VIVO';
  btn.className = 'btn-audio active';
  btn.disabled = true;
  document.getElementById('status-line').textContent = '▶ INICIANDO REUNIÃO...';
  document.getElementById('badge-txt').textContent = 'AO VIVO';
  fetch(`/api/v1/sala/${{SALA_ID}}/iniciar`, {{method:'POST'}})
    .then(() => setTimeout(() => {{ if (audioQueue.length > 0 && !tocandoAudio) tocarProximo(); }}, 500));
}}

function tocarProximo() {{
  if (!audioDesbloqueado || audioQueue.length === 0) {{ tocandoAudio = false; return; }}
  tocandoAudio = true;
  const b64 = audioQueue.shift();
  const audio = new Audio('data:audio/mpeg;base64,' + b64);
  audio.onended = tocarProximo;
  audio.onerror = tocarProximo;
  audio.play().catch(tocarProximo);
}}

// ── WebSocket ────────────────────────────────────────────────────
const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${{wsProto}}://${{location.host}}/ws/sala/${{SALA_ID}}`);

ws.onopen = () => {{
  document.getElementById('status-line').textContent = '⬡ CONECTADO — TOQUE EM "ATIVAR" PARA INICIAR';
}};

ws.onmessage = (e) => {{
  const ev = JSON.parse(e.data);
  if (ev.tipo === 'inicio') {{
    document.getElementById('badge-txt').textContent = 'AO VIVO';
    document.getElementById('dot-live').className = 'dot pulse';
    document.getElementById('status-line').textContent = `▶ REUNIÃO INICIADA — ${{ev.agentes?.length||''}} PARTICIPANTES`;
  }}
  if (ev.tipo === 'fala') {{
    ativarAgente(ev.agente, ev.nome, ev.cargo, ev.genero||'M', ev.texto, ev.audio, ev.ts);
    document.getElementById('status-line').textContent = `▶ ${{ev.nome.toUpperCase()}} — ${{ev.cargo.toUpperCase()}}`;
  }}
  if (ev.tipo === 'historico') {{
    ev.historico.forEach(h => adicionarHistorico(h));
  }}
  if (ev.tipo === 'mensagem_cliente') {{
    document.getElementById('status-line').textContent = `💬 ${{ev.texto}}`;
  }}
  if (ev.tipo === 'encerramento') {{
    document.getElementById('badge-txt').textContent = 'ENCERRADO';
    document.getElementById('dot-live').className = 'dot';
    AGENTES.forEach(a => {{
      const av = document.getElementById(`av-${{a.id}}`);
      if (av) av.className = `avatar-node aguardando ${{a.genero}}`;
    }});
    document.getElementById('conn-svg').innerHTML = '';
    if (ev.decisao) {{
      document.getElementById('decisao-texto').textContent = ev.decisao;
      document.getElementById('decisao-panel').className = 'decisao-panel show';
    }}
    document.getElementById('status-line').textContent = '⬡ REUNIÃO ENCERRADA';
  }}
}};

ws.onerror = () => {{
  document.getElementById('status-line').textContent = '⚠ ERRO DE CONEXÃO';
}};

// ── Chat ────────────────────────────────────────────────────────
function enviarDirecao() {{
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  fetch(`/api/v1/sala/${{SALA_ID}}/mensagem`, {{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{mensagem: msg}})
  }});
  input.value = '';
  document.getElementById('status-line').textContent = `⬡ DIREÇÃO ENVIADA: "${{msg}}"`;
}}
document.getElementById('chat-input').addEventListener('keydown', e => {{ if (e.key==='Enter') enviarDirecao(); }});

// Init
posicionarAvatares();
</script>
</body>
</html>"""
    return HTMLResponse(html)

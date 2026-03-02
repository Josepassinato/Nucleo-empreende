"""
Nucleo Empreende — API REST + Dashboard
FastAPI na porta 8000
"""

import os
import re
import json
import fcntl
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import asyncio

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
ALMA_STATE_PATH = BASE_DIR / "nucleo" / "logs" / "alma_state.json"
LOGS_DIR = BASE_DIR / "nucleo" / "logs"
SITE_DIR = BASE_DIR / "site"

# ── App ──────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Iniciar scheduler autônomo em background
    try:
        from nucleo.autonomo import scheduler
        asyncio.create_task(scheduler())
        print("⚙️ Scheduler autônomo iniciado")
    except Exception as e:
        print(f"⚠️ Scheduler não iniciado: {e}")
    yield

app = FastAPI(title="Nucleo Empreende", version="1.0.0", lifespan=lifespan)

# WhatsApp webhook router
from nucleo.webhook_whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)

# Remote Control — acesso direto para Claude
try:
    from nucleo.remote_control import router as rc_router
    app.include_router(rc_router)
except: pass

# Static files (site/)
if SITE_DIR.exists():
    app.mount("/site", StaticFiles(directory=str(SITE_DIR), html=True), name="site")

STARTUP_TIME = datetime.now()

CARGOS = {
    "lucas_mendes": "CEO",
    "mariana_oliveira": "CMO",
    "pedro_lima": "CFO",
    "carla_santos": "COO",
    "rafael_torres": "CPO",
    "ana_costa": "CHRO",
    "ze_carvalho": "Coach",
    "dani_ferreira": "Analista de Dados",
    "beto_rocha": "Otimizador",
}

NOMES = {
    "lucas_mendes": "Lucas Mendes",
    "mariana_oliveira": "Mariana Oliveira",
    "pedro_lima": "Pedro Lima",
    "carla_santos": "Carla Santos",
    "rafael_torres": "Rafael Torres",
    "ana_costa": "Ana Costa",
    "ze_carvalho": "Zé Carvalho",
    "dani_ferreira": "Dani Ferreira",
    "beto_rocha": "Beto Rocha",
}


# ── Integracoes Registry ─────────────────────────────────────────
ENV_PATH = BASE_DIR / ".env"
ENV_WHITELIST: set[str] = set()  # populated below

INTEGRACOES_REGISTRY = [
    {
        "categoria": "Empresa",
        "descricao": "Dados basicos da empresa e do dono",
        "icone": "building",
        "chaves": [
            {"env_key": "EMPRESA_NOME", "label": "Nome da Empresa", "tipo": "text", "dica": "Nome fantasia", "como_obter": ""},
            {"env_key": "DONO_NOME", "label": "Nome do Dono", "tipo": "text", "dica": "Seu nome completo", "como_obter": ""},
            {"env_key": "DONO_WHATSAPP_NUMBER", "label": "WhatsApp do Dono", "tipo": "text", "dica": "+5511999999999", "como_obter": ""},
            {"env_key": "NUCLEO_FASE", "label": "Fase do Nucleo", "tipo": "text", "dica": "1, 2 ou 3", "como_obter": ""},
            {"env_key": "LIMITE_APROVACAO_REAIS", "label": "Limite Aprovacao (R$)", "tipo": "text", "dica": "Valor maximo sem aprovacao manual", "como_obter": ""},
        ],
    },
    {
        "categoria": "LLM",
        "descricao": "Modelos de linguagem (IA)",
        "icone": "brain",
        "chaves": [
            {"env_key": "GOOGLE_API_KEY", "label": "Google AI API Key", "tipo": "secret", "dica": "Gemini / AI Studio", "como_obter": "https://aistudio.google.com/app/apikey"},
            {"env_key": "GROQ_API_KEY", "label": "Groq API Key", "tipo": "secret", "dica": "LLMs ultrarapidos", "como_obter": "https://console.groq.com"},
        ],
    },
    {
        "categoria": "Comunicacao",
        "descricao": "WhatsApp, Telegram e E-mail",
        "icone": "message",
        "chaves": [
            {"env_key": "TWILIO_ACCOUNT_SID", "label": "Twilio Account SID", "tipo": "secret", "dica": "Console Twilio", "como_obter": "https://console.twilio.com"},
            {"env_key": "TWILIO_AUTH_TOKEN", "label": "Twilio Auth Token", "tipo": "secret", "dica": "Console Twilio", "como_obter": "https://console.twilio.com"},
            {"env_key": "TWILIO_WHATSAPP_NUMBER", "label": "Twilio WhatsApp Number", "tipo": "text", "dica": "whatsapp:+14155238886", "como_obter": "https://console.twilio.com"},
            {"env_key": "TELEGRAM_BOT_TOKEN", "label": "Telegram Bot Token", "tipo": "secret", "dica": "Via @BotFather", "como_obter": "https://t.me/BotFather"},
            {"env_key": "TELEGRAM_CHAT_DONO", "label": "Telegram Chat ID (Dono)", "tipo": "text", "dica": "ID numerico do chat", "como_obter": "https://t.me/userinfobot"},
            {"env_key": "GMAIL_CLIENT_ID", "label": "Gmail Client ID", "tipo": "secret", "dica": "Google Cloud Console", "como_obter": "https://console.cloud.google.com/apis/credentials"},
            {"env_key": "GMAIL_CLIENT_SECRET", "label": "Gmail Client Secret", "tipo": "secret", "dica": "Google Cloud Console", "como_obter": "https://console.cloud.google.com/apis/credentials"},
            {"env_key": "GMAIL_REFRESH_TOKEN", "label": "Gmail Refresh Token", "tipo": "secret", "dica": "OAuth2 refresh token", "como_obter": "https://console.cloud.google.com/apis/credentials"},
        ],
    },
    {
        "categoria": "Pagamentos",
        "descricao": "Gateways de pagamento",
        "icone": "credit-card",
        "chaves": [
            {"env_key": "MERCADOPAGO_ACCESS_TOKEN", "label": "MercadoPago Access Token", "tipo": "secret", "dica": "Token de producao", "como_obter": "https://www.mercadopago.com.br/developers/panel/app"},
            {"env_key": "STRIPE_SECRET_KEY", "label": "Stripe Secret Key", "tipo": "secret", "dica": "sk_live_... ou sk_test_...", "como_obter": "https://dashboard.stripe.com/apikeys"},
        ],
    },
    {
        "categoria": "Marketing",
        "descricao": "Anuncios, SEO e criacao de conteudo",
        "icone": "megaphone",
        "chaves": [
            {"env_key": "META_ACCESS_TOKEN", "label": "Meta Ads Access Token", "tipo": "secret", "dica": "Token de acesso longo", "como_obter": "https://developers.facebook.com/tools/explorer"},
            {"env_key": "META_AD_ACCOUNT_ID", "label": "Meta Ad Account ID", "tipo": "text", "dica": "act_XXXXXXXXX", "como_obter": "https://business.facebook.com/settings"},
            {"env_key": "LEONARDO_API_KEY", "label": "Leonardo AI API Key", "tipo": "secret", "dica": "Geracao de imagens", "como_obter": "https://app.leonardo.ai/settings"},
            {"env_key": "SEMRUSH_API_KEY", "label": "SEMRush API Key", "tipo": "secret", "dica": "Analise de SEO", "como_obter": "https://www.semrush.com/management/apicenter"},
            {"env_key": "GA4_PROPERTY_ID", "label": "Google Analytics 4 Property ID", "tipo": "text", "dica": "Numerico, ex: 123456789", "como_obter": "https://analytics.google.com/analytics/web/#/a/p/admin"},
        ],
    },
    {
        "categoria": "Memoria",
        "descricao": "Bancos de dados e vetores",
        "icone": "database",
        "chaves": [
            {"env_key": "PINECONE_API_KEY", "label": "Pinecone API Key", "tipo": "secret", "dica": "Banco vetorial", "como_obter": "https://app.pinecone.io"},
            {"env_key": "SUPABASE_URL", "label": "Supabase URL", "tipo": "url", "dica": "https://xxx.supabase.co", "como_obter": "https://supabase.com/dashboard"},
            {"env_key": "SUPABASE_SERVICE_ROLE_KEY", "label": "Supabase Service Role Key", "tipo": "secret", "dica": "Chave de servico (nao anon!)", "como_obter": "https://supabase.com/dashboard"},
            {"env_key": "REDIS_URL", "label": "Redis URL", "tipo": "url", "dica": "redis://localhost:6379", "como_obter": ""},
        ],
    },
    {
        "categoria": "Vendas",
        "descricao": "Hotmart, contratos, voz e marketplace",
        "icone": "shopping-cart",
        "chaves": [
            {"env_key": "HOTMART_CLIENT_ID", "label": "Hotmart Client ID", "tipo": "secret", "dica": "API de vendas", "como_obter": "https://developers.hotmart.com"},
            {"env_key": "HOTMART_CLIENT_SECRET", "label": "Hotmart Client Secret", "tipo": "secret", "dica": "API de vendas", "como_obter": "https://developers.hotmart.com"},
            {"env_key": "HOTMART_WEBHOOK_TOKEN", "label": "Hotmart Webhook Token", "tipo": "secret", "dica": "Validacao de webhook", "como_obter": "https://developers.hotmart.com"},
            {"env_key": "HOTMART_PRODUTO_ID", "label": "Hotmart Produto ID", "tipo": "text", "dica": "ID do produto principal", "como_obter": "https://app.hotmart.com"},
            {"env_key": "HOTMART_AMBIENTE", "label": "Hotmart Ambiente", "tipo": "text", "dica": "producao ou sandbox", "como_obter": ""},
            {"env_key": "CLICKSIGN_ACCESS_TOKEN", "label": "ClickSign Access Token", "tipo": "secret", "dica": "Assinatura digital", "como_obter": "https://app.clicksign.com"},
            {"env_key": "ELEVENLABS_API_KEY", "label": "ElevenLabs API Key", "tipo": "secret", "dica": "Sintese de voz", "como_obter": "https://elevenlabs.io/app/settings"},
            {"env_key": "MELI_ACCESS_TOKEN", "label": "Mercado Livre Access Token", "tipo": "secret", "dica": "API do Mercado Livre", "como_obter": "https://developers.mercadolivre.com.br"},
        ],
    },
    {
        "categoria": "Sistema",
        "descricao": "Seguranca e ambiente",
        "icone": "shield",
        "chaves": [
            {"env_key": "SECRET_KEY", "label": "Secret Key (Dashboard)", "tipo": "secret", "dica": "Senha para salvar integracoes", "como_obter": ""},
            {"env_key": "NUCLEO_ENV", "label": "Ambiente", "tipo": "text", "dica": "production ou development", "como_obter": ""},
        ],
    },
]

# Build whitelist from registry
for cat in INTEGRACOES_REGISTRY:
    for ch in cat["chaves"]:
        ENV_WHITELIST.add(ch["env_key"])


def _mascarar_valor(valor: str, tipo: str) -> str:
    """Mask secret values showing first 4 + last 4 chars."""
    if not valor or tipo != "secret":
        return valor
    if len(valor) <= 8:
        return "****"
    return valor[:4] + "****" + valor[-4:]


def _atualizar_env(updates: dict[str, str]) -> None:
    """Update .env file with backup, file locking, and rotation."""
    # Backup
    if ENV_PATH.exists():
        backup_dir = ENV_PATH.parent / ".env_backups"
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f".env.backup.{ts}"
        shutil.copy2(ENV_PATH, backup_path)
        # Rotate: keep max 10 backups
        backups = sorted(backup_dir.glob(".env.backup.*"))
        while len(backups) > 10:
            backups.pop(0).unlink()

    # Read existing .env preserving structure
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            match = re.match(r"^([A-Z_][A-Z0-9_]*)=", stripped)
            if match:
                key = match.group(1)
                if key in remaining:
                    new_lines.append(f"{key}='{remaining.pop(key)}'")
                    continue
        new_lines.append(line)

    # Append any new keys not found in existing file
    for key, val in remaining.items():
        new_lines.append(f"{key}='{val}'")

    # Write with file locking
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write("\n".join(new_lines) + "\n")
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    os.chmod(ENV_PATH, 0o600)

    # Reload env vars into current process
    load_dotenv(ENV_PATH, override=True)


def _load_alma() -> dict:
    if ALMA_STATE_PATH.exists():
        with open(ALMA_STATE_PATH, "r") as f:
            return json.load(f)
    return {}


def _ultimo_resultado() -> str | None:
    arquivos = sorted(LOGS_DIR.glob("resultado_*.md"), reverse=True)
    if arquivos:
        return arquivos[0].read_text(encoding="utf-8")
    return None


def _ultimo_log_linhas(n: int = 50) -> list[str]:
    arquivos = sorted(LOGS_DIR.glob("nucleo_*.log"), reverse=True)
    if not arquivos:
        return []
    lines = arquivos[0].read_text(encoding="utf-8").strip().split("\n")
    return lines[-n:]


# ── Health ───────────────────────────────────────────────────────
@app.get("/")
def health():
    return {
        "sistema": "Nucleo Empreende",
        "versao": "1.0.0",
        "status": "online",
        "empresa": os.getenv("EMPRESA_NOME", "Nucleo Empreende"),
        "ts": datetime.now().isoformat(),
    }


# ── Status ───────────────────────────────────────────────────────
@app.get("/api/v1/status")
def status():
    alma = _load_alma()
    agentes_alertas = [a for a in alma.values() if a.get("estresse", 0) >= 0.7]
    uptime = (datetime.now() - STARTUP_TIME).total_seconds()
    return {
        "sistema": {"ligado": True, "uptime_segundos": int(uptime)},
        "agentes": {
            "total": len(alma),
            "ativos": len(alma),
            "em_alerta": len(agentes_alertas),
            "score_medio": round(sum(a.get("score_total", 0) for a in alma.values()) / max(len(alma), 1), 2),
        },
    }


# ── Agentes ──────────────────────────────────────────────────────
@app.get("/api/v1/agentes")
def agentes():
    alma = _load_alma()
    lista = []
    for aid, data in alma.items():
        lista.append({
            "id": aid,
            "nome": data.get("nome", NOMES.get(aid, aid)),
            "cargo": data.get("cargo", CARGOS.get(aid, "Agente")),
            "score": data.get("score_total", 0),
            "estresse": data.get("estresse", 0),
            "energia": data.get("energia", 1),
            "confianca": data.get("confianca", 1),
            "tarefas_concluidas": data.get("tarefas_concluidas", 0),
            "scores": data.get("scores", {}),
        })
    lista.sort(key=lambda x: x["score"], reverse=True)
    return {"agentes": lista}


# ── Dashboard Data ───────────────────────────────────────────────
@app.get("/api/v1/dashboard")
def dashboard_data():
    alma = _load_alma()
    resultado = _ultimo_resultado()
    logs = _ultimo_log_linhas(30)
    return {
        "agentes": agentes()["agentes"],
        "status": status(),
        "ultimo_resultado": resultado,
        "logs_recentes": logs,
    }


# ── Último resultado ─────────────────────────────────────────────
@app.get("/api/v1/resultado")
def ultimo_resultado():
    resultado = _ultimo_resultado()
    if resultado:
        return {"resultado": resultado}
    return {"resultado": None, "mensagem": "Nenhum resultado encontrado"}


# ── Logs ─────────────────────────────────────────────────────────
@app.get("/api/v1/logs")
def logs(linhas: int = 50):
    return {"logs": _ultimo_log_linhas(linhas)}


# ── Integracoes ──────────────────────────────────────────────────
@app.get("/api/v1/integracoes")
def listar_integracoes():
    categorias = []
    for cat in INTEGRACOES_REGISTRY:
        chaves_info = []
        configurados = 0
        for ch in cat["chaves"]:
            val = os.getenv(ch["env_key"], "")
            tem_valor = bool(val)
            if tem_valor:
                configurados += 1
            chaves_info.append({
                "env_key": ch["env_key"],
                "label": ch["label"],
                "tipo": ch["tipo"],
                "dica": ch["dica"],
                "como_obter": ch["como_obter"],
                "valor": _mascarar_valor(val, ch["tipo"]) if tem_valor else "",
                "configurado": tem_valor,
            })
        total = len(cat["chaves"])
        if configurados == total:
            badge = "conectado"
        elif configurados > 0:
            badge = "parcial"
        else:
            badge = "desconectado"
        categorias.append({
            "categoria": cat["categoria"],
            "descricao": cat["descricao"],
            "icone": cat["icone"],
            "badge": badge,
            "configurados": configurados,
            "total": total,
            "chaves": chaves_info,
        })
    return {"categorias": categorias}


@app.post("/api/v1/integracoes")
async def salvar_integracoes(request: Request):
    # Auth check
    secret = request.headers.get("X-Secret-Key", "")
    expected = os.getenv("SECRET_KEY", "")
    if not expected:
        return JSONResponse(
            status_code=403,
            content={"erro": "SECRET_KEY nao configurada no servidor. Defina-a no .env primeiro."},
        )
    if secret != expected:
        return JSONResponse(
            status_code=401,
            content={"erro": "Chave secreta invalida"},
        )

    body = await request.json()
    chaves = body.get("chaves", {})
    if not isinstance(chaves, dict) or not chaves:
        return JSONResponse(
            status_code=400,
            content={"erro": "Envie {\"chaves\": {\"KEY\": \"valor\", ...}}"},
        )

    # Validate
    erros = []
    sanitized: dict[str, str] = {}
    for key, val in chaves.items():
        if key not in ENV_WHITELIST:
            erros.append(f"Chave '{key}' nao permitida")
            continue
        val = str(val)
        if len(val) > 500:
            erros.append(f"'{key}' excede 500 caracteres")
            continue
        if "\n" in val or "\r" in val or "\x00" in val:
            erros.append(f"'{key}' contem caracteres invalidos")
            continue
        sanitized[key] = val

    if erros and not sanitized:
        return JSONResponse(status_code=400, content={"erro": "; ".join(erros)})

    _atualizar_env(sanitized)

    return {
        "sucesso": True,
        "atualizadas": len(sanitized),
        "erros": erros if erros else None,
    }


# ── WebSocket ────────────────────────────────────────────────────

# ── Chat direto (dashboard e testes) ─────────────────────────
@app.post("/api/v1/chat")
async def chat_direto(request: Request):
    """Chat direto com qualquer agente."""
    data = await request.json()
    mensagem = data.get("mensagem","")
    agente   = data.get("agente","lucas")
    try:
        from nucleo.webhook_whatsapp import resposta_lucas, resposta_agente, mem_add
        if agente != "lucas":
            resp = await resposta_agente(agente, mensagem)
        else:
            resp = await resposta_lucas(mensagem)
        mem_add("user", mensagem)
        mem_add("assistant", resp, agente)
        return {"resposta": resp, "agente": agente}
    except Exception as e:
        return {"resposta": f"Erro: {e}", "agente": agente}

@app.post("/api/v1/reset")
async def reset_empresa():
    """Reset para sistema virgem."""
    import json
    from pathlib import Path
    mem_file = Path("/root/Nucleo-empreende/nucleo/data/memoria.json")
    mem_file.parent.mkdir(parents=True, exist_ok=True)
    mem_file.write_text(json.dumps({"empresa": {}, "historico": [], "onboarding_completo": False}))
    return {"ok": True, "msg": "Sistema resetado — virgem para novo usuário"}

@app.get("/api/v1/memoria")
async def ver_memoria():
    """Ver memória atual do sistema."""
    import json
    from pathlib import Path
    mem_file = Path("/root/Nucleo-empreende/nucleo/data/memoria.json")
    if mem_file.exists():
        return json.loads(mem_file.read_text())
    return {"empresa": {}, "historico": []}

@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = {
                "tipo": "update",
                "ts": datetime.now().isoformat(),
                "agentes": agentes()["agentes"],
                "status": status()["sistema"],
            }
            await websocket.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass


# ── Dashboard HTML ───────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nucleo Empreende — Dashboard</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e4e4e7;
    --muted: #8b8fa3;
    --accent: #3b82f6;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
  .header { background:var(--surface); border-bottom:1px solid var(--border); padding:16px 24px; display:flex; justify-content:space-between; align-items:center; }
  .header h1 { font-size:20px; font-weight:600; }
  .header h1 span { color:var(--accent); }
  .header .status { display:flex; align-items:center; gap:8px; font-size:13px; color:var(--muted); }
  .header .dot { width:8px; height:8px; border-radius:50%; background:var(--green); }

  /* Tabs */
  .tabs { background:var(--surface); border-bottom:1px solid var(--border); padding:0 24px; display:flex; gap:0; }
  .tab-btn { padding:12px 24px; font-size:14px; font-weight:500; color:var(--muted); background:none; border:none; border-bottom:2px solid transparent; cursor:pointer; transition:all 0.2s; }
  .tab-btn:hover { color:var(--text); }
  .tab-btn.active { color:var(--accent); border-bottom-color:var(--accent); }
  .tab-content { display:none; }
  .tab-content.active { display:block; }

  .container { max-width:1200px; margin:0 auto; padding:24px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
  .card { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:20px; }
  .card h2 { font-size:14px; color:var(--muted); margin-bottom:16px; text-transform:uppercase; letter-spacing:0.5px; }
  .agent-row { display:flex; align-items:center; gap:12px; padding:10px 0; border-bottom:1px solid var(--border); }
  .agent-row:last-child { border-bottom:none; }
  .rank { font-size:13px; color:var(--muted); width:24px; text-align:center; font-weight:600; }
  .agent-info { flex:1; }
  .agent-name { font-size:14px; font-weight:500; }
  .agent-role { font-size:12px; color:var(--muted); }
  .score-bar { width:120px; }
  .bar-bg { height:6px; background:var(--border); border-radius:3px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:3px; transition:width 0.5s; }
  .bar-label { font-size:12px; color:var(--muted); margin-top:2px; text-align:right; }
  .stress-badge { font-size:11px; padding:2px 8px; border-radius:10px; font-weight:500; }
  .stress-low { background:#22c55e22; color:var(--green); }
  .stress-med { background:#eab30822; color:var(--yellow); }
  .stress-high { background:#ef444422; color:var(--red); }
  .stat-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; }
  .stat { text-align:center; }
  .stat-value { font-size:28px; font-weight:700; color:var(--accent); }
  .stat-label { font-size:12px; color:var(--muted); }
  .resultado { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:20px; margin-bottom:16px; }
  .resultado h2 { font-size:14px; color:var(--muted); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px; }
  .resultado pre { font-size:13px; line-height:1.6; white-space:pre-wrap; color:var(--text); font-family:'Segoe UI', system-ui, sans-serif; }
  .logs { background:#0d0f14; border:1px solid var(--border); border-radius:8px; padding:16px; max-height:300px; overflow-y:auto; }
  .logs h2 { font-size:14px; color:var(--muted); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px; }
  .logs pre { font-size:11px; line-height:1.5; color:var(--muted); font-family:'JetBrains Mono', 'Fira Code', monospace; white-space:pre-wrap; }

  /* Integracoes */
  .int-card { background:var(--surface); border:1px solid var(--border); border-radius:8px; margin-bottom:12px; overflow:hidden; }
  .int-header { padding:16px 20px; display:flex; align-items:center; gap:12px; cursor:pointer; user-select:none; }
  .int-header:hover { background:#1e2130; }
  .int-icon { width:36px; height:36px; border-radius:8px; background:var(--accent); display:flex; align-items:center; justify-content:center; font-size:16px; flex-shrink:0; }
  .int-icon.conectado { background:#22c55e33; }
  .int-icon.parcial { background:#eab30833; }
  .int-icon.desconectado { background:#ef444433; }
  .int-meta { flex:1; }
  .int-title { font-size:15px; font-weight:600; }
  .int-desc { font-size:12px; color:var(--muted); margin-top:2px; }
  .int-progress { width:100px; }
  .int-progress-bar { height:4px; background:var(--border); border-radius:2px; overflow:hidden; margin-bottom:4px; }
  .int-progress-fill { height:100%; border-radius:2px; transition:width 0.3s; }
  .int-progress-label { font-size:11px; color:var(--muted); text-align:right; }
  .int-badge { font-size:11px; padding:3px 10px; border-radius:10px; font-weight:600; white-space:nowrap; }
  .badge-conectado { background:#22c55e22; color:var(--green); }
  .badge-parcial { background:#eab30822; color:var(--yellow); }
  .badge-desconectado { background:#2a2d3a; color:var(--muted); }
  .int-chevron { color:var(--muted); font-size:18px; transition:transform 0.2s; }
  .int-card.open .int-chevron { transform:rotate(90deg); }
  .int-body { display:none; padding:0 20px 16px; }
  .int-card.open .int-body { display:block; }
  .int-row { display:flex; align-items:center; gap:10px; padding:8px 0; border-top:1px solid var(--border); }
  .int-row:first-child { border-top:none; }
  .int-label { font-size:13px; width:200px; flex-shrink:0; }
  .int-label small { display:block; color:var(--muted); font-size:11px; }
  .int-input { flex:1; display:flex; gap:8px; align-items:center; }
  .int-input input { flex:1; background:var(--bg); border:1px solid var(--border); border-radius:4px; padding:7px 10px; color:var(--text); font-size:13px; font-family:inherit; }
  .int-input input:focus { outline:none; border-color:var(--accent); }
  .int-input input::placeholder { color:#555; }
  .int-status-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
  .int-status-dot.on { background:var(--green); }
  .int-status-dot.off { background:var(--border); }
  .int-link { font-size:11px; color:var(--accent); text-decoration:none; white-space:nowrap; }
  .int-link:hover { text-decoration:underline; }
  .int-save-row { padding-top:12px; display:flex; justify-content:flex-end; }
  .btn { padding:8px 20px; border-radius:6px; border:none; font-size:13px; font-weight:500; cursor:pointer; transition:all 0.2s; }
  .btn-primary { background:var(--accent); color:#fff; }
  .btn-primary:hover { background:#2563eb; }
  .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }

  /* Modal */
  .modal-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:100; align-items:center; justify-content:center; }
  .modal-overlay.show { display:flex; }
  .modal { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:24px; width:360px; max-width:90vw; }
  .modal h3 { font-size:16px; margin-bottom:4px; }
  .modal p { font-size:13px; color:var(--muted); margin-bottom:16px; }
  .modal input { width:100%; background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:10px 12px; color:var(--text); font-size:14px; margin-bottom:16px; }
  .modal input:focus { outline:none; border-color:var(--accent); }
  .modal-actions { display:flex; gap:8px; justify-content:flex-end; }
  .btn-ghost { background:none; color:var(--muted); border:1px solid var(--border); }
  .btn-ghost:hover { color:var(--text); border-color:var(--text); }

  /* Toast */
  .toast-container { position:fixed; top:20px; right:20px; z-index:200; display:flex; flex-direction:column; gap:8px; }
  .toast { padding:12px 20px; border-radius:8px; font-size:13px; font-weight:500; animation:slideIn 0.3s ease; }
  .toast-success { background:#22c55e; color:#fff; }
  .toast-error { background:#ef4444; color:#fff; }
  @keyframes slideIn { from { transform:translateX(100px); opacity:0; } to { transform:translateX(0); opacity:1; } }

  @media(max-width:768px) { .grid { grid-template-columns:1fr; } .stat-grid { grid-template-columns:repeat(2,1fr); } .int-row { flex-direction:column; align-items:stretch; } .int-label { width:auto; } }
</style>
</head>
<body>
<div class="header">
  <h1><span>Nucleo</span> Empreende</h1>
  <div class="status"><div class="dot" id="dot"></div><span id="uptime">Conectando...</span></div>
</div>
<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('painel')">Painel</button>
  <button class="tab-btn" onclick="switchTab('integracoes')">Integracoes</button>
</div>
<div class="container">
  <!-- Tab Painel -->
  <div id="tab-painel" class="tab-content active">
    <div class="card" style="margin-bottom:16px">
      <div class="stat-grid" id="stats"></div>
    </div>
    <div class="grid">
      <div class="card">
        <h2>Leaderboard</h2>
        <div id="leaderboard"></div>
      </div>
      <div class="card">
        <h2>Detalhes dos Agentes</h2>
        <div id="details"></div>
      </div>
    </div>
    <div class="resultado">
      <h2>Ultima Sintese Executiva</h2>
      <pre id="resultado">Carregando...</pre>
    </div>
    <div class="logs">
      <h2>Logs Recentes</h2>
      <pre id="logs">Carregando...</pre>
    </div>
  </div>
  <!-- Tab Integracoes -->
  <div id="tab-integracoes" class="tab-content">
    <div id="int-list">Carregando integracoes...</div>
  </div>
</div>

<!-- Auth Modal -->
<div class="modal-overlay" id="authModal">
  <div class="modal">
    <h3>Autenticacao</h3>
    <p>Informe a SECRET_KEY para salvar as alteracoes.</p>
    <input type="password" id="authKey" placeholder="SECRET_KEY" autocomplete="off">
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeAuthModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmAuth()">Confirmar</button>
    </div>
  </div>
</div>

<!-- Toasts -->
<div class="toast-container" id="toasts"></div>

<script>
/* ── Tabs ─────────────────────────────── */
function switchTab(id) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  document.querySelector(`.tab-btn[onclick="switchTab('${id}')"]`).classList.add('active');
  if (id === 'integracoes') loadIntegracoes();
}

/* ── Toast ─────────────────────────────── */
function toast(msg, type) {
  const el = document.createElement('div');
  el.className = 'toast toast-' + type;
  el.textContent = msg;
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

/* ── Icons ─────────────────────────────── */
const ICONS = {
  'building': '&#x1f3e2;', 'brain': '&#x1f9e0;', 'message': '&#x1f4ac;',
  'credit-card': '&#x1f4b3;', 'megaphone': '&#x1f4e3;', 'database': '&#x1f4be;',
  'shopping-cart': '&#x1f6d2;', 'shield': '&#x1f6e1;'
};
const BADGE_LABELS = { conectado:'Conectado', parcial:'Parcial', desconectado:'Nao Configurado' };

/* ── Painel (existing) ─────────────────── */
function stressClass(v) { return v >= 0.7 ? 'stress-high' : v >= 0.4 ? 'stress-med' : 'stress-low'; }
function barColor(score) { return score >= 7 ? 'var(--green)' : score >= 4 ? 'var(--yellow)' : 'var(--red)'; }

function renderAgents(agentes) {
  let lb = '', dt = '';
  agentes.forEach((a, i) => {
    lb += `<div class="agent-row">
      <div class="rank">#${i+1}</div>
      <div class="agent-info"><div class="agent-name">${a.nome}</div><div class="agent-role">${a.cargo}</div></div>
      <div class="score-bar"><div class="bar-bg"><div class="bar-fill" style="width:${a.score*10}%;background:${barColor(a.score)}"></div></div><div class="bar-label">${a.score.toFixed(1)}/10</div></div>
    </div>`;
    dt += `<div class="agent-row">
      <div class="agent-info"><div class="agent-name">${a.nome}</div><div class="agent-role">${a.cargo}</div></div>
      <span class="stress-badge ${stressClass(a.estresse)}">Stress: ${(a.estresse*100).toFixed(0)}%</span>
    </div>`;
  });
  document.getElementById('leaderboard').innerHTML = lb;
  document.getElementById('details').innerHTML = dt;
}

async function loadDashboard() {
  try {
    const res = await fetch('/api/v1/dashboard');
    const data = await res.json();
    renderAgents(data.agentes);
    const s = data.status;
    document.getElementById('stats').innerHTML = `
      <div class="stat"><div class="stat-value">${s.agentes.total}</div><div class="stat-label">Agentes</div></div>
      <div class="stat"><div class="stat-value">${s.agentes.score_medio}</div><div class="stat-label">Score Medio</div></div>
      <div class="stat"><div class="stat-value">${s.agentes.em_alerta}</div><div class="stat-label">Em Alerta</div></div>`;
    document.getElementById('uptime').textContent = `Online | ${Math.floor(s.sistema.uptime_segundos/60)}min`;
    if (data.ultimo_resultado) {
      document.getElementById('resultado').textContent = data.ultimo_resultado;
    } else {
      document.getElementById('resultado').textContent = 'Aguardando primeiro ciclo...';
    }
    if (data.logs_recentes && data.logs_recentes.length) {
      document.getElementById('logs').textContent = data.logs_recentes.join('\\n');
    }
  } catch(e) { console.error(e); }
}

/* ── Integracoes ──────────────────────── */
let intData = [];

async function loadIntegracoes() {
  try {
    const res = await fetch('/api/v1/integracoes');
    const data = await res.json();
    intData = data.categorias;
    renderIntegracoes();
  } catch(e) {
    document.getElementById('int-list').innerHTML = '<p style="color:var(--red)">Erro ao carregar integracoes.</p>';
  }
}

function renderIntegracoes() {
  let html = '';
  intData.forEach((cat, ci) => {
    const pct = cat.total > 0 ? Math.round((cat.configurados / cat.total) * 100) : 0;
    const fillColor = cat.badge === 'conectado' ? 'var(--green)' : cat.badge === 'parcial' ? 'var(--yellow)' : 'var(--border)';
    html += `<div class="int-card" id="int-cat-${ci}">
      <div class="int-header" onclick="toggleCat(${ci})">
        <div class="int-icon ${cat.badge}">${ICONS[cat.icone] || '&#x2699;'}</div>
        <div class="int-meta">
          <div class="int-title">${cat.categoria}</div>
          <div class="int-desc">${cat.descricao}</div>
        </div>
        <div class="int-progress">
          <div class="int-progress-bar"><div class="int-progress-fill" style="width:${pct}%;background:${fillColor}"></div></div>
          <div class="int-progress-label">${cat.configurados}/${cat.total}</div>
        </div>
        <span class="int-badge badge-${cat.badge}">${BADGE_LABELS[cat.badge]}</span>
        <span class="int-chevron">&#x25B6;</span>
      </div>
      <div class="int-body">`;
    cat.chaves.forEach(ch => {
      const dot = ch.configurado ? 'on' : 'off';
      const val = ch.configurado ? ch.valor : '';
      const inputType = ch.tipo === 'secret' ? 'password' : 'text';
      const link = ch.como_obter ? `<a class="int-link" href="${ch.como_obter}" target="_blank">Como obter</a>` : '';
      html += `<div class="int-row">
        <div class="int-label">${ch.label}<small>${ch.dica}</small></div>
        <div class="int-input">
          <span class="int-status-dot ${dot}"></span>
          <input type="${inputType}" data-key="${ch.env_key}" placeholder="${ch.env_key}" value="${val}">
          ${link}
        </div>
      </div>`;
    });
    html += `<div class="int-save-row"><button class="btn btn-primary" onclick="saveCat(${ci})">Salvar ${cat.categoria}</button></div>
      </div></div>`;
  });
  document.getElementById('int-list').innerHTML = html;
}

function toggleCat(i) {
  document.getElementById('int-cat-' + i).classList.toggle('open');
}

/* ── Save flow ─────────────────────────── */
let pendingSaveCat = null;

function saveCat(ci) {
  pendingSaveCat = ci;
  document.getElementById('authKey').value = '';
  document.getElementById('authModal').classList.add('show');
  document.getElementById('authKey').focus();
}

function closeAuthModal() {
  document.getElementById('authModal').classList.remove('show');
  pendingSaveCat = null;
}

async function confirmAuth() {
  const key = document.getElementById('authKey').value.trim();
  if (!key) return;
  closeAuthModal();
  const ci = pendingSaveCat;
  if (ci === null) return;

  const card = document.getElementById('int-cat-' + ci);
  const inputs = card.querySelectorAll('input[data-key]');
  const chaves = {};
  inputs.forEach(inp => {
    const v = inp.value.trim();
    const orig = intData[ci].chaves.find(c => c.env_key === inp.dataset.key);
    // Only send if value changed (not the masked version and not empty)
    if (v && v !== orig.valor) {
      chaves[inp.dataset.key] = v;
    }
  });

  if (Object.keys(chaves).length === 0) {
    toast('Nenhuma alteracao detectada', 'error');
    return;
  }

  try {
    const res = await fetch('/api/v1/integracoes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Secret-Key': key },
      body: JSON.stringify({ chaves }),
    });
    const data = await res.json();
    if (res.ok && data.sucesso) {
      toast(`${data.atualizadas} chave(s) salva(s) com sucesso`, 'success');
      loadIntegracoes();
    } else {
      toast(data.erro || 'Erro ao salvar', 'error');
    }
  } catch(e) {
    toast('Erro de conexao', 'error');
  }
}

// Allow Enter to confirm auth modal
document.getElementById('authKey').addEventListener('keydown', e => {
  if (e.key === 'Enter') confirmAuth();
});

/* ── WebSocket ─────────────────────────── */
let ws;
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws/dashboard`);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.tipo === 'update') {
      renderAgents(data.agentes);
      const up = data.status.uptime_segundos;
      document.getElementById('uptime').textContent = `Online | ${Math.floor(up/60)}min`;
      document.getElementById('dot').style.background = 'var(--green)';
    }
  };
  ws.onclose = () => {
    document.getElementById('dot').style.background = 'var(--red)';
    setTimeout(connectWS, 3000);
  };
}

loadDashboard();
connectWS();
setInterval(loadDashboard, 30000);
</script>
</body>
</html>"""

# ── Endpoints Autônomos ──────────────────────────────────────────
from fastapi import APIRouter
auto_router = APIRouter()

@auto_router.post("/api/v1/autonomo/{agente}")
async def disparar_ciclo(agente: str):
    """Dispara manualmente o ciclo autônomo de um agente."""
    from nucleo.autonomo import (ciclo_diana, ciclo_pedro, 
                                  ciclo_mariana, ciclo_lucas, 
                                  ciclo_conhecimento)
    ciclos = {
        "diana":       ciclo_diana,
        "pedro":       ciclo_pedro,
        "mariana":     ciclo_mariana,
        "lucas":       ciclo_lucas,
        "conhecimento": ciclo_conhecimento,
    }
    if agente not in ciclos:
        return {"erro": f"Agente '{agente}' não encontrado"}
    try:
        resultado = await ciclos[agente]()
        return {"ok": True, "agente": agente, "resultado": resultado}
    except Exception as e:
        return {"erro": str(e)}

@auto_router.get("/api/v1/autonomo/logs")
async def ver_logs_autonomos():
    """Ver últimas ações autônomas da diretoria."""
    from pathlib import Path
    import json
    log_file = Path("nucleo/data/acoes_autonomas.json")
    if not log_file.exists():
        return {"acoes": []}
    return {"acoes": json.loads(log_file.read_text())[-50:]}

@auto_router.get("/api/v1/conhecimento")
async def ver_knowledge_base():
    """Ver knowledge base atualizado da diretoria."""
    from pathlib import Path
    import json
    kb_file = Path("nucleo/data/knowledge_base.json")
    if not kb_file.exists():
        return {"updates": []}
    return {"updates": json.loads(kb_file.read_text())[-10:]}

app.include_router(auto_router)

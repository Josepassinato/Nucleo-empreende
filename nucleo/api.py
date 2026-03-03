"""
Increase Team — API REST + Dashboard
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
    # ── SCHEDULER DESATIVADO ─────────────────────────────────────
    # Aguardando onboarding de empresa real.
    # Para reativar: descomentar as 4 linhas abaixo.
    # try:
    #     from nucleo.autonomo import scheduler
    #     asyncio.create_task(scheduler())
    #     print("⚙️ Scheduler autônomo iniciado")
    # except Exception as e:
    #     print(f"⚠️ Scheduler não iniciado: {e}")
    print("⏸️  Scheduler pausado — aguardando onboarding")
    yield

app = FastAPI(title="Increase Team", version="1.0.0", lifespan=lifespan)

# ── Auth router ──────────────────────────────────────────────
try:
    from nucleo.auth import router as auth_router
    app.include_router(auth_router)
    print("🔐 Auth ativado")
except Exception as e:
    print(f"⚠️ Auth não carregado: {e}")

# WhatsApp webhook router
from nucleo.webhook_whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)

# Sala de Reunião Virtual
try:
    from nucleo.sala_reuniao.routes import router as sala_router
    app.include_router(sala_router)
    print("🏛️ Sala de Reunião ativada")
except Exception as e:
    print(f"⚠️ Sala não carregada: {e}")

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


# ── Health (API) ─────────────────────────────────────────────────
@app.get("/api/v1/health")
def health():
    return {
        "sistema": "Increase Team",
        "versao": "1.0.0",
        "status": "online",
        "empresa": os.getenv("EMPRESA_NOME", "Increase Team"),
        "ts": datetime.now().isoformat(),
    }

# ── Home Page ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home_page():
    return HTMLResponse('<meta http-equiv="refresh" content="0;url=/login">')

@app.get("/login", response_class=HTMLResponse)
def login_page():
    auth_path = Path(__file__).parent.parent / "site" / "auth.html"
    if auth_path.exists():
        return HTMLResponse(auth_path.read_text())
    return HTMLResponse(HOME_HTML)


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
<title>Increase Team — Dashboard</title>
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

# ── Endpoints Colegiado ──────────────────────────────────────────
@app.post("/api/v1/colegiado")
async def convocar_reuniao(request: Request):
    """Convoca reunião colegiada para uma decisão."""
    from nucleo.colegiado import reuniao_colegiada
    data = await request.json()
    resultado = await reuniao_colegiada(
        tema=data.get("tema", ""),
        descricao=data.get("descricao", ""),
        proponente=data.get("proponente", "dono"),
        tipo=data.get("tipo", "decisao")
    )
    return resultado

@app.get("/api/v1/colegiado/pautas")
async def ver_pautas():
    """Ver histórico de pautas do colegiado."""
    import json
    f = Path("nucleo/data/pautas_colegiado.json")
    return {"pautas": json.loads(f.read_text())[-20:] if f.exists() else []}

@app.post("/api/v1/autodev/{agente}")
async def disparar_autodev(agente: str):
    """Dispara ciclo de autodesenvolvimento de um agente."""
    from nucleo.colegiado import ciclo_autodesenvolvimento
    resultado = await ciclo_autodesenvolvimento(agente)
    return {"ok": True, "agente": agente, "reflexao": resultado}

@app.get("/api/v1/reflexoes")
async def ver_reflexoes():
    """Ver reflexões de autodesenvolvimento dos agentes."""
    import json
    f = Path("nucleo/data/reflexoes_agentes.json")
    return {"reflexoes": json.loads(f.read_text())[-30:] if f.exists() else []}

# ══════════════════════════════════════════════════════════════════
# MURAL DIGITAL — CRM de Tarefas da Diretoria
# ══════════════════════════════════════════════════════════════════

@app.get("/api/v1/mural")
def mural_data():
    """Retorna todos os dados do mural: tarefas do dia + abertas + agentes."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── Ações do dia (rotinas autônomas) ─────────────────────────
    acoes_hoje = []
    acoes_file = Path("nucleo/data/acoes_autonomas.json")
    if acoes_file.exists():
        try:
            todas = json.loads(acoes_file.read_text())
            acoes_hoje = [a for a in todas if a.get("ts","").startswith(hoje)]
        except: pass

    # ── Tarefas abertas das atas (5W2H) ──────────────────────────
    tarefas_abertas = []
    tarefas_concluidas = []
    salas_dir = Path("nucleo/data/salas")
    if salas_dir.exists():
        for arq in sorted(salas_dir.glob("*.json"), reverse=True)[:20]:
            try:
                sala = json.loads(arq.read_text())
                tema = sala.get("tema","")
                data_sala = sala.get("criado_em","")[:10]
                decisao = sala.get("decisao_final","")
                # Extrair 5W2H da decisão
                if "QUEM:" in decisao or "O QUÊ:" in decisao or "O QUE:" in decisao:
                    tarefa = {
                        "sala_id": sala.get("id",""),
                        "tema": tema,
                        "data": data_sala,
                        "o_que": "", "quem": "", "quando": "",
                        "por_que": "", "onde": "", "como": "", "quanto": "",
                        "status": "aberta"
                    }
                    for linha in decisao.split("\n"):
                        for campo, chaves in [
                            ("o_que",   ["O QUÊ:","O QUE:"]),
                            ("quem",    ["QUEM:"]),
                            ("quando",  ["QUANDO:"]),
                            ("por_que", ["POR QUÊ:","POR QUE:"]),
                            ("onde",    ["ONDE:"]),
                            ("como",    ["COMO:"]),
                            ("quanto",  ["QUANTO:"]),
                        ]:
                            for chave in chaves:
                                if chave in linha:
                                    tarefa[campo] = linha.split(chave,1)[-1].strip()[:120]
                    if tarefa["quem"] or tarefa["o_que"]:
                        if data_sala == hoje:
                            tarefas_concluidas.append(tarefa)
                        else:
                            tarefas_abertas.append(tarefa)
            except: pass

    # ── Contexto compartilhado (o que cada agente sabe) ──────────
    shared = {}
    shared_file = Path("nucleo/data/contexto_compartilhado.json")
    if shared_file.exists():
        try: shared = json.loads(shared_file.read_text())
        except: pass

    # ── Heartbeat (status de cada agente) ────────────────────────
    heartbeat = {}
    hb_file = Path("nucleo/data/heartbeat.json")
    if hb_file.exists():
        try: heartbeat = json.loads(hb_file.read_text())
        except: pass

    # ── Score de produtividade do dia ─────────────────────────────
    total_ciclos_esperados = 24  # rotinas diárias planejadas
    ciclos_executados = len(set(a.get("agente","") + a.get("acao","") for a in acoes_hoje))
    score_dia = min(100, int((ciclos_executados / total_ciclos_esperados) * 100))

    return {
        "atualizado_em": agora_str,
        "hoje": hoje,
        "score_produtividade": score_dia,
        "acoes_hoje": acoes_hoje[-50:],
        "tarefas_abertas": tarefas_abertas,
        "tarefas_concluidas_hoje": tarefas_concluidas,
        "shared_context": shared,
        "heartbeat": heartbeat,
        "resumo": {
            "acoes_hoje": len(acoes_hoje),
            "tarefas_abertas": len(tarefas_abertas),
            "tarefas_concluidas": len(tarefas_concluidas),
            "agentes_ativos_hoje": len(set(a.get("agente","") for a in acoes_hoje)),
        }
    }


@app.get("/mural", response_class=HTMLResponse)
def mural_page():
    """Mural digital — CRM público da diretoria."""
    return HTMLResponse(MURAL_HTML)


MURAL_HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mural — Increase Team</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #080b0f;
    --surface: #0e1318;
    --border: #1a2330;
    --accent: #00e5a0;
    --accent2: #0099ff;
    --warn: #ff6b35;
    --text: #e8edf2;
    --muted: #4a6070;
    --card: #111820;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Grid de fundo */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,229,160,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,229,160,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(8,11,15,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
    padding: 0 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .logo-icon {
    width: 36px; height: 36px;
    background: var(--accent);
    border-radius: 8px;
    display: grid;
    place-items: center;
    font-size: 18px;
  }
  .logo-text { font-size: 1.1rem; font-weight: 800; letter-spacing: -0.5px; }
  .logo-sub { font-size: 0.7rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; }

  .header-right {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }
  .live-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
  }
  .live-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50% { opacity:0.5; transform:scale(0.8); }
  }
  #clock { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--muted); }

  main {
    position: relative;
    z-index: 1;
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
  }

  /* Score bar */
  .score-section {
    display: flex;
    align-items: center;
    gap: 2rem;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 2rem;
    overflow: hidden;
    position: relative;
  }
  .score-section::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: var(--accent);
    border-radius: 4px 0 0 4px;
  }
  .score-num {
    font-size: 3.5rem;
    font-weight: 800;
    color: var(--accent);
    line-height: 1;
    min-width: 80px;
  }
  .score-label { font-size: 0.7rem; color: var(--muted); font-family: 'JetBrains Mono'; text-transform: uppercase; letter-spacing: 1px; }
  .score-bar-wrap { flex: 1; }
  .score-bar-track {
    height: 8px;
    background: var(--border);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 8px;
  }
  .score-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 4px;
    transition: width 1s ease;
  }
  .score-stats {
    display: flex;
    gap: 2rem;
    margin-left: auto;
  }
  .stat { text-align: center; }
  .stat-num { font-size: 1.8rem; font-weight: 700; color: var(--text); line-height: 1; }
  .stat-label { font-size: 0.65rem; color: var(--muted); font-family: 'JetBrains Mono'; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

  /* Grid de colunas */
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
  }
  @media (max-width: 1100px) { .grid { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }

  .col-title {
    font-size: 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--muted);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .col-title-dot {
    width: 6px; height: 6px; border-radius: 50%;
  }

  /* Cards de tarefa */
  .task-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s, transform 0.2s;
    animation: fadeIn 0.4s ease both;
  }
  .task-card:hover {
    border-color: rgba(0,229,160,0.3);
    transform: translateX(3px);
  }
  @keyframes fadeIn {
    from { opacity:0; transform: translateY(8px); }
    to   { opacity:1; transform: translateY(0); }
  }
  .task-card.aberta { border-left: 3px solid var(--warn); }
  .task-card.concluida { border-left: 3px solid var(--accent); }
  .task-card.acao { border-left: 3px solid var(--accent2); }

  .task-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }
  .task-tema {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.3;
  }
  .task-badge {
    font-size: 0.6rem;
    font-family: 'JetBrains Mono';
    padding: 2px 8px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .badge-aberta { background: rgba(255,107,53,0.15); color: var(--warn); }
  .badge-concluida { background: rgba(0,229,160,0.12); color: var(--accent); }
  .badge-acao { background: rgba(0,153,255,0.12); color: var(--accent2); }

  .task-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 12px;
    margin-top: 8px;
  }
  .task-field {
    font-size: 0.7rem;
    display: flex;
    gap: 4px;
  }
  .task-field-key {
    color: var(--muted);
    font-family: 'JetBrains Mono';
    flex-shrink: 0;
  }
  .task-field-val { color: var(--text); }

  .task-ts {
    font-size: 0.62rem;
    color: var(--muted);
    font-family: 'JetBrains Mono';
    margin-top: 6px;
  }

  /* Agentes sidebar */
  .agents-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
  }
  @media (max-width: 900px) { .agents-grid { grid-template-columns: repeat(3, 1fr); } }

  .agent-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    transition: all 0.2s;
    animation: fadeIn 0.4s ease both;
  }
  .agent-card.ativo { border-color: rgba(0,229,160,0.4); }
  .agent-card:hover { transform: translateY(-2px); }
  .agent-avatar {
    width: 48px; height: 48px;
    border-radius: 50%;
    margin: 0 auto 8px;
    display: grid;
    place-items: center;
    font-size: 22px;
    background: var(--surface);
    border: 2px solid var(--border);
  }
  .agent-card.ativo .agent-avatar { border-color: var(--accent); }
  .agent-nome { font-size: 0.75rem; font-weight: 600; }
  .agent-cargo { font-size: 0.6rem; color: var(--muted); font-family: 'JetBrains Mono'; margin-top: 2px; }
  .agent-acoes {
    font-size: 0.65rem;
    color: var(--accent);
    font-family: 'JetBrains Mono';
    margin-top: 6px;
  }
  .agent-ultima {
    font-size: 0.6rem;
    color: var(--muted);
    margin-top: 4px;
    font-family: 'JetBrains Mono';
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Empty state */
  .empty {
    text-align: center;
    padding: 2rem;
    color: var(--muted);
    font-size: 0.8rem;
    font-family: 'JetBrains Mono';
  }

  /* Scrollable column */
  .col-scroll {
    max-height: 520px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }

  .section-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 1rem;
    letter-spacing: -0.3px;
  }

  footer {
    text-align: center;
    padding: 2rem;
    font-size: 0.7rem;
    color: var(--muted);
    font-family: 'JetBrains Mono';
    border-top: 1px solid var(--border);
    margin-top: 2rem;
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">⬡</div>
    <div>
      <div class="logo-text">INCREASE TEAM</div>
      <div class="logo-sub">MURAL DIGITAL — DIRETORIA</div>
    </div>
  </div>
  <div class="header-right">
    <div class="live-badge">
      <div class="live-dot"></div>
      AO VIVO
    </div>
    <div id="clock">--:--:--</div>
  </div>
</header>

<main>

  <!-- Score do dia -->
  <div class="score-section" id="score-section">
    <div>
      <div class="score-label">produtividade hoje</div>
      <div class="score-num" id="score-num">--</div>
    </div>
    <div class="score-bar-wrap">
      <div class="score-label">ciclos executados / planejados</div>
      <div class="score-bar-track">
        <div class="score-bar-fill" id="score-bar" style="width:0%"></div>
      </div>
    </div>
    <div class="score-stats">
      <div class="stat">
        <div class="stat-num" id="stat-acoes">--</div>
        <div class="stat-label">ações hoje</div>
      </div>
      <div class="stat">
        <div class="stat-num" id="stat-abertas">--</div>
        <div class="stat-label">tarefas abertas</div>
      </div>
      <div class="stat">
        <div class="stat-num" id="stat-agentes">--</div>
        <div class="stat-label">agentes ativos</div>
      </div>
    </div>
  </div>

  <!-- Agentes -->
  <div class="section-title">Diretoria</div>
  <div class="agents-grid" id="agents-grid">
    <div class="empty">Carregando...</div>
  </div>

  <!-- Grid principal -->
  <div class="grid">

    <!-- Coluna 1: Ações do dia -->
    <div>
      <div class="col-title">
        <div class="col-title-dot" style="background:#0099ff"></div>
        Atividades do Dia
      </div>
      <div class="col-scroll" id="acoes-col">
        <div class="empty">Carregando...</div>
      </div>
    </div>

    <!-- Coluna 2: Tarefas abertas -->
    <div>
      <div class="col-title">
        <div class="col-title-dot" style="background:#ff6b35"></div>
        Tarefas em Aberto (5W2H)
      </div>
      <div class="col-scroll" id="abertas-col">
        <div class="empty">Carregando...</div>
      </div>
    </div>

    <!-- Coluna 3: Concluídas hoje -->
    <div>
      <div class="col-title">
        <div class="col-title-dot" style="background:#00e5a0"></div>
        Concluídas Hoje
      </div>
      <div class="col-scroll" id="concluidas-col">
        <div class="empty">Carregando...</div>
      </div>
    </div>

  </div>

</main>

<footer id="footer">Atualizado em --</footer>

<script>
const AGENTES_META = {
  lucas:   { nome: "Lucas",   cargo: "CEO",   icon: "👔" },
  mariana: { nome: "Mariana", cargo: "CMO",   icon: "📣" },
  pedro:   { nome: "Pedro",   cargo: "CFO",   icon: "💰" },
  carla:   { nome: "Carla",   cargo: "COO",   icon: "⚙️" },
  rafael:  { nome: "Rafael",  cargo: "CPO",   icon: "🚀" },
  ana:     { nome: "Ana",     cargo: "CHRO",  icon: "🧘" },
  dani:    { nome: "Dani",    cargo: "Dados", icon: "📊" },
  ze:      { nome: "Zé",      cargo: "Coach", icon: "🎯" },
  beto:    { nome: "Beto",    cargo: "Otim.", icon: "💡" },
  diana:   { nome: "Diana",   cargo: "CNO",   icon: "🔍" },
};

function clock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString("pt-BR");
}
setInterval(clock, 1000); clock();

function esc(s) {
  return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function renderAcoes(acoes) {
  if (!acoes.length) return '<div class="empty">Nenhuma atividade ainda hoje</div>';
  return acoes.slice().reverse().map((a, i) => `
    <div class="task-card acao" style="animation-delay:${i*0.05}s">
      <div class="task-header">
        <div class="task-tema">${esc(a.acao || "ação executada")}</div>
        <span class="task-badge badge-acao">${esc((AGENTES_META[a.agente]||{}).icon||"")} ${esc(a.agente||"")}</span>
      </div>
      <div class="task-ts">${esc((a.ts||"").replace("T"," ").slice(0,16))}</div>
      ${a.resultado ? `<div class="task-field" style="margin-top:6px"><span class="task-field-val" style="font-size:0.68rem;color:#4a6070;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${esc(a.resultado.slice(0,120))}</span></div>` : ""}
    </div>
  `).join("");
}

function renderTarefas(tarefas, tipo) {
  if (!tarefas.length) return `<div class="empty">${tipo === "aberta" ? "Sem tarefas abertas 🎉" : "Nenhuma concluída hoje ainda"}</div>`;
  return tarefas.map((t, i) => `
    <div class="task-card ${tipo}" style="animation-delay:${i*0.07}s">
      <div class="task-header">
        <div class="task-tema">${esc(t.o_que || t.tema || "Tarefa")}</div>
        <span class="task-badge ${tipo==="aberta"?"badge-aberta":"badge-concluida"}">${tipo==="aberta"?"⏳ ABERTA":"✅ FEITA"}</span>
      </div>
      <div class="task-fields">
        ${t.quem    ? `<div class="task-field"><span class="task-field-key">quem</span><span class="task-field-val">${esc(t.quem)}</span></div>` : ""}
        ${t.quando  ? `<div class="task-field"><span class="task-field-key">quando</span><span class="task-field-val">${esc(t.quando)}</span></div>` : ""}
        ${t.onde    ? `<div class="task-field"><span class="task-field-key">onde</span><span class="task-field-val">${esc(t.onde)}</span></div>` : ""}
        ${t.quanto  ? `<div class="task-field"><span class="task-field-key">quanto</span><span class="task-field-val">${esc(t.quanto)}</span></div>` : ""}
        ${t.como    ? `<div class="task-field" style="grid-column:span 2"><span class="task-field-key">como</span><span class="task-field-val">${esc(t.como)}</span></div>` : ""}
      </div>
      <div class="task-ts">Reunião: ${esc(t.tema||"")} · ${esc(t.data||"")}</div>
    </div>
  `).join("");
}

function renderAgentes(acoes) {
  const acosPorAgente = {};
  acoes.forEach(a => {
    if (!acosPorAgente[a.agente]) acosPorAgente[a.agente] = [];
    acosPorAgente[a.agente].push(a);
  });

  return Object.entries(AGENTES_META).map(([id, meta], i) => {
    const minhasAcoes = acosPorAgente[id] || [];
    const ativo = minhasAcoes.length > 0;
    const ultima = minhasAcoes.slice(-1)[0];
    return `
      <div class="agent-card ${ativo?"ativo":""}" style="animation-delay:${i*0.06}s">
        <div class="agent-avatar">${meta.icon}</div>
        <div class="agent-nome">${meta.nome}</div>
        <div class="agent-cargo">${meta.cargo}</div>
        <div class="agent-acoes">${minhasAcoes.length} ações</div>
        ${ultima ? `<div class="agent-ultima">${esc(ultima.acao.slice(0,30))}</div>` : '<div class="agent-ultima" style="color:var(--border)">aguardando</div>'}
      </div>
    `;
  }).join("");
}

async function atualizar() {
  try {
    const r = await fetch("/api/v1/mural");
    const d = await r.json();

    // Score
    document.getElementById("score-num").textContent = d.score_produtividade + "%";
    document.getElementById("score-bar").style.width = d.score_produtividade + "%";
    document.getElementById("stat-acoes").textContent = d.resumo.acoes_hoje;
    document.getElementById("stat-abertas").textContent = d.resumo.tarefas_abertas;
    document.getElementById("stat-agentes").textContent = d.resumo.agentes_ativos_hoje;

    // Agentes
    document.getElementById("agents-grid").innerHTML = renderAgentes(d.acoes_hoje);

    // Colunas
    document.getElementById("acoes-col").innerHTML     = renderAcoes(d.acoes_hoje);
    document.getElementById("abertas-col").innerHTML   = renderTarefas(d.tarefas_abertas, "aberta");
    document.getElementById("concluidas-col").innerHTML = renderTarefas(d.tarefas_concluidas_hoje, "concluida");

    document.getElementById("footer").textContent = "Atualizado em " + d.atualizado_em + " · refresh automático a cada 60s";
  } catch(e) {
    console.error("Erro ao carregar mural:", e);
  }
}

atualizar();
setInterval(atualizar, 60000);
</script>
</body>
</html>'''

# ══════════════════════════════════════════════════════════════════
# ALEX — Agente Consultor de Onboarding
# ══════════════════════════════════════════════════════════════════
from nucleo.alex.routes import router as alex_router
app.include_router(alex_router)

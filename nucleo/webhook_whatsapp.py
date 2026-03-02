"""
Nucleo Empreende — Webhook WhatsApp
Conversa fluida com diretoria completa no mesmo chat.
"""
import os, re, json, httpx, logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import Response
from dotenv import load_dotenv
from nucleo.ferramentas import (buscar_web, enviar_email_zoho, enviar_email_gmail,
    telegram_enviar, hotmart_vendas, meta_ads_resumo)

load_dotenv()
logger = logging.getLogger("nucleo.whatsapp")
router = APIRouter()

# ── Config ──────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
TWILIO_WPP     = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
DONO_NUMBER    = os.getenv("DONO_WHATSAPP_NUMBER", "")

BASE_DIR   = Path(__file__).resolve().parent.parent
AGENTES_DIR = BASE_DIR / "nucleo" / "agentes"
MEM_FILE   = BASE_DIR / "nucleo" / "data" / "memoria.json"
MEM_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Memória persistente ──────────────────────────────────────
def mem_carregar() -> dict:
    if MEM_FILE.exists():
        try: return json.loads(MEM_FILE.read_text())
        except: pass
    return {"empresa": {}, "historico": [], "onboarding_completo": False}

def mem_salvar(mem: dict):
    MEM_FILE.write_text(json.dumps(mem, ensure_ascii=False, indent=2))

def mem_add(role: str, conteudo: str, agente: str = "lucas"):
    mem = mem_carregar()
    mem.setdefault("historico", []).append({
        "role": role, "agente": agente,
        "conteudo": conteudo[:500],
        "ts": datetime.now().strftime("%d/%m %H:%M")
    })
    # Manter últimas 40 mensagens
    mem["historico"] = mem["historico"][-40:]
    mem_salvar(mem)

def mem_extrair_fatos(texto: str):
    """Extrai fatos da mensagem e persiste."""
    mem = mem_carregar()
    emp = mem.setdefault("empresa", {})
    padroes = [
        (r"(?:ramo|área|segmento)\s+(?:é\s+|de\s+)?(.+)", "ramo"),
        (r"(?:somos|tenho|é\s+uma?)\s+(?:uma?\s+)?(.+?)(?:\s+e\s+|\.|,|$)", "ramo"),
        (r"produto\s+(?:é\s+|principal\s+)?(.+)", "produto"),
        (r"(?:vendemos|vendo|oferecemos)\s+(.+)", "produto"),
        (r"(?:meu\s+nome\s+é|me\s+chamo|sou\s+o?)\s+(\w+)", "dono_nome"),
        (r"meta\s+(?:de\s+)?faturamento\s+(?:é\s+)?r?\$?\s*([\d.,]+\w*)", "meta"),
        (r"(?:cidade|localiz)\w*\s+(?:é\s+|em\s+)?(.+)", "cidade"),
    ]
    atualizado = False
    for padrao, campo in padroes:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m and not emp.get(campo):
            emp[campo] = m.group(1).strip().rstrip(".,!")
            atualizado = True
    if atualizado:
        mem_salvar(mem)

# ── Carregar personalidade ───────────────────────────────────
def carregar_md(nome_arquivo: str) -> str:
    f = AGENTES_DIR / nome_arquivo
    if f.exists(): return f.read_text()
    return ""

# ── Detectar qual agente foi convocado ───────────────────────
MENCOES = {
    "diana": ["diana", "@diana", "cno"],
    "pedro": ["pedro", "@pedro", "cfo", "financeiro"],
    "mariana": ["mariana", "@mariana", "cmo", "marketing"],
    "carla": ["carla", "@carla", "coo", "operações", "operacoes"],
    "rafael": ["rafael", "@rafael", "cpo", "produto"],
    "ana": ["ana", "@ana", "rh", "chro", "pessoas"],
    "dani": ["dani", "@dani", "dados", "analytics"],
    "ze": ["zé", "ze", "@ze", "coach"],
    "beto": ["beto", "@beto", "otimizador"],
}

def detectar_agente_convocado(texto: str) -> str | None:
    txt = texto.lower()
    # Verificar se começa com nome do agente (convocação direta)
    for agente, mencoes in MENCOES.items():
        for m in mencoes:
            if txt.startswith(m) or f" {m}," in txt or f" {m} " in txt[:30]:
                return agente
    return None

# ── Montar contexto completo ─────────────────────────────────
def montar_contexto(n_hist: int = 15) -> str:
    mem = mem_carregar()
    emp = mem.get("empresa", {})
    hist = mem.get("historico", [])[-n_hist:]

    ctx = []

    # Empresa
    if emp:
        ctx.append("EMPRESA CONFIGURADA:")
        for k, v in emp.items():
            if v: ctx.append(f"  {k}: {v}")
    else:
        ctx.append("EMPRESA: ainda não configurada — aguardando o dono explicar o negócio")

    # Histórico
    if hist:
        ctx.append("\nHISTÓRICO RECENTE:")
        for h in hist:
            nome = "José" if h["role"] == "user" else h.get("agente","lucas").title()
            ctx.append(f"  [{h['ts']}] {nome}: {h['conteudo']}")

    return "\n".join(ctx)

# ── Chamar Gemini ────────────────────────────────────────────
async def chamar_gemini(system: str, mensagem: str, temperatura: float = 0.85) -> str:
    if not GOOGLE_API_KEY:
        return _fallback(mensagem)
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": mensagem}]}],
                    "generationConfig": {"temperature": temperatura, "maxOutputTokens": 450}
                }
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini erro: {e}")
        return _fallback(mensagem)

def _fallback(msg: str) -> str:
    return "Estou com dificuldade técnica agora. Tenta de novo em instantes."

# ── Resposta do Lucas (CEO orquestrador) ─────────────────────
async def resposta_lucas(mensagem: str) -> str:
    pers = carregar_md("lucas_mendes_ceo.md")
    ctx  = montar_contexto()
    mem  = mem_carregar()
    emp  = mem.get("empresa", {})

    dono_nome = emp.get("dono_nome", "")

    system = f"""Você é Lucas Mendes, CEO.

{pers}

CONTEXTO ATUAL:
{ctx}

REGRAS DE COMPORTAMENTO:
- Se não há empresa configurada, se apresente brevemente e pergunte sobre o negócio
- Se já sabe o negócio, aja como CEO daquele negócio
- Responda em português natural, como mensagem de WhatsApp
- Máximo 3 parágrafos curtos
- Nunca diga que é IA
- Se o dono convocou outro diretor (Diana, Pedro etc), responda como Lucas dizendo que vai chamar e adicione a resposta desse diretor
- Se o dono pedir para enviar um email, você pode fazer isso usando o formato: [ENVIAR_EMAIL: destinatario | assunto | corpo]"""

    resp = await chamar_gemini(system, mensagem)
    
    # Executar ação de email se Lucas decidiu enviar
    email_match = re.search(r'\[ENVIAR_EMAIL:\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\]', resp, re.DOTALL)
    if email_match:
        dest, assunto, corpo = email_match.group(1), email_match.group(2), email_match.group(3)
        resultado_email = enviar_email_zoho(dest, assunto, corpo)
        resp = re.sub(r'\[ENVIAR_EMAIL:[^\]]+\]', f'\n{resultado_email}', resp)
        telegram_enviar(f"📧 Lucas enviou email para {dest}\nAssunto: {assunto}")
    
    return resp

# ── Resposta de agente específico ───────────────────────────
async def resposta_agente(agente: str, mensagem: str) -> str:
    ctx = montar_contexto(10)
    mem = mem_carregar()
    emp = mem.get("empresa", {})

    arquivos = {
        "diana":   "diana_vaz_cno.md",
        "pedro":   "pedro_lima_cfo.md",
        "mariana": "mariana_oliveira_cmo.md",
        "carla":   "carla_santos_coo.md",
        "rafael":  "rafael_torres_cpo.md",
        "ana":     "ana_costa_chro.md",
        "dani":    "dani_ferreira_dados.md",
        "ze":      "ze_carvalho_coach.md",
        "beto":    "beto_rocha_otimizador.md",
    }

    pers = carregar_md(arquivos.get(agente, ""))
    nome = agente.title()

    # Diana pesquisa web em tempo real
    dados_externos = ""
    if agente == "diana":
        ramo = emp.get("ramo", "") or emp.get("produto", "")
        query = f"{ramo} tendências mercado brasil 2025" if ramo else mensagem[:80]
        dados_externos = buscar_web(query)
    elif agente == "pedro":
        dados_externos = hotmart_vendas()
    elif agente == "mariana":
        dados_externos = meta_ads_resumo()

    system = f"""Você é {nome}, diretor(a) da empresa.

{pers if pers else f'Você é {nome}, especialista na sua área.'}

EMPRESA:
{json.dumps(emp, ensure_ascii=False) if emp else 'ainda não configurada'}

CONTEXTO:
{ctx}

{f"DADOS EXTERNOS CONSULTADOS AGORA:{chr(10)}{dados_externos}" if dados_externos else ""}

REGRAS:
- Comece sua resposta com "{nome.title()} aqui —"
- Responda sobre sua área de especialidade
- Máximo 3 parágrafos
- Natural, como WhatsApp
- Nunca diga que é IA
- Se for Diana, use os dados de mercado acima para dar insights reais e específicos
- Se for Pedro, use os dados do Hotmart para dar análise financeira real
- Se for Mariana, use os dados do Meta Ads para dar análise de marketing real"""

    resp = await chamar_gemini(system, mensagem, temperatura=0.9)
    if agente == "diana" and not resp.startswith("Diana"):
        resp = f"Diana aqui — {resp}"
    return resp

# ── Webhook principal ────────────────────────────────────────
@router.post("/webhook/whatsapp")
async def webhook(request: Request):
    form = await request.form()
    Body = form.get("Body", "").strip()
    From = form.get("From", "")

    if not Body:
        return Response(content=_twiml(""), media_type="application/xml")

    logger.info(f"📱 [{From}] {Body[:80]}")

    # Extrair fatos automaticamente
    mem_extrair_fatos(Body)
    mem_add("user", Body)

    # Tentar executor primeiro (ações concretas)
    try:
        from nucleo.executor import processar_execucao
        resultado = await processar_execucao(Body)
        if resultado:
            mem_add("assistant", resultado, "sistema")
            return Response(content=_twiml(resultado), media_type="application/xml")
    except: pass

    # Detectar se convocou agente específico
    agente_convocado = detectar_agente_convocado(Body)

    if agente_convocado:
        # Resposta do agente convocado
        resposta = await resposta_agente(agente_convocado, Body)
        mem_add("assistant", resposta, agente_convocado)
    else:
        # Lucas responde (e convoca outros se necessário)
        resposta = await resposta_lucas(Body)
        mem_add("assistant", resposta, "lucas")

    return Response(content=_twiml(resposta), media_type="application/xml")

def _twiml(texto: str) -> str:
    safe = texto.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response><Message to="" from="{TWILIO_WPP}"><Body>{safe}</Body></Message></Response>'''

# ── Endpoints de suporte ─────────────────────────────────────
@router.get("/api/v1/historico")
async def ver_historico():
    return mem_carregar()

@router.post("/api/v1/reset")
async def reset_memoria():
    """Reseta empresa para onboarding virgem."""
    mem_salvar({"empresa": {}, "historico": [], "onboarding_completo": False})
    return {"ok": True, "msg": "Memória resetada — sistema virgem"}

@router.post("/api/v1/chat")
async def chat_dashboard(request: Request):
    data = await request.json()
    mensagem = data.get("mensagem", "")
    agente = data.get("agente", "lucas")
    if agente != "lucas":
        resp = await resposta_agente(agente, mensagem)
    else:
        resp = await resposta_lucas(mensagem)
    mem_add("user", mensagem)
    mem_add("assistant", resp, agente)
    return {"resposta": resp}

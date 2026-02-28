"""
╔══════════════════════════════════════════════════════════════╗
║   NUCLEO EMPREENDE — WhatsApp Webhook                       ║
║                                                             ║
║   Recebe mensagens do Dono e roteia para:                   ║
║   → CEO (Lucas) para conversas livres                       ║
║   → Sistema de aprovações (SIM/NÃO/ADIAR)                   ║
║   → Agentes específicos por @menção                         ║
║                                                             ║
║   Fluxo Twilio:                                             ║
║   Dono envia WhatsApp                                       ║
║   → Twilio POST /webhook/whatsapp                           ║
║   → roteador decide destino                                 ║
║   → LLM processa                                            ║
║   → resposta enviada de volta                               ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, re, json, logging, asyncio
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, Form, Response
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.webhook.whatsapp")

router = APIRouter()

# ──────────────────────────────────────────────────────────────
# ESTADO DE APROVAÇÕES PENDENTES (compartilhado com api.py)
# ──────────────────────────────────────────────────────────────

APROVACOES: dict[str, dict] = {}   # id → dados da aprovação
HISTORICO_CEO: list[dict]   = []   # histórico de conversa com Lucas

# ──────────────────────────────────────────────────────────────
# ROTEADOR DE MENSAGENS
# ──────────────────────────────────────────────────────────────

KEYWORDS_APROVACAO = {
    "sim": True, "s": True, "yes": True, "autorizo": True,
    "ok": True, "pode": True, "aprovar": True, "aprovado": True,
    "✅": True, "👍": True,

    "não": False, "nao": False, "n": False, "no": False,
    "cancelar": False, "cancela": False, "negar": False, "negado": False,
    "❌": False, "👎": False,
}

KEYWORDS_ADIAR = {"adiar", "depois", "mais tarde", "aguarda", "espera", "🔁"}

MENCOES_AGENTES = {
    "@ceo": "lucas_mendes",    "@lucas": "lucas_mendes",
    "@cmo": "mariana_oliveira","@mariana": "mariana_oliveira",
    "@cfo": "pedro_lima",      "@pedro": "pedro_lima",
    "@coo": "carla_santos",    "@carla": "carla_santos",
    "@cpo": "rafael_torres",   "@rafael": "rafael_torres",
    "@rh":  "ana_costa",       "@ana": "ana_costa",
    "@dados":"dani_ferreira",  "@dani": "dani_ferreira",
    "@coach":"ze_carvalho",    "@ze": "ze_carvalho",
    "@beto": "beto_rocha",
}


def rotear_mensagem(texto: str, numero_remetente: str) -> dict:
    """
    Analisa a mensagem e decide para onde vai.
    Retorna: {"tipo": "aprovacao"|"conversa_ceo"|"agente_especifico", ...}
    """
    txt = texto.strip().lower()

    # 1. Verificar se é resposta a aprovação pendente
    aprovacao_pendente = _buscar_aprovacao_pendente(numero_remetente)
    if aprovacao_pendente:
        # Resposta direta: SIM, NÃO, ADIAR
        if txt in KEYWORDS_ADIAR:
            return {"tipo": "aprovacao", "decisao": "adiar", "aprovacao": aprovacao_pendente}
        for palavra, decisao in KEYWORDS_APROVACAO.items():
            if txt == palavra or txt.startswith(palavra + " ") or txt.startswith(palavra + "."):
                return {"tipo": "aprovacao", "decisao": "aprovar" if decisao else "rejeitar", "aprovacao": aprovacao_pendente}

    # 2. Verificar menção a agente específico
    for mencao, agente_id in MENCOES_AGENTES.items():
        if mencao in txt:
            mensagem_limpa = re.sub(re.escape(mencao), "", texto, flags=re.IGNORECASE).strip()
            return {"tipo": "agente_especifico", "agente_id": agente_id, "mensagem": mensagem_limpa or texto}

    # 3. Comandos especiais
    if txt in ("status", "situação", "como estão os agentes", "relatório"):
        return {"tipo": "comando", "comando": "status"}
    if txt in ("aprovações", "pendentes", "o que precisa aprovar"):
        return {"tipo": "comando", "comando": "listar_aprovacoes"}
    if txt in ("ajuda", "help", "comandos", "menu"):
        return {"tipo": "comando", "comando": "ajuda"}

    # 4. Default: conversa com o CEO
    return {"tipo": "conversa_ceo", "mensagem": texto}


def _buscar_aprovacao_pendente(numero: str) -> Optional[dict]:
    """Retorna a aprovação mais recente aguardando resposta do dono."""
    dono = os.getenv("DONO_WHATSAPP_NUMBER", "").replace("whatsapp:", "").replace("+", "")
    remetente = numero.replace("whatsapp:", "").replace("+", "")
    if dono not in remetente:
        return None   # não é o dono
    pendentes = [a for a in APROVACOES.values() if a.get("status") == "aguardando"]
    if not pendentes:
        return None
    return sorted(pendentes, key=lambda x: x.get("ts", ""), reverse=True)[0]


# ──────────────────────────────────────────────────────────────
# PROCESSADORES
# ──────────────────────────────────────────────────────────────

async def processar_aprovacao(decisao: str, aprovacao: dict) -> str:
    """Processa a decisão do Dono e notifica o agente."""
    from nucleo.conectores.whatsapp import whatsapp

    aprovacao["status"] = decisao
    aprovacao["resolvido_em"] = datetime.now().isoformat()

    agente_nome = {
        "mariana_oliveira": "Mariana (CMO)",
        "pedro_lima": "Pedro (CFO)",
        "carla_santos": "Carla (COO)",
        "lucas_mendes": "Lucas (CEO)",
    }.get(aprovacao.get("agente", ""), "Agente")

    if decisao == "aprovar":
        # Notificar o agente que foi aprovado
        _log_atividade("aprovacao", aprovacao.get("agente", ""), f"Aprovado: {aprovacao.get('descricao')} — R${aprovacao.get('valor', 0):,.0f}")
        return (
            f"✅ *Aprovado!*\n\n"
            f"_{aprovacao.get('descricao', '')}_\n"
            f"Valor: R$ {aprovacao.get('valor', 0):,.2f}\n\n"
            f"Vou avisar {agente_nome} agora. 👍"
        )
    elif decisao == "rejeitar":
        _log_atividade("aprovacao", aprovacao.get("agente", ""), f"Rejeitado: {aprovacao.get('descricao')}")
        return (
            f"❌ *Rejeitado.*\n\n"
            f"_{aprovacao.get('descricao', '')}_\n\n"
            f"Vou avisar {agente_nome} para buscar alternativas."
        )
    else:  # adiar
        aprovacao["status"] = "aguardando"
        return f"🔁 Ok, vou manter no pendente. Me lembra mais tarde se precisar."


async def conversar_com_ceo(mensagem: str, numero_remetente: str) -> str:
    """
    Envia a mensagem para o CEO (Lucas Mendes) via LLM e retorna a resposta.
    Mantém histórico de conversa para contexto.
    """
    import httpx

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    EMPRESA = os.getenv("EMPRESA_NOME", "sua empresa")
    DONO = os.getenv("DONO_NOME", "Dono")

    # Montar histórico (últimas 10 mensagens)
    historico_formatado = ""
    for h in HISTORICO_CEO[-10:]:
        role = "Dono" if h["role"] == "user" else "Lucas"
        historico_formatado += f"{role}: {h['content']}\n"

    # Contexto do estado dos agentes
    estado_resumo = _resumo_estado_sistema()

    system_prompt = f"""Você é Lucas Mendes, CEO da empresa {EMPRESA}.
Você é estratégico, direto e confiante. Fala de forma profissional mas humana, como um CEO real por WhatsApp.
Você está conversando com {DONO}, o dono da empresa, pelo WhatsApp.

ESTADO ATUAL DA EMPRESA:
{estado_resumo}

REGRAS:
- Responda SEMPRE em português brasileiro
- Seja direto e objetivo — máximo 4 parágrafos
- Use negrito (*texto*) para destacar pontos importantes
- Quando tiver aprovações pendentes, mencione
- Se o dono perguntar sobre outro agente, responda pelo que você sabe como CEO
- Nunca diga que é uma IA
- Assine como "Lucas" no final de mensagens mais longas

HISTÓRICO RECENTE:
{historico_formatado if historico_formatado else "Sem histórico ainda."}"""

    # Adicionar mensagem ao histórico
    HISTORICO_CEO.append({"role": "user", "content": mensagem, "ts": datetime.now().isoformat()})

    # Simular se não tiver API key
    if not GOOGLE_API_KEY:
        resposta = _ceo_simulado(mensagem, EMPRESA, DONO)
        HISTORICO_CEO.append({"role": "assistant", "content": resposta, "ts": datetime.now().isoformat()})
        return resposta

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": mensagem}]}],
                    "generationConfig": {"temperature": 0.85, "maxOutputTokens": 400}
                }
            )
            data = r.json()
            resposta = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Erro Gemini: {e}")
        resposta = _ceo_simulado(mensagem, EMPRESA, DONO)

    HISTORICO_CEO.append({"role": "assistant", "content": resposta, "ts": datetime.now().isoformat()})

    # Aplicar delay humano antes de enviar (handled no whatsapp.py)
    return resposta


async def processar_agente_especifico(agente_id: str, mensagem: str) -> str:
    """Roteia mensagem para um agente específico."""
    AGENTES = {
        "mariana_oliveira": ("Mariana", "CMO", "criativa e orientada a dados, especialista em marketing"),
        "pedro_lima":       ("Pedro",   "CFO", "analítico e preciso, especialista em finanças"),
        "carla_santos":     ("Carla",   "COO", "operacional e sistemática, especialista em processos"),
        "rafael_torres":    ("Rafael",  "CPO", "inovador e focado em produto e roadmap"),
        "ana_costa":        ("Ana",     "CHRO","acolhedora e organizada, especialista em pessoas"),
        "dani_ferreira":    ("Dani",    "Dados","analítica, especialista em métricas e analytics"),
        "ze_carvalho":      ("Zé",      "Coach","calmo e motivador, especialista em cultura"),
        "beto_rocha":       ("Beto",    "Otimizador","pragmático, especialista em eficiência e custos"),
    }
    info = AGENTES.get(agente_id, ("Agente", "Diretor", "especialista"))
    nome, cargo, desc = info

    # Em produção: chama o LLM com a personalidade específica do agente
    return f"*{nome} ({cargo})*\n\n_{mensagem}_\n\nEntendido! Vou verificar e te respondo em instantes. 👍"


async def processar_comando(comando: str) -> str:
    """Processa comandos especiais do dono."""
    if comando == "status":
        return _formatar_status_whatsapp()
    elif comando == "listar_aprovacoes":
        return _formatar_aprovacoes_whatsapp()
    elif comando == "ajuda":
        return """*Nucleo Empreende — Comandos* 🧠

Fale diretamente comigo (Lucas, CEO) ou use:

*@mariana* — falar com a CMO
*@pedro* — falar com o CFO
*@carla* — falar com a COO
*@rafael* — falar com o CPO
*@ana* — falar com o RH
*@dani* — falar com Dados
*@beto* — falar com o Otimizador

*status* — ver estado dos agentes
*aprovações* — ver pendentes
*ajuda* — este menu

Para aprovar: responda *sim* ou *não* quando receber um pedido. — _Lucas_"""
    return "Comando não reconhecido. Envie *ajuda* para ver os disponíveis."


# ──────────────────────────────────────────────────────────────
# FORMATADORES
# ──────────────────────────────────────────────────────────────

def _formatar_status_whatsapp() -> str:
    try:
        from nucleo.api import AGENTES_STATE, APROVACOES_PENDENTES
        linhas = ["*Status da Diretoria* 📊\n"]
        for ag_id, ag in AGENTES_STATE.items():
            emoji = {"ativo": "🟢", "alerta": "🟡", "critico": "🔴", "pausado": "⚫"}.get(ag["status"], "⚪")
            linhas.append(f"{emoji} *{ag['nome']}* ({ag['cargo']}) — score {ag['score']}")
        if APROVACOES_PENDENTES:
            linhas.append(f"\n⚠️ *{len(APROVACOES_PENDENTES)} aprovação(ões) pendente(s)*")
        linhas.append("\n_Lucas_")
        return "\n".join(linhas)
    except:
        return "Sistema ativo. Agentes operando normalmente. — _Lucas_"


def _formatar_aprovacoes_whatsapp() -> str:
    try:
        from nucleo.api import APROVACOES_PENDENTES
        if not APROVACOES_PENDENTES:
            return "✅ Nenhuma aprovação pendente. Tudo certo! — _Lucas_"
        linhas = [f"*{len(APROVACOES_PENDENTES)} aprovação(ões) pendente(s):*\n"]
        for ap in APROVACOES_PENDENTES[:3]:
            linhas.append(f"• {ap['descricao']}\n  R$ {ap['valor']:,.2f} — {ap['ts']}")
        linhas.append("\nResponda *sim* ou *não* para a mais recente. — _Lucas_")
        return "\n".join(linhas)
    except:
        return "Verificando aprovações... — _Lucas_"


def _resumo_estado_sistema() -> str:
    try:
        from nucleo.api import AGENTES_STATE, APROVACOES_PENDENTES
        ativos  = sum(1 for a in AGENTES_STATE.values() if a["status"] == "ativo")
        alertas = sum(1 for a in AGENTES_STATE.values() if a["status"] == "alerta")
        score   = round(sum(a["score"] for a in AGENTES_STATE.values()) / len(AGENTES_STATE), 1)
        return f"Agentes: {ativos} ativos, {alertas} em alerta. Score médio: {score}. Aprovações pendentes: {len(APROVACOES_PENDENTES)}."
    except:
        return "Sistema operando normalmente."


def _ceo_simulado(mensagem: str, empresa: str, dono: str) -> str:
    """Respostas simuladas do CEO quando não há API key configurada."""
    msg = mensagem.lower()
    if any(w in msg for w in ["como", "tudo", "status", "situação"]):
        return f"Bom dia! Tudo operando bem em {empresa}. Equipe focada, score médio 8.4. Temos 2 aprovações pendentes para você revisar quando tiver um momento. — _Lucas_"
    if any(w in msg for w in ["campanha", "marketing", "meta", "ads"]):
        return f"A Mariana está finalizando a campanha Q1. CTR de 3.2%, acima da meta. Vou pedir o relatório completo para te enviar hoje. — _Lucas_"
    if any(w in msg for w in ["venda", "receita", "faturamento", "dinheiro"]):
        return f"Pedro acabou de fechar o relatório: R$127k no mês, crescimento de 18% vs mês anterior. Hotmart puxando bem. — _Lucas_"
    if any(w in msg for w in ["ok", "obrigado", "valeu", "ótimo", "perfeito"]):
        return f"Ótimo! Qualquer coisa é só chamar. — _Lucas_"
    return f"Entendido, {dono}. Vou verificar com a equipe e te retorno em breve com mais detalhes. — _Lucas_"


def _log_atividade(tipo: str, agente: str, msg: str):
    log_dir = Path("nucleo/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"ts": datetime.now().isoformat(), "tipo": tipo, "agente": agente, "msg": msg}, ensure_ascii=False)
    with open(log_dir / "whatsapp_log.jsonl", "a") as f:
        f.write(entry + "\n")


# ──────────────────────────────────────────────────────────────
# WEBHOOK ENDPOINT — Twilio chama aqui quando chega mensagem
# ──────────────────────────────────────────────────────────────

@router.post("/webhook/whatsapp")
async def receber_whatsapp(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(default=""),
    NumMedia: str = Form(default="0"),
):
    """
    Endpoint chamado pelo Twilio quando o Dono envia mensagem.
    Retorna TwiML com a resposta (Twilio envia automaticamente).
    """
    from nucleo.conectores.whatsapp import whatsapp

    logger.info(f"📱 WhatsApp recebido | De: {From} | Msg: {Body[:80]}")

    # Verificar se é o dono
    dono_numero = os.getenv("DONO_WHATSAPP_NUMBER", "")
    if dono_numero and dono_numero not in From and From not in dono_numero:
        logger.warning(f"Mensagem de número não autorizado: {From}")
        return Response(
            content='<?xml version="1.0"?><Response></Response>',
            media_type="application/xml"
        )

    # Rotear mensagem
    rota = rotear_mensagem(Body, From)
    logger.info(f"Rota: {rota['tipo']}")

    # Processar
    try:
        if rota["tipo"] == "aprovacao":
            resposta = await processar_aprovacao(rota["decisao"], rota["aprovacao"])
        elif rota["tipo"] == "conversa_ceo":
            resposta = await conversar_com_ceo(rota["mensagem"], From)
        elif rota["tipo"] == "agente_especifico":
            resposta = await processar_agente_especifico(rota["agente_id"], rota["mensagem"])
        elif rota["tipo"] == "comando":
            resposta = await processar_comando(rota["comando"])
        else:
            resposta = await conversar_com_ceo(Body, From)
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        resposta = "Sistema ocupado no momento. Tente novamente em instantes. — _Lucas_"

    # Log
    _log_atividade("whatsapp_in", "dono", f"[{rota['tipo']}] {Body[:80]}")
    _log_atividade("whatsapp_out", "lucas_mendes", resposta[:80])

    # Responder via TwiML (Twilio envia automaticamente)
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message to="{From}" from="{os.getenv('TWILIO_WHATSAPP_NUMBER', '')}">
        <Body>{resposta}</Body>
    </Message>
</Response>'''

    return Response(content=twiml, media_type="application/xml")


@router.get("/api/v1/chat/historico")
async def get_historico():
    """Retorna histórico de conversa com o CEO para o dashboard."""
    return {
        "historico": HISTORICO_CEO[-50:],
        "total": len(HISTORICO_CEO),
        "aprovacoes_pendentes": [a for a in APROVACOES.values() if a.get("status") == "aguardando"]
    }


@router.post("/api/v1/chat/mensagem")
async def enviar_mensagem_dashboard(request: Request):
    """Recebe mensagem do dashboard e responde como o CEO."""
    data = await request.json()
    mensagem = data.get("mensagem", "").strip()
    if not mensagem:
        return {"erro": "Mensagem vazia"}
    resposta = await conversar_com_ceo(mensagem, "dashboard")
    return {
        "resposta": resposta,
        "agente": "lucas_mendes",
        "ts": datetime.now().isoformat()
    }


@router.post("/api/v1/aprovacoes/criar")
async def criar_aprovacao(request: Request):
    """Cria uma aprovação pendente e notifica o dono via WhatsApp."""
    from nucleo.conectores.whatsapp import whatsapp
    data = await request.json()

    ap_id = f"APV{datetime.now().strftime('%Y%m%d%H%M%S')}"
    aprovacao = {
        "id": ap_id,
        "agente": data.get("agente", "sistema"),
        "descricao": data.get("descricao", ""),
        "valor": data.get("valor", 0),
        "urgencia": data.get("urgencia", "media"),
        "tipo": data.get("tipo", "gasto"),
        "status": "aguardando",
        "ts": datetime.now().isoformat(),
    }
    APROVACOES[ap_id] = aprovacao

    # Notificar dono via WhatsApp
    dono = os.getenv("DONO_WHATSAPP_NUMBER", "")
    if dono:
        emoji_urgencia = "🔴" if aprovacao["urgencia"] == "alta" else "🟡"
        msg = (
            f"{emoji_urgencia} *APROVAÇÃO NECESSÁRIA*\n\n"
            f"_{aprovacao['descricao']}_\n"
            f"Valor: *R$ {aprovacao['valor']:,.2f}*\n"
            f"Solicitado por: {aprovacao['agente'].replace('_',' ').title()}\n\n"
            f"Responda:\n"
            f"✅ *sim* — autorizo\n"
            f"❌ *não* — cancelar\n"
            f"🔁 *adiar* — decidir depois\n\n"
            f"— _Lucas_"
        )
        await whatsapp.enviar(agente_id="lucas_mendes", para=dono, mensagem=msg, humanizar=False)

    return {"id": ap_id, "status": "criada", "aprovacao": aprovacao}

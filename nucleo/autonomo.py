"""
Nucleo Empreende — Motor Autônomo
Cada agente pensa, decide e age sozinho no horário certo.
Loop: OBSERVAR → PENSAR → DECIDIR → AGIR → REPORTAR
"""
import os, json, asyncio, logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()
logger = logging.getLogger("nucleo.autonomo")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Importar ferramentas ─────────────────────────────────────
from nucleo.ferramentas import (
    buscar_web, enviar_email_zoho, telegram_enviar,
    hotmart_vendas, meta_ads_resumo
)

# ── Gemini async ─────────────────────────────────────────────
async def gemini(system: str, prompt: str, tokens: int = 600) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": tokens}
                }
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini erro: {e}")
        return ""

# ── Carregar memória da empresa ──────────────────────────────
def carregar_empresa() -> dict:
    mem_file = BASE_DIR / "nucleo" / "data" / "memoria.json"
    if mem_file.exists():
        try:
            return json.loads(mem_file.read_text()).get("empresa", {})
        except: pass
    return {}

# ── Salvar log de ações autônomas ────────────────────────────
def log_acao(agente: str, acao: str, resultado: str):
    log_file = BASE_DIR / "nucleo" / "data" / "acoes_autonomas.json"
    log_file.parent.mkdir(exist_ok=True)
    try:
        logs = json.loads(log_file.read_text()) if log_file.exists() else []
    except: logs = []
    logs.append({
        "ts": datetime.now().isoformat(),
        "agente": agente,
        "acao": acao,
        "resultado": resultado[:300]
    })
    logs = logs[-200:]  # manter últimas 200 ações
    log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2))

# ── Notificar dono ───────────────────────────────────────────
async def notificar_dono(mensagem: str, via: str = "telegram"):
    """Envia notificação pro dono via Telegram ou WhatsApp."""
    if via == "telegram":
        result = telegram_enviar(mensagem)
        logger.info(f"Notificação: {result}")
    elif via == "whatsapp":
        # Via Twilio WhatsApp
        try:
            from twilio.rest import Client
            client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
            client.messages.create(
                body=mensagem,
                from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
                to=os.getenv("DONO_WHATSAPP_NUMBER")
            )
        except Exception as e:
            logger.error(f"WhatsApp erro: {e}")

# ═══════════════════════════════════════════════════════════════
# CICLOS AUTÔNOMOS POR AGENTE
# ═══════════════════════════════════════════════════════════════

async def ciclo_diana():
    """Diana — Inteligência de Mercado — Roda toda manhã às 7h"""
    logger.info("🔍 Diana iniciando ciclo autônomo...")
    empresa = carregar_empresa()
    ramo = empresa.get("ramo", "") or empresa.get("produto", "")

    # 1. OBSERVAR — buscar dados de mercado
    query1 = f"{ramo} tendências mercado brasil 2026" if ramo else "tendências negócios digitais brasil 2026"
    query2 = f"{ramo} concorrentes novidades" if ramo else "startups brasil 2026 inovação"
    query3 = "ferramentas inteligencia artificial novidades 2026"

    mercado   = buscar_web(query1)
    concorr   = buscar_web(query2)
    ia_tools  = buscar_web(query3)

    # 2. PENSAR — analisar e extrair insights
    system = """Você é Diana, CNO (Chief Network Officer) de uma empresa brasileira.
Sua missão: transformar dados de mercado em insights acionáveis para o CEO.
Seja direta, específica e prática. Máximo 5 insights numerados."""

    prompt = f"""
Empresa: {json.dumps(empresa, ensure_ascii=False) if empresa else 'em configuração'}
Data: {datetime.now().strftime('%d/%m/%Y')}

DADOS DE MERCADO COLETADOS:
Tendências: {mercado[:600]}
Concorrência: {concorr[:400]}
Novas ferramentas IA: {ia_tools[:400]}

Gere um briefing executivo com:
1. 3 oportunidades imediatas para o negócio
2. 2 ameaças ou mudanças que merecem atenção
3. 1 ferramenta de IA nova que pode ser incorporada
4. Recomendação prioritária para hoje

Formato: WhatsApp, direto ao ponto."""

    briefing = await gemini(system, prompt, 500)

    # 3. AGIR — enviar briefing
    if briefing:
        msg = f"🔍 *Diana — Briefing de Mercado {datetime.now().strftime('%d/%m')}*\n\n{briefing}"
        await notificar_dono(msg)
        log_acao("diana", "briefing_mercado", briefing)
        logger.info("✅ Diana: briefing enviado")
    
    return briefing

async def ciclo_pedro():
    """Pedro — CFO — Roda todo dia às 8h e às 18h"""
    logger.info("💰 Pedro iniciando ciclo autônomo...")
    empresa = carregar_empresa()

    # 1. OBSERVAR — dados financeiros
    vendas = hotmart_vendas(7)  # última semana
    vendas_mes = hotmart_vendas(30)

    # 2. PENSAR — análise financeira
    system = """Você é Pedro, CFO. Analisa dados financeiros e age quando necessário.
Se detectar queda nas vendas, alerta imediatamente. Se estiver bem, reporta brevemente.
Seja objetivo. Use números reais."""

    prompt = f"""
Empresa: {json.dumps(empresa, ensure_ascii=False) if empresa else 'em configuração'}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

DADOS FINANCEIROS:
Última semana: {vendas}
Último mês: {vendas_mes}

Analise:
1. Tendência (subindo/caindo/estável)?
2. Algum alerta urgente?
3. Recomendação de ação para hoje?

Seja direto. Máximo 3 parágrafos."""

    analise = await gemini(system, prompt, 300)

    # 3. DECIDIR — só notifica se há algo relevante
    if analise and any(word in analise.lower() for word in ["alerta", "queda", "urgente", "atenção", "preocupante", "crescimento", "recorde"]):
        msg = f"💰 *Pedro — Alerta Financeiro {datetime.now().strftime('%d/%m %H:%M')}*\n\n{analise}"
        await notificar_dono(msg)
        log_acao("pedro", "alerta_financeiro", analise)
        logger.info("✅ Pedro: alerta enviado")
    else:
        log_acao("pedro", "check_financeiro", analise or "sem dados")
        logger.info("✅ Pedro: check financeiro — sem alertas")

    return analise

async def ciclo_mariana():
    """Mariana — CMO — Roda toda manhã às 8h30"""
    logger.info("📣 Mariana iniciando ciclo autônomo...")
    empresa = carregar_empresa()

    # 1. OBSERVAR
    ads = meta_ads_resumo()
    ramo = empresa.get("ramo", "negócios digitais")
    mkt_trends = buscar_web(f"marketing digital {ramo} estratégias 2026")

    # 2. PENSAR
    system = """Você é Mariana, CMO. Analisa performance de marketing e sugere ações.
Foco em ROI, engajamento e crescimento. Prática e orientada a dados."""

    prompt = f"""
Empresa: {json.dumps(empresa, ensure_ascii=False) if empresa else 'em configuração'}

PERFORMANCE META ADS:
{ads}

TENDÊNCIAS DE MARKETING:
{mkt_trends[:500]}

Analise e responda:
1. Performance atual das campanhas (boa/ruim/regular)?
2. O que otimizar imediatamente?
3. Uma estratégia nova baseada nas tendências?

Direto ao ponto, máximo 3 parágrafos."""

    analise = await gemini(system, prompt, 350)

    if analise:
        msg = f"📣 *Mariana — Relatório Marketing {datetime.now().strftime('%d/%m')}*\n\n{analise}"
        await notificar_dono(msg)
        log_acao("mariana", "relatorio_marketing", analise)
        logger.info("✅ Mariana: relatório enviado")

    return analise

async def ciclo_lucas():
    """Lucas — CEO — Roda toda segunda-feira às 9h com briefing semanal"""
    logger.info("👔 Lucas iniciando ciclo autônomo semanal...")
    empresa = carregar_empresa()

    # Ler log de ações da semana
    log_file = BASE_DIR / "nucleo" / "data" / "acoes_autonomas.json"
    acoes_semana = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text())
            acoes_semana = logs[-50:]  # últimas 50 ações
        except: pass

    system = """Você é Lucas, CEO. Todo início de semana você consolida o trabalho da diretoria
e define as prioridades estratégicas. Seja executivo, direto e motivador."""

    prompt = f"""
Empresa: {json.dumps(empresa, ensure_ascii=False) if empresa else 'em configuração'}
Data: {datetime.now().strftime('%d/%m/%Y')} — Início de semana

AÇÕES DA DIRETORIA NA ÚLTIMA SEMANA:
{json.dumps(acoes_semana[-20:], ensure_ascii=False, indent=2)[:1000]}

Gere o briefing executivo semanal:
1. Resumo do que a diretoria fez
2. 3 prioridades desta semana
3. Uma decisão estratégica que você tomou
4. Mensagem motivacional para o dono

Formato WhatsApp, máximo 4 parágrafos."""

    briefing = await gemini(system, prompt, 500)

    if briefing:
        msg = f"👔 *Lucas — Briefing Executivo Semanal {datetime.now().strftime('%d/%m')}*\n\n{briefing}"
        await notificar_dono(msg)
        log_acao("lucas", "briefing_semanal", briefing)
        logger.info("✅ Lucas: briefing semanal enviado")

    return briefing

async def ciclo_conhecimento():
    """Todos os agentes atualizam seu conhecimento — Roda toda semana"""
    logger.info("🧠 Ciclo de atualização de conhecimento iniciado...")
    
    # Buscar atualizações em 4 frentes
    atualizacoes = {
        "mercado":     buscar_web("tendências mercado digital brasil 2026 novidades"),
        "legislacao":  buscar_web("legislação empresas digitais brasil 2026 mudanças"),
        "ia_tools":    buscar_web("novas ferramentas inteligência artificial lançamentos 2026"),
        "produtos":    buscar_web("novos produtos saas brasil startups 2026"),
    }

    system = """Você é o sistema de inteligência do Nucleo Empreende.
Sua função: transformar atualizações de mercado em aprendizados para a diretoria.
Seja específico, cite ferramentas reais, leis reais, tendências reais."""

    prompt = f"""
Data: {datetime.now().strftime('%d/%m/%Y')}

ATUALIZAÇÕES COLETADAS:

📊 Mercado: {atualizacoes['mercado'][:400]}
⚖️ Legislação: {atualizacoes['legislacao'][:400]}  
🤖 Novas ferramentas IA: {atualizacoes['ia_tools'][:400]}
🚀 Novos produtos: {atualizacoes['produtos'][:400]}

Gere um relatório de atualização de conhecimento com:
1. 3 aprendizados de mercado que a diretoria deve saber
2. 1 mudança legal ou regulatória relevante
3. 2 ferramentas de IA novas que merecem avaliação
4. 1 oportunidade de novo produto ou serviço

Formato executivo, direto."""

    relatorio = await gemini(system, prompt, 600)

    if relatorio:
        # Salvar no knowledge base
        kb_file = BASE_DIR / "nucleo" / "data" / "knowledge_base.json"
        try:
            kb = json.loads(kb_file.read_text()) if kb_file.exists() else []
        except: kb = []
        
        kb.append({
            "data": datetime.now().isoformat(),
            "tipo": "atualizacao_semanal",
            "conteudo": relatorio,
            "fontes": atualizacoes
        })
        kb = kb[-52:]  # 1 ano de atualizações
        kb_file.write_text(json.dumps(kb, ensure_ascii=False, indent=2))

        msg = f"🧠 *Atualização de Conhecimento — {datetime.now().strftime('%d/%m')}*\n\n{relatorio}"
        await notificar_dono(msg)
        log_acao("sistema", "atualizacao_conhecimento", relatorio)
        logger.info("✅ Knowledge base atualizado")

    return relatorio

# ═══════════════════════════════════════════════════════════════
# SCHEDULER — Agenda e dispara cada ciclo
# ═══════════════════════════════════════════════════════════════

async def scheduler():
    """Motor principal — verifica horários e dispara ciclos."""
    logger.info("⚙️ Scheduler autônomo iniciado")
    
    ultimo = {}  # controle de última execução por agente

    while True:
        agora = datetime.now()
        hora  = agora.hour
        minuto = agora.minute
        dia_semana = agora.weekday()  # 0=segunda, 6=domingo

        # Diana — todo dia às 7:00
        if hora == 7 and minuto == 0 and ultimo.get("diana") != agora.date():
            try:
                await ciclo_diana()
                ultimo["diana"] = agora.date()
            except Exception as e:
                logger.error(f"Diana erro: {e}")

        # Pedro — todo dia às 8:00 e 18:00
        chave_pedro = f"pedro_{agora.date()}_{hora}"
        if hora in [8, 18] and minuto == 0 and ultimo.get("pedro") != chave_pedro:
            try:
                await ciclo_pedro()
                ultimo["pedro"] = chave_pedro
            except Exception as e:
                logger.error(f"Pedro erro: {e}")

        # Mariana — todo dia às 8:30
        if hora == 8 and minuto == 30 and ultimo.get("mariana") != agora.date():
            try:
                await ciclo_mariana()
                ultimo["mariana"] = agora.date()
            except Exception as e:
                logger.error(f"Mariana erro: {e}")

        # Lucas — toda segunda-feira às 9:00
        if dia_semana == 0 and hora == 9 and minuto == 0 and ultimo.get("lucas") != agora.date():
            try:
                await ciclo_lucas()
                ultimo["lucas"] = agora.date()
            except Exception as e:
                logger.error(f"Lucas erro: {e}")

        # Conhecimento — todo domingo às 20:00
        if dia_semana == 6 and hora == 20 and minuto == 0 and ultimo.get("conhecimento") != agora.date():
            try:
                await ciclo_conhecimento()
                ultimo["conhecimento"] = agora.date()
            except Exception as e:
                logger.error(f"Conhecimento erro: {e}")

        # Aguarda 1 minuto antes do próximo check
        await asyncio.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scheduler())

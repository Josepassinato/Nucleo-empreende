"""
╔══════════════════════════════════════════════════════════════╗
║   INCREASE TEAM — Rotinas Diárias de Todos os Agentes    ║
║                                                             ║
║   Cada agente tem 2-3 ciclos por dia na sua área.           ║
║   Ninguém espera reunião para agir.                         ║
║                                                             ║
║   HORÁRIOS:                                                 ║
║   07:00 Diana   — briefing de mercado                       ║
║   07:15 Lucas   — leitura dos briefings + prioridade do dia ║
║   07:30 Dani    — coleta de dados e métricas                ║
║   08:00 Pedro   — check financeiro manhã                    ║
║   08:30 Mariana — performance Meta Ads                      ║
║   08:45 Carla   — check operacional                         ║
║   09:00 Rafael  — métricas de produto                       ║
║   09:30 Ana     — energia e produtividade do dono           ║
║   10:00 Beto    — auditoria de custos                       ║
║   10:30 Zé      — check de bem-estar e decisões travadas    ║
║   11:00 Dani    — anomalias e alertas                       ║
║   12:00 Mariana — ação de marketing do dia                  ║
║   13:00 Pedro   — revisão de custos                         ║
║   14:00 Diana   — inteligência competitiva                  ║
║   14:30 Rafael  — priorização de features                   ║
║   15:00 Beto    — quick wins do dia                         ║
║   15:30 Ana     — revisão de delegação e automação          ║
║   16:00 Dani    — relatório de métricas para shared context ║
║   16:30 Zé      — destravar loops de decisão               ║
║   17:00 Carla   — check de SLAs e entregas                  ║
║   17:30 Mariana — relatório de leads                        ║
║   18:00 Pedro   — fechamento financeiro do dia              ║
║   18:30 Lucas   — fechamento executivo + cobrança 5W2H      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, asyncio, logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()
logger = logging.getLogger("nucleo.rotinas")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Helpers compartilhados ────────────────────────────────────────

async def _gemini(system: str, prompt: str, tokens: int = 400) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents":           [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig":   {"temperature": 0.75, "maxOutputTokens": tokens}
                }
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini erro: {e}")
        return ""

def _empresa() -> dict:
    f = BASE_DIR / "nucleo" / "data" / "memoria.json"
    try: return json.loads(f.read_text()).get("empresa", {}) if f.exists() else {}
    except: return {}

def _shared_ctx() -> str:
    f = BASE_DIR / "nucleo" / "data" / "contexto_compartilhado.json"
    try:
        ctx = json.loads(f.read_text()) if f.exists() else {}
        linhas = []
        for ag, dados in ctx.items():
            if ag.startswith("_"): continue
            for chave, info in list(dados.items())[:2]:
                linhas.append(f"[{ag.upper()}] {chave}: {info.get('valor','')[:100]}")
        return "\n".join(linhas)
    except: return ""

def _atualizar_shared(agente: str, chave: str, valor: str):
    f = BASE_DIR / "nucleo" / "data" / "contexto_compartilhado.json"
    try:
        ctx = json.loads(f.read_text()) if f.exists() else {}
        ctx.setdefault(agente, {})[chave] = {"valor": valor[:400], "ts": datetime.now().isoformat()}
        ctx["_atualizado"] = datetime.now().isoformat()
        f.write_text(json.dumps(ctx, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"Shared ctx write erro: {e}")

def _log(agente: str, acao: str, resultado: str):
    f = BASE_DIR / "nucleo" / "data" / "acoes_autonomas.json"
    f.parent.mkdir(exist_ok=True)
    try: logs = json.loads(f.read_text()) if f.exists() else []
    except: logs = []
    logs.append({"ts": datetime.now().isoformat(), "agente": agente, "acao": acao, "resultado": resultado[:300]})
    logs = logs[-500:]
    f.write_text(json.dumps(logs, ensure_ascii=False, indent=2))

def _pendencias_5w2h() -> str:
    """Lê compromissos pendentes das atas."""
    salas_dir = BASE_DIR / "nucleo" / "data" / "salas"
    pendencias = []
    if not salas_dir.exists(): return ""
    for arq in sorted(salas_dir.glob("*.json"), reverse=True)[:10]:
        try:
            sala = json.loads(arq.read_text())
            if sala.get("status") == "encerrada":
                decisao = sala.get("decisao_final", "")
                if "QUEM:" in decisao:
                    for linha in decisao.split("\n"):
                        if "QUEM:" in linha:
                            responsavel = linha.split("QUEM:")[-1].strip()
                        if "O QUÊ:" in linha or "O QUE:" in linha:
                            tarefa = linha.split(":")[-1].strip()
                            pendencias.append(f"• {responsavel}: {tarefa[:80]}")
        except: pass
    return "\n".join(pendencias[:10]) if pendencias else "Nenhuma pendência registrada."

async def _notificar(msg: str):
    """Notifica via WhatsApp (preferencial) ou Telegram."""
    try:
        from nucleo.autonomo import notificar_dono
        await notificar_dono(msg, via="whatsapp")
    except:
        try:
            from nucleo.ferramentas import telegram_enviar
            telegram_enviar(msg)
        except: pass

# ═══════════════════════════════════════════════════════════════════
# DIANA — Chief Network Officer
# 07:00 Briefing de mercado  |  14:00 Inteligência competitiva
# ═══════════════════════════════════════════════════════════════════

async def diana_briefing_mercado():
    """07:00 — Diana coleta tendências e abre o dia da diretoria."""
    logger.info("🔍 Diana 07:00 — briefing de mercado")
    emp = _empresa()
    ramo = emp.get("ramo","") or emp.get("produto","") or "educação IA e agentes de negócio"
    
    from nucleo.ferramentas import buscar_web
    mercado  = buscar_web(f"{ramo} tendências brasil 2026")
    concorr  = buscar_web(f"concorrentes {ramo} brasil lançamentos")
    ia_tools = buscar_web("ferramentas IA novidades negócios 2026")

    analise = await _gemini(
        "Você é Diana, CNO. Transforma dados de mercado em inteligência acionável. Seja específica com números e nomes reais.",
        f"Empresa: {json.dumps(emp, ensure_ascii=False)}\nData: {datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"Mercado: {mercado[:500]}\nConcorrentes: {concorr[:400]}\nIA Tools: {ia_tools[:300]}\n\n"
        "Retorne:\n1. Top 3 oportunidades DO DIA (com ação concreta)\n2. 1 ameaça urgente\n"
        "3. 1 ferramenta IA nova relevante\n4. Sua recomendação prioritária para hoje\nFormato WhatsApp.", 500
    )
    if analise:
        _atualizar_shared("diana", "briefing_mercado_hoje", analise[:300])
        await _notificar(f"🔍 *Diana — Mercado {datetime.now().strftime('%d/%m')}*\n\n{analise}")
        _log("diana", "briefing_mercado", analise)

async def diana_inteligencia_competitiva():
    """14:00 — Diana monitora concorrentes e atualiza shared context."""
    logger.info("🔍 Diana 14:00 — inteligência competitiva")
    emp = _empresa()
    from nucleo.ferramentas import buscar_web
    concorr = buscar_web("Hotmart Kiwify Eduzz cursos IA empreendedores brasil novidades")
    diferenciais = buscar_web("VibeSchool 12Brain increase team diferencial")

    analise = await _gemini(
        "Você é Diana, CNO. Analise movimentos da concorrência com foco em ameaças e oportunidades.",
        f"Empresa: {json.dumps(emp)}\nConcorrentes hoje: {concorr[:600]}\n\n"
        "Identifique: 1. O que os concorrentes fizeram HOJE? 2. Nosso diferencial ainda é defensável? "
        "3. Alguma oportunidade de posicionamento? Seja direta.", 350
    )
    if analise:
        _atualizar_shared("diana", "inteligencia_competitiva", analise[:300])
        _log("diana", "inteligencia_competitiva", analise)

# ═══════════════════════════════════════════════════════════════════
# LUCAS — CEO
# 07:15 Leitura + prioridade  |  09:00 Decisão do dia  |  18:30 Fechamento
# ═══════════════════════════════════════════════════════════════════

async def lucas_leitura_manha():
    """07:15 — Lucas lê todos os briefings e define a prioridade do dia."""
    logger.info("👔 Lucas 07:15 — leitura de briefings")
    emp = _empresa()
    ctx = _shared_ctx()
    pendencias = _pendencias_5w2h()

    decisao = await _gemini(
        "Você é Lucas, CEO da Increase Future Tech. Todo dia às 7:15 você lê o que a diretoria produziu "
        "e define UMA prioridade executiva para o dia. Seja direto e firme.",
        f"Empresa: {json.dumps(emp)}\n\nO QUE A DIRETORIA DESCOBRIU:\n{ctx}\n\n"
        f"PENDÊNCIAS 5W2H:\n{pendencias}\n\n"
        f"Data: {datetime.now().strftime('%d/%m/%Y %A')}\n\n"
        "Defina:\n1. A UMA coisa mais importante que precisa acontecer HOJE\n"
        "2. Quem é o responsável\n3. Como você vai saber que foi feito\n"
        "4. Alguma cobrança urgente de pendência?\nFormato WhatsApp. Máximo 4 frases.", 400
    )
    if decisao:
        _atualizar_shared("lucas", "prioridade_do_dia", decisao[:300])
        await _notificar(f"👔 *Lucas — Prioridade do Dia {datetime.now().strftime('%d/%m')}*\n\n{decisao}")
        _log("lucas", "prioridade_dia", decisao)

async def lucas_decisao_dia():
    """09:00 — Lucas toma 1 decisão concreta baseada nos dados da manhã."""
    logger.info("👔 Lucas 09:00 — decisão do dia")
    emp = _empresa()
    ctx = _shared_ctx()

    decisao = await _gemini(
        "Você é Lucas, CEO. Às 9h você toma UMA decisão executiva baseada nos dados coletados até agora. "
        "Decisão sem dado não é decisão — é chute. Se faltar dado, declare o que precisa antes de decidir.",
        f"Empresa: {json.dumps(emp)}\nContexto da diretoria:\n{ctx}\n\n"
        "Com base nesses dados, tome UMA decisão concreta agora:\n"
        "- O que você decide?\n- Por que agora?\n- Quem executa?\n- Prazo?\n"
        "Se não tiver dados suficientes, declare o que precisa saber primeiro.\nMáximo 4 frases.", 350
    )
    if decisao:
        _atualizar_shared("lucas", "decisao_hoje", decisao[:300])
        _log("lucas", "decisao_executiva", decisao)

async def lucas_fechamento_dia():
    """18:30 — Lucas fecha o dia: o que avançou, o que travou, quem está atrasado."""
    logger.info("👔 Lucas 18:30 — fechamento do dia")
    emp = _empresa()
    ctx = _shared_ctx()
    pendencias = _pendencias_5w2h()

    # Ler ações do dia
    f = BASE_DIR / "nucleo" / "data" / "acoes_autonomas.json"
    acoes_hoje = []
    if f.exists():
        try:
            logs = json.loads(f.read_text())
            hoje = datetime.now().strftime("%Y-%m-%d")
            acoes_hoje = [l for l in logs if l.get("ts","").startswith(hoje)][-20:]
        except: pass

    fechamento = await _gemini(
        "Você é Lucas, CEO. Às 18:30 você fecha o dia executivo. Sem rodeios — o que aconteceu, o que não aconteceu, quem cobrar.",
        f"Empresa: {json.dumps(emp)}\n\nAÇÕES DO DIA:\n{json.dumps(acoes_hoje, ensure_ascii=False)[:800]}\n\n"
        f"CONTEXTO DIRETORIA:\n{ctx}\n\nPENDÊNCIAS ABERTAS:\n{pendencias}\n\n"
        "Relate:\n1. O que avançou hoje (com evidência)\n2. O que travou e por quê\n"
        "3. Quem está atrasado em compromisso do 5W2H\n4. Prioridade de amanhã\n"
        "Formato WhatsApp. Direto.", 500
    )
    if fechamento:
        await _notificar(f"👔 *Lucas — Fechamento {datetime.now().strftime('%d/%m')}*\n\n{fechamento}")
        _log("lucas", "fechamento_dia", fechamento)

# ═══════════════════════════════════════════════════════════════════
# DANI — Analista de Dados
# 07:30 Coleta  |  11:00 Anomalias  |  16:00 Relatório métricas
# ═══════════════════════════════════════════════════════════════════

async def dani_coleta_dados():
    """07:30 — Dani coleta e organiza métricas de todas as fontes."""
    logger.info("📊 Dani 07:30 — coleta de dados")
    emp = _empresa()
    from nucleo.ferramentas import hotmart_vendas, meta_ads_resumo
    
    vendas = hotmart_vendas(7)
    ads    = meta_ads_resumo()

    metricas = await _gemini(
        "Você é Dani, Analista de Dados. Você organiza fatos — nunca opiniões. Se não há dado, diz que não há dado.",
        f"Empresa: {json.dumps(emp)}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"VENDAS (7 dias): {vendas}\nMETA ADS: {ads}\n\n"
        "Organize as métricas disponíveis:\n"
        "1. Quais dados temos hoje (com números reais)\n"
        "2. Quais dados estão faltando e deveríamos ter\n"
        "3. Alguma anomalia vs ontem/semana passada?\n"
        "NUNCA invente número. Se não há dado, diga 'sem dado disponível'.", 400
    )
    if metricas:
        _atualizar_shared("dani", "metricas_manha", metricas[:300])
        _log("dani", "coleta_dados", metricas)

async def dani_anomalias():
    """11:00 — Dani detecta anomalias e dispara alertas."""
    logger.info("📊 Dani 11:00 — detecção de anomalias")
    emp = _empresa()
    ctx = _shared_ctx()

    alerta = await _gemini(
        "Você é Dani, Analista de Dados. Você caça anomalias — padrões fora do normal que precisam de atenção.",
        f"Empresa: {json.dumps(emp)}\nDados coletados hoje:\n{ctx}\n\n"
        "Identifique:\n1. Algo fora do padrão nos dados de hoje?\n"
        "2. Alguma métrica que deveria estar sendo medida mas não está?\n"
        "3. Correlação entre dados que pode indicar oportunidade ou risco?\n"
        "Se tudo estiver normal, diga isso com base nos dados — não invente problema.", 350
    )
    if alerta:
        _atualizar_shared("dani", "anomalias_11h", alerta[:300])
        if any(w in alerta.lower() for w in ["anomalia","alerta","queda","fora do padrão","preocupante"]):
            await _notificar(f"📊 *Dani — Alerta de Dados {datetime.now().strftime('%H:%M')}*\n\n{alerta}")
        _log("dani", "deteccao_anomalias", alerta)

async def dani_relatorio_metricas():
    """16:00 — Dani fecha o relatório de métricas do dia e atualiza shared context."""
    logger.info("📊 Dani 16:00 — relatório de métricas")
    emp = _empresa()
    ctx = _shared_ctx()
    from nucleo.ferramentas import hotmart_vendas, meta_ads_resumo
    vendas = hotmart_vendas(1)
    ads    = meta_ads_resumo()

    relatorio = await _gemini(
        "Você é Dani. Feche o relatório de métricas do dia. Números reais ou 'sem dado' — nunca estimativa.",
        f"Empresa: {json.dumps(emp)}\nVendas hoje: {vendas}\nAds hoje: {ads}\n"
        f"Contexto do dia:\n{ctx}\n\n"
        "Relatório final do dia:\n"
        "1. MRR estimado atual (se tiver dado)\n2. Leads gerados hoje\n"
        "3. Custo por lead hoje (se tiver dado)\n4. Conversão do funil (se tiver dado)\n"
        "5. Uma métrica que precisa melhorar amanhã\nSeja cirúrgica.", 400
    )
    if relatorio:
        _atualizar_shared("dani", "relatorio_dia", relatorio[:400])
        await _notificar(f"📊 *Dani — Métricas {datetime.now().strftime('%d/%m')}*\n\n{relatorio}")
        _log("dani", "relatorio_metricas", relatorio)

# ═══════════════════════════════════════════════════════════════════
# PEDRO — CFO
# 08:00 Check financeiro  |  13:00 Revisão de custos  |  18:00 Fechamento P&L
# ═══════════════════════════════════════════════════════════════════

async def pedro_check_financeiro():
    """08:00 — Pedro verifica situação financeira da manhã."""
    logger.info("💰 Pedro 08:00 — check financeiro")
    emp = _empresa()
    from nucleo.ferramentas import hotmart_vendas
    vendas_7 = hotmart_vendas(7)
    vendas_30 = hotmart_vendas(30)

    analise = await _gemini(
        "Você é Pedro, CFO. Analisa dados financeiros com frieza. Usa unit economics: CAC, LTV, margem, runway. "
        "Nunca aprova gasto sem ROI esperado. Se os dados estiverem ausentes, diz que não pode opinar.",
        f"Empresa: {json.dumps(emp)}\nData: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
        f"Vendas 7 dias: {vendas_7}\nVendas 30 dias: {vendas_30}\n\n"
        "Avalie:\n1. Tendência de receita (com número)\n2. Custo de API estimado hoje (OpenAI/Gemini/ElevenLabs/Twilio)\n"
        "3. Algum alerta financeiro urgente?\n4. Uma ação de custo que você recomenda agora\n"
        "Máximo 3 parágrafos. Use números reais ou diga 'sem dado'.", 350
    )
    if analise:
        _atualizar_shared("pedro", "saude_financeira_manha", analise[:300])
        if any(w in analise.lower() for w in ["alerta","queda","urgente","atenção","crítico"]):
            await _notificar(f"💰 *Pedro — Alerta Financeiro {datetime.now().strftime('%H:%M')}*\n\n{analise}")
        _log("pedro", "check_financeiro_manha", analise)

async def pedro_revisao_custos():
    """13:00 — Pedro audita custos e identifica desperdícios."""
    logger.info("💰 Pedro 13:00 — revisão de custos")
    emp = _empresa()
    ctx = _shared_ctx()

    revisao = await _gemini(
        "Você é Pedro, CFO. Às 13h você faz a caçada de custos desnecessários. "
        "Cada real conta. Questione tudo que não tem ROI comprovado.",
        f"Empresa: {json.dumps(emp)}\nContexto do dia:\n{ctx}\n\n"
        "Revise:\n1. Custos de infraestrutura (VPS, APIs, ferramentas) — algum desnecessário?\n"
        "2. Algum gasto proposto hoje pela diretoria que não tem ROI claro?\n"
        "3. Uma oportunidade de corte ou renegociação\n"
        "Se não houver dado de custo, diga isso e peça o dado.", 350
    )
    if revisao:
        _atualizar_shared("pedro", "revisao_custos_13h", revisao[:300])
        _log("pedro", "revisao_custos", revisao)

async def pedro_fechamento_pl():
    """18:00 — Pedro fecha o P&L do dia."""
    logger.info("💰 Pedro 18:00 — fechamento P&L")
    emp = _empresa()
    ctx = _shared_ctx()
    from nucleo.ferramentas import hotmart_vendas
    vendas_hoje = hotmart_vendas(1)

    pl = await _gemini(
        "Você é Pedro, CFO. Feche o P&L do dia com os dados disponíveis. "
        "Onde não há dado, declare ausência — nunca estime sem avisar.",
        f"Empresa: {json.dumps(emp)}\nVendas hoje: {vendas_hoje}\nContexto:\n{ctx}\n\n"
        "P&L do dia:\n1. Receita gerada hoje (se disponível)\n2. Custos estimados hoje\n"
        "3. Margem do dia (ou impossibilidade de calcular sem dado X)\n"
        "4. Situação do runway (se tiver dado de caixa)\n5. Uma decisão financeira para amanhã\n"
        "Seja objetivo. Números reais ou 'sem dado'.", 400
    )
    if pl:
        _atualizar_shared("pedro", "pl_fechamento", pl[:300])
        await _notificar(f"💰 *Pedro — P&L {datetime.now().strftime('%d/%m')}*\n\n{pl}")
        _log("pedro", "fechamento_pl", pl)

# ═══════════════════════════════════════════════════════════════════
# MARIANA — CMO
# 08:30 Meta Ads  |  12:00 Ação de marketing  |  17:30 Relatório leads
# ═══════════════════════════════════════════════════════════════════

async def mariana_check_ads():
    """08:30 — Mariana verifica performance das campanhas."""
    logger.info("📣 Mariana 08:30 — check Meta Ads")
    emp = _empresa()
    from nucleo.ferramentas import meta_ads_resumo, buscar_web
    ads = meta_ads_resumo()
    ctx = _shared_ctx()
    tendencias = buscar_web("marketing digital instagram whatsapp leads brasil 2026")

    analise = await _gemini(
        "Você é Mariana, CMO. Usa AARRR e métricas reais. CAC < R$15/lead é seu benchmark. "
        "Se não tiver dados de campanha, diga isso e proponha como obtê-los.",
        f"Empresa: {json.dumps(emp)}\nMeta Ads hoje: {ads}\n"
        f"Contexto diretoria:\n{ctx}\nTendências: {tendencias[:300]}\n\n"
        "Avalie:\n1. Performance das campanhas (com CPL e CTR se disponível)\n"
        "2. O que otimizar agora (ação específica)\n3. Uma hipótese testável para hoje\n"
        "Máximo 3 frases. Se não tiver dado de campanha, diga que precisa do acesso.", 350
    )
    if analise:
        _atualizar_shared("mariana", "performance_ads_manha", analise[:300])
        _log("mariana", "check_ads", analise)

async def mariana_acao_marketing():
    """12:00 — Mariana define e registra a ação de marketing do dia."""
    logger.info("📣 Mariana 12:00 — ação de marketing")
    emp = _empresa()
    ctx = _shared_ctx()

    acao = await _gemini(
        "Você é Mariana, CMO. Às 12h você define a ação de marketing concreta de hoje. "
        "Não planejamento — AÇÃO. O que vai ser feito hoje, por quem, em qual canal.",
        f"Empresa: {json.dumps(emp)}\nContexto:\n{ctx}\n\n"
        "Defina a ação de marketing de hoje:\n"
        "1. O que: ação específica (post, campanha, email, teste AB)\n"
        "2. Canal: onde (Instagram, WhatsApp, Meta Ads, email)\n"
        "3. Objetivo: qual métrica move (leads, cliques, conversão)\n"
        "4. Como medir: o que conta como sucesso hoje\n"
        "Se não tiver dados suficientes do produto/público, declare o que precisa antes.", 350
    )
    if acao:
        _atualizar_shared("mariana", "acao_marketing_hoje", acao[:300])
        _log("mariana", "acao_marketing", acao)

async def mariana_relatorio_leads():
    """17:30 — Mariana fecha relatório de leads do dia."""
    logger.info("📣 Mariana 17:30 — relatório de leads")
    emp = _empresa()
    ctx = _shared_ctx()
    from nucleo.ferramentas import meta_ads_resumo
    ads = meta_ads_resumo()

    relatorio = await _gemini(
        "Você é Mariana, CMO. Feche o relatório de leads do dia com dados reais.",
        f"Empresa: {json.dumps(emp)}\nAds hoje: {ads}\nContexto:\n{ctx}\n\n"
        "Relatório de leads:\n1. Leads gerados hoje (número real ou 'sem dado')\n"
        "2. Canal de melhor performance\n3. CPL (custo por lead) se disponível\n"
        "4. Taxa de conversão do funil (se disponível)\n5. O que testar amanhã\n"
        "Sem dado inventado.", 350
    )
    if relatorio:
        _atualizar_shared("mariana", "leads_fechamento", relatorio[:300])
        _log("mariana", "relatorio_leads", relatorio)

# ═══════════════════════════════════════════════════════════════════
# CARLA — COO
# 08:45 Check operacional  |  17:00 Check de SLAs
# ═══════════════════════════════════════════════════════════════════

async def carla_check_operacional():
    """08:45 — Carla verifica operações e identifica gargalos."""
    logger.info("⚙️ Carla 08:45 — check operacional")
    emp = _empresa()
    ctx = _shared_ctx()

    check = await _gemini(
        "Você é Carla, COO. Usa OKRs e processos. Identifica gargalos antes que virem problema. "
        "Propõe automação antes de contratar.",
        f"Empresa: {json.dumps(emp)}\nContexto:\n{ctx}\n\n"
        "Check operacional:\n1. Algum processo quebrando ou lento hoje?\n"
        "2. Qual gargalo está impedindo a escala?\n3. Algo que deveria ser automatizado mas ainda é manual?\n"
        "4. Uma OKR que está em risco esta semana\nSeja específica.", 350
    )
    if check:
        _atualizar_shared("carla", "gargalos_operacionais", check[:300])
        if any(w in check.lower() for w in ["urgente","quebrando","crítico","bloqueado","risco"]):
            await _notificar(f"⚙️ *Carla — Alerta Operacional {datetime.now().strftime('%H:%M')}*\n\n{check}")
        _log("carla", "check_operacional", check)

async def carla_check_sla():
    """17:00 — Carla verifica SLAs e entregas do dia."""
    logger.info("⚙️ Carla 17:00 — check SLA")
    emp = _empresa()
    ctx = _shared_ctx()
    pendencias = _pendencias_5w2h()

    sla = await _gemini(
        "Você é Carla, COO. Às 17h você verifica se o que foi prometido foi entregue.",
        f"Empresa: {json.dumps(emp)}\nPendências 5W2H:\n{pendencias}\n"
        f"O que aconteceu hoje:\n{ctx}\n\n"
        "Verifique:\n1. Algum compromisso do 5W2H venceu hoje e não foi entregue?\n"
        "2. Algum processo operacional falhou hoje?\n3. O que precisa de atenção amanhã cedo?\n"
        "Seja direta e específica.", 300
    )
    if sla:
        _atualizar_shared("carla", "sla_fechamento", sla[:300])
        _log("carla", "check_sla", sla)

# ═══════════════════════════════════════════════════════════════════
# RAFAEL — CPO
# 09:00 Métricas de produto  |  14:30 Priorização de features
# ═══════════════════════════════════════════════════════════════════

async def rafael_metricas_produto():
    """09:00 — Rafael verifica métricas de produto e engajamento."""
    logger.info("🚀 Rafael 09:00 — métricas de produto")
    emp = _empresa()
    ctx = _shared_ctx()

    metricas = await _gemini(
        "Você é Rafael, CPO. Usa JTBD e RICE. Cada feature deve resolver uma dor real. "
        "Se não tiver dado de uso do produto, declare isso — é um problema crítico.",
        f"Empresa: {json.dumps(emp)}\nContexto:\n{ctx}\n\n"
        "Métricas de produto hoje:\n1. Taxa de ativação de novos usuários (se disponível)\n"
        "2. Taxa de conclusão de cursos/módulos (VibeSchool)\n"
        "3. Funcionalidade mais usada vs menos usada\n4. Principal queixa ou pedido dos usuários\n"
        "Se não tiver acesso ao Supabase com esses dados, declare que precisa dessa integração.", 350
    )
    if metricas:
        _atualizar_shared("rafael", "metricas_produto", metricas[:300])
        _log("rafael", "metricas_produto", metricas)

async def rafael_priorizacao_features():
    """14:30 — Rafael prioriza o que o produto precisa com RICE score."""
    logger.info("🚀 Rafael 14:30 — priorização de features")
    emp = _empresa()
    ctx = _shared_ctx()

    priorizacao = await _gemini(
        "Você é Rafael, CPO. Usa RICE score para priorizar. Reach × Impact × Confidence ÷ Effort. "
        "Questiona qualquer feature sem evidência de dor do usuário.",
        f"Empresa: {json.dumps(emp)}\nContexto do dia:\n{ctx}\n\n"
        "Priorização de hoje:\n1. O que o produto mais precisa agora (baseado em dado, não achismo)\n"
        "2. O que NÃO deve ser feito agora (e por quê)\n"
        "3. Um gap de produto que está travando o crescimento\n"
        "4. RICE score estimado da top prioridade\n"
        "Se não tiver dados de usuário, diga isso — você não pode priorizar sem dado.", 350
    )
    if priorizacao:
        _atualizar_shared("rafael", "priorizacao_features", priorizacao[:300])
        _log("rafael", "priorizacao_features", priorizacao)

# ═══════════════════════════════════════════════════════════════════
# ANA — CHRO
# 09:30 Energia do dono  |  15:30 Delegação e automação
# ═══════════════════════════════════════════════════════════════════

async def ana_check_energia_dono():
    """09:30 — Ana monitora energia e produtividade do dono."""
    logger.info("🧘 Ana 09:30 — energia do dono")
    emp = _empresa()
    ctx = _shared_ctx()

    check = await _gemini(
        "Você é Ana, CHRO. Seu foco principal é o Jose (dono) — energia física, mental e emocional. "
        "Um dono sobrecarregado toma decisões ruins. Sua missão é prevenir isso.",
        f"Empresa: {json.dumps(emp)}\nContexto do dia:\n{ctx}\n\n"
        "Check de energia:\n1. Com base na carga de trabalho do dia, Jose está em risco de sobrecarga?\n"
        "2. Alguma tarefa que Jose está fazendo que deveria ser delegada ou automatizada?\n"
        "3. Uma recomendação concreta para preservar energia hoje\n"
        "4. O sistema de agentes está aliviando ou adicionando carga para o Jose?\n"
        "Seja empática mas direta.", 350
    )
    if check:
        _atualizar_shared("ana", "energia_dono", check[:300])
        _log("ana", "check_energia_dono", check)

async def ana_delegacao_automacao():
    """15:30 — Ana identifica o que pode ser delegado ou automatizado."""
    logger.info("🧘 Ana 15:30 — delegação e automação")
    emp = _empresa()
    ctx = _shared_ctx()

    analise = await _gemini(
        "Você é Ana, CHRO. Usa a Matriz de Delegação: o que só o Jose pode fazer vs o que agentes fazem "
        "vs o que deve ser automatizado. Menos Jose operacional = mais Jose estratégico.",
        f"Empresa: {json.dumps(emp)}\nAtividades do dia:\n{ctx}\n\n"
        "Mapeie:\n1. O que Jose fez hoje que poderia ter sido feito por um agente?\n"
        "2. O que um agente fez hoje que precisa virar automação?\n"
        "3. Uma sugestão concreta de delegação para esta semana\n"
        "4. O que só o Jose pode e deve fazer (não delegar)", 300
    )
    if analise:
        _atualizar_shared("ana", "delegacao_automacao", analise[:300])
        _log("ana", "delegacao_automacao", analise)

# ═══════════════════════════════════════════════════════════════════
# BETO — Otimizador
# 10:00 Auditoria de custos  |  15:00 Quick wins do dia
# ═══════════════════════════════════════════════════════════════════

async def beto_auditoria_custos():
    """10:00 — Beto audita todos os custos e caça desperdícios."""
    logger.info("💡 Beto 10:00 — auditoria de custos")
    emp = _empresa()
    ctx = _shared_ctx()

    auditoria = await _gemini(
        "Você é Beto, Otimizador. Usa Lean Thinking. Caça os 7 desperdícios em tech: "
        "superprodução, espera, retrabalho, over-engineering, bugs, processamento desnecessário, custo de oportunidade. "
        "Sempre pergunta: existe versão mais barata de testar isso?",
        f"Empresa: {json.dumps(emp)}\nContexto:\n{ctx}\n\n"
        "Auditoria de hoje:\n1. Qual o custo de API estimado hoje (OpenAI, Gemini, ElevenLabs, Twilio)?\n"
        "2. Algum processo sendo feito de forma cara quando existe alternativa grátis ou barata?\n"
        "3. Alguma proposta da diretoria que pode ser testada com 1/10 do custo sugerido?\n"
        "4. Um corte ou otimização que você recomenda agora\n"
        "Seja específico com valores em R$.", 350
    )
    if auditoria:
        _atualizar_shared("beto", "auditoria_custos", auditoria[:300])
        _log("beto", "auditoria_custos", auditoria)

async def beto_quick_wins():
    """15:00 — Beto identifica quick wins de alto impacto e baixo esforço."""
    logger.info("💡 Beto 15:00 — quick wins")
    emp = _empresa()
    ctx = _shared_ctx()

    wins = await _gemini(
        "Você é Beto, Otimizador. Quick win = alto impacto, baixo esforço, resultado em menos de 48h. "
        "Você tem instinto para achar o atalho que ninguém viu.",
        f"Empresa: {json.dumps(emp)}\nContexto do dia:\n{ctx}\n\n"
        "Quick wins de hoje:\n1. Uma ação que pode ser feita em 2h e gera resultado imediato\n"
        "2. Uma automação simples que elimina trabalho repetitivo\n"
        "3. Um custo que pode ser cortado hoje sem impacto no produto\n"
        "Cada item com: O quê, Quanto tempo leva, Impacto esperado.", 350
    )
    if wins:
        _atualizar_shared("beto", "quick_wins_dia", wins[:300])
        _log("beto", "quick_wins", wins)

# ═══════════════════════════════════════════════════════════════════
# ZÉ — Coach
# 10:30 Bem-estar  |  16:30 Destravar decisões
# ═══════════════════════════════════════════════════════════════════

async def ze_check_bemestar():
    """10:30 — Zé monitora o bem-estar e identifica loops de ansiedade."""
    logger.info("🧘 Zé 10:30 — check de bem-estar")
    emp = _empresa()
    ctx = _shared_ctx()

    check = await _gemini(
        "Você é Zé, Coach executivo. Usa 5 Whys e distinção fato vs interpretação. "
        "Seu foco é o Jose. Identifica o que está gerando mais ansiedade ou estresse hoje.",
        f"Empresa: {json.dumps(emp)}\nContexto do dia:\n{ctx}\n\n"
        "Check de bem-estar:\n1. O que parece estar gerando mais estresse ou pressão hoje?\n"
        "2. Alguma decisão sendo evitada por ansiedade?\n"
        "3. Uma distinção importante: o que é fato vs o que é interpretação nas preocupações do dia\n"
        "4. Uma pergunta de coaching para o Jose refletir hoje\n"
        "Seja calmo, empático, mas direto na reflexão.", 350
    )
    if check:
        _atualizar_shared("ze", "bemestar_manha", check[:300])
        _log("ze", "check_bemestar", check)

async def ze_destravar_decisoes():
    """16:30 — Zé identifica decisões travadas e ajuda a desbloqueá-las."""
    logger.info("🧘 Zé 16:30 — destravar decisões")
    emp = _empresa()
    ctx = _shared_ctx()
    pendencias = _pendencias_5w2h()

    destravamento = await _gemini(
        "Você é Zé, Coach. Às 16:30 você identifica o que está travado e por quê. "
        "Usa Commitment vs Interest: o que é compromisso real vs o que é interesse passageiro.",
        f"Empresa: {json.dumps(emp)}\nContexto do dia:\n{ctx}\n"
        f"Pendências abertas:\n{pendencias}\n\n"
        "Desbloqueie:\n1. Qual decisão está sendo postergada hoje e por quê?\n"
        "2. O que é compromisso (vai ser feito) vs interesse (seria legal fazer)?\n"
        "3. O menor próximo passo concreto para a decisão mais travada\n"
        "4. Uma pergunta que, se respondida, destrava tudo\n"
        "Máximo 4 frases. Direto.", 300
    )
    if destravamento:
        _atualizar_shared("ze", "decisoes_destravadas", destravamento[:300])
        _log("ze", "destravar_decisoes", destravamento)


# ═══════════════════════════════════════════════════════════════════
# MAPA COMPLETO DE HORÁRIOS
# ═══════════════════════════════════════════════════════════════════

# (hora, minuto, chave_unica, funcao)
ROTINAS_DIARIAS = [
    (7,  0,  "diana_mercado",      diana_briefing_mercado),
    (7,  15, "lucas_leitura",      lucas_leitura_manha),
    (7,  30, "dani_coleta",        dani_coleta_dados),
    (8,  0,  "pedro_manha",        pedro_check_financeiro),
    (8,  30, "mariana_ads",        mariana_check_ads),
    (8,  45, "carla_operacional",  carla_check_operacional),
    (9,  0,  "rafael_metricas",    rafael_metricas_produto),
    (9,  30, "ana_energia",        ana_check_energia_dono),
    (10, 0,  "beto_auditoria",     beto_auditoria_custos),
    (10, 30, "ze_bemestar",        ze_check_bemestar),
    (11, 0,  "dani_anomalias",     dani_anomalias),
    (12, 0,  "mariana_acao",       mariana_acao_marketing),
    (13, 0,  "pedro_custos",       pedro_revisao_custos),
    (14, 0,  "diana_competitiva",  diana_inteligencia_competitiva),
    (14, 30, "rafael_features",    rafael_priorizacao_features),
    (15, 0,  "beto_wins",          beto_quick_wins),
    (15, 30, "ana_delegacao",      ana_delegacao_automacao),
    (16, 0,  "dani_relatorio",     dani_relatorio_metricas),
    (16, 30, "ze_decisoes",        ze_destravar_decisoes),
    (17, 0,  "carla_sla",          carla_check_sla),
    (17, 30, "mariana_leads",      mariana_relatorio_leads),
    (18, 0,  "pedro_pl",           pedro_fechamento_pl),
    (18, 30, "lucas_fechamento",   lucas_fechamento_dia),
    (9,  0,  "lucas_decisao",      lucas_decisao_dia),
]

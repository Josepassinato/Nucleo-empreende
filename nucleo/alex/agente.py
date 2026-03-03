"""
Alex — Agente Consultor de Onboarding

Fluxo:
  FASE 1 — Boas-vindas e apresentação
  FASE 2 — Diagnóstico (15 perguntas adaptativas)
  FASE 3 — Classificação do negócio
  FASE 4 — Apresentação do pacote de serviços
  FASE 5 — Autorização e entrega para Lucas

Alex conversa via WebSocket (interface web) ou WhatsApp.
Salva progresso a cada resposta — retoma onde parou.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import httpx
from dotenv import load_dotenv

from nucleo.alex.classificador import classificar_ramo, gerar_dna_empresa
from nucleo.alex.universo_servicos import (
    servicos_automaticos, servicos_manuais, resumo_para_alex
)

load_dotenv()
logger = logging.getLogger("nucleo.alex")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ══════════════════════════════════════════════════════════════════
# PERGUNTAS DO DIAGNÓSTICO
# ══════════════════════════════════════════════════════════════════

PERGUNTAS = [
    {
        "id": "nome_dono",
        "pergunta": "Antes de tudo, qual é o seu nome?",
        "campo": "nome_dono",
        "obrigatoria": True,
    },
    {
        "id": "nome_empresa",
        "pergunta": "Qual é o nome da sua empresa ou negócio?",
        "campo": "nome_empresa",
        "obrigatoria": True,
    },
    {
        "id": "descricao_negocio",
        "pergunta": "Me conta em poucas palavras o que sua empresa faz. Qual problema ela resolve?",
        "campo": "descricao_negocio",
        "obrigatoria": True,
    },
    {
        "id": "produto_servico",
        "pergunta": "Qual é o seu principal produto ou serviço? Descreva como ele funciona.",
        "campo": "produto_servico",
        "obrigatoria": True,
    },
    {
        "id": "preco_ticket",
        "pergunta": "Qual é o preço do seu produto ou serviço? (Ticket médio ou faixa de preço)",
        "campo": "preco_ticket",
        "obrigatoria": True,
    },
    {
        "id": "publico_alvo",
        "pergunta": "Quem é o seu cliente ideal? (Idade, profissão, problema que tem, onde mora)",
        "campo": "publico_alvo",
        "obrigatoria": True,
    },
    {
        "id": "canais_aquisicao",
        "pergunta": "Como você consegue seus clientes hoje? (Instagram, indicação, Google, WhatsApp, etc.)",
        "campo": "canais_aquisicao",
        "obrigatoria": True,
    },
    {
        "id": "concorrentes",
        "pergunta": "Quem são seus principais concorrentes? O que te diferencia deles?",
        "campo": "concorrentes",
        "obrigatoria": False,
    },
    {
        "id": "diferenciais",
        "pergunta": "Por que um cliente escolhe você e não o concorrente? Qual é o seu grande diferencial?",
        "campo": "diferenciais",
        "obrigatoria": True,
    },
    {
        "id": "faturamento_atual",
        "pergunta": "Quanto sua empresa fatura por mês hoje? (Aproximado, pode ser uma faixa)",
        "campo": "faturamento_atual",
        "obrigatoria": False,
    },
    {
        "id": "meta_faturamento",
        "pergunta": "Qual é a sua meta de faturamento? Quanto você quer chegar?",
        "campo": "meta_faturamento",
        "obrigatoria": True,
    },
    {
        "id": "prazo_meta",
        "pergunta": "Em quanto tempo você quer atingir essa meta? (3 meses, 6 meses, 1 ano?)",
        "campo": "prazo_meta",
        "obrigatoria": True,
    },
    {
        "id": "tamanho_equipe",
        "pergunta": "Você trabalha sozinho ou tem equipe? Quantas pessoas?",
        "campo": "tamanho_equipe",
        "obrigatoria": False,
    },
    {
        "id": "ferramentas_atuais",
        "pergunta": "Quais ferramentas ou sistemas você usa hoje? (WhatsApp, planilha, sistema de agendamento, etc.)",
        "campo": "ferramentas_atuais",
        "obrigatoria": False,
    },
    {
        "id": "maior_dor",
        "pergunta": "Qual é a sua maior dificuldade ou dor hoje no negócio? O que mais te tira o sono?",
        "campo": "maior_dor",
        "obrigatoria": True,
    },
]


# ══════════════════════════════════════════════════════════════════
# ESTADO DE SESSÃO DO ALEX
# ══════════════════════════════════════════════════════════════════

def _path_sessao(tenant_id: str) -> Path:
    p = BASE_DIR / "nucleo" / "data" / "onboarding" / f"{tenant_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def carregar_sessao(tenant_id: str) -> dict:
    p = _path_sessao(tenant_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {
        "tenant_id": tenant_id,
        "fase": 1,
        "pergunta_idx": 0,
        "respostas": {},
        "historico": [],
        "classificacao": None,
        "dna_gerado": False,
        "autorizado": False,
        "criado_em": datetime.now().isoformat(),
        "atualizado_em": datetime.now().isoformat(),
    }


def salvar_sessao(tenant_id: str, sessao: dict):
    sessao["atualizado_em"] = datetime.now().isoformat()
    _path_sessao(tenant_id).write_text(
        json.dumps(sessao, ensure_ascii=False, indent=2)
    )


# ══════════════════════════════════════════════════════════════════
# GEMINI — LLM DO ALEX
# ══════════════════════════════════════════════════════════════════

ALEX_SYSTEM = """Você é Alex, o Agente Consultor do Nucleo Empreende.

Seu papel: entender profundamente o negócio do empreendedor em uma conversa natural e acolhedora.

PERSONALIDADE:
- Empático, direto e profissional
- Usa linguagem simples, sem jargão desnecessário
- Faz uma pergunta de cada vez, sem sobrecarregar
- Quando a resposta for vaga, aprofunda com uma pergunta de acompanhamento
- Celebra conquistas do empreendedor (ex: "Que legal que você já tem X clientes!")
- Nunca julga a situação atual — só olha para frente

REGRAS ABSOLUTAS:
- NUNCA invente informações sobre a empresa
- NUNCA faça mais de UMA pergunta por mensagem
- NUNCA prometa resultados específicos
- Se não entender a resposta, peça para explicar de outro jeito
- Mantenha o tom de consultor experiente, não de robô

CONTEXTO: Você está fazendo o diagnóstico inicial para configurar a equipe de agentes de IA
que vai gerenciar o negócio do empreendedor. Quanto mais você souber, melhor a equipe vai trabalhar."""


async def gemini_alex(mensagens: list, tokens: int = 400) -> str:
    """Chama Gemini com histórico de conversa."""
    try:
        contents = []
        for m in mensagens:
            contents.append({
                "role": "user" if m["role"] == "user" else "model",
                "parts": [{"text": m["content"]}]
            })

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": ALEX_SYSTEM}]},
                    "contents": contents,
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": tokens}
                }
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini Alex erro: {e}")
        return "Desculpe, tive um problema técnico. Pode repetir sua resposta?"


# ══════════════════════════════════════════════════════════════════
# LÓGICA PRINCIPAL DO ALEX
# ══════════════════════════════════════════════════════════════════

async def iniciar_conversa(tenant_id: str) -> dict:
    """Inicia ou retoma a conversa de onboarding."""
    sessao = carregar_sessao(tenant_id)

    # Se já concluiu
    if sessao.get("dna_gerado"):
        return {
            "mensagem": f"Seu diagnóstico já está completo! Sua diretoria de IA está configurada e operando. 🚀",
            "fase": "concluido",
            "sessao": sessao,
        }

    # Saudação inicial (primeira vez)
    if not sessao["historico"]:
        boas_vindas = (
            "👋 Olá! Sou o **Alex**, seu Consultor de IA do Nucleo Empreende.\n\n"
            "Nos próximos minutos, vou fazer algumas perguntas sobre o seu negócio. "
            "Com base nas suas respostas, vou configurar uma **equipe completa de agentes de IA** "
            "— CEO, CFO, CMO, COO e mais — para gerenciar e fazer sua empresa crescer.\n\n"
            "Quanto mais você me contar, mais precisa e poderosa será sua equipe. "
            "Vamos começar? 😊\n\n"
            f"**{PERGUNTAS[0]['pergunta']}**"
        )
        sessao["historico"].append({"role": "assistant", "content": boas_vindas})
        salvar_sessao(tenant_id, sessao)
        return {"mensagem": boas_vindas, "fase": "diagnostico", "progresso": 0}

    # Retomando sessão existente
    idx = sessao["pergunta_idx"]
    if idx < len(PERGUNTAS):
        pergunta_atual = PERGUNTAS[idx]["pergunta"]
        return {
            "mensagem": f"Bem-vindo de volta! Vamos continuar de onde paramos.\n\n**{pergunta_atual}**",
            "fase": "diagnostico",
            "progresso": int((idx / len(PERGUNTAS)) * 100),
        }

    return {"mensagem": "Continuando...", "fase": "diagnostico", "progresso": 90}


async def processar_resposta(tenant_id: str, mensagem_usuario: str) -> dict:
    """Processa uma resposta do usuário e avança o diagnóstico."""
    sessao = carregar_sessao(tenant_id)

    # Adiciona mensagem do usuário ao histórico
    sessao["historico"].append({"role": "user", "content": mensagem_usuario})

    # ── FASE 1-2: Diagnóstico ─────────────────────────────────────
    idx = sessao["pergunta_idx"]

    if idx < len(PERGUNTAS):
        pergunta = PERGUNTAS[idx]

        # Salva a resposta no campo correto
        sessao["respostas"][pergunta["campo"]] = mensagem_usuario

        # Avança para próxima pergunta
        idx += 1
        sessao["pergunta_idx"] = idx

        # Ainda tem perguntas?
        if idx < len(PERGUNTAS):
            proxima = PERGUNTAS[idx]
            progresso = int((idx / len(PERGUNTAS)) * 100)

            # Gera resposta empática com Gemini + já apresenta próxima pergunta
            prompt_gemini = (
                f"O empreendedor respondeu à pergunta '{pergunta['pergunta']}':\n"
                f"Resposta: '{mensagem_usuario}'\n\n"
                f"Faça um comentário breve e empático sobre a resposta (1-2 frases), "
                f"depois faça naturalmente a próxima pergunta:\n'{proxima['pergunta']}'\n\n"
                f"NÃO use markdown excessivo. Seja direto e natural."
            )
            sessao["historico"].append({"role": "user", "content": prompt_gemini})
            resposta = await gemini_alex(sessao["historico"][-6:], tokens=300)
            # Remove a pergunta do prompt do histórico real
            sessao["historico"].pop()
            sessao["historico"].append({"role": "assistant", "content": resposta})
            salvar_sessao(tenant_id, sessao)

            return {
                "mensagem": resposta,
                "fase": "diagnostico",
                "progresso": progresso,
            }

        else:
            # ── Diagnóstico concluído — classificar ──────────────
            return await _concluir_diagnostico(tenant_id, sessao)

    # ── FASE 3: Aguardando autorização ───────────────────────────
    elif sessao.get("classificacao") and not sessao.get("autorizado"):
        return await _processar_autorizacao(tenant_id, sessao, mensagem_usuario)

    return {"mensagem": "Diagnóstico em processamento...", "fase": "processando"}


async def _concluir_diagnostico(tenant_id: str, sessao: dict) -> dict:
    """Classifica o negócio, gera DNA e apresenta o pacote."""

    # Junta todas as respostas para classificar
    texto_completo = " ".join(sessao["respostas"].values())
    classificacao = classificar_ramo(texto_completo)
    sessao["classificacao"] = classificacao

    ramo = classificacao["ramo"]
    automaticos = servicos_automaticos(ramo)
    manuais = servicos_manuais(ramo)

    nome_dono = sessao["respostas"].get("nome_dono", "")
    nome_empresa = sessao["respostas"].get("nome_empresa", "")
    meta = sessao["respostas"].get("meta_faturamento", "")
    dor = sessao["respostas"].get("maior_dor", "")

    # Monta mensagem de conclusão
    msg = (
        f"✅ **Diagnóstico concluído, {nome_dono}!**\n\n"
        f"Analisei tudo sobre a **{nome_empresa}** e aqui está o que vou fazer por você:\n\n"
        f"🎯 **Tipo de negócio detectado:** {_label_ramo(ramo)}\n"
        f"💰 **Meta:** {meta}\n"
        f"🔥 **Principal dor a resolver:** {dor[:100]}\n\n"
        f"---\n\n"
        f"🤖 **Sua equipe de IA vai ser configurada assim:**\n\n"
        f"✅ **{len(automaticos)} serviços que configuro automaticamente agora:**\n"
    )

    for s in automaticos[:8]:
        msg += f"   • {s['nome']}\n"

    if len(automaticos) > 8:
        msg += f"   • ...e mais {len(automaticos) - 8} serviços\n"

    if manuais:
        msg += f"\n⚙️ **{len(manuais)} serviços que precisam de uma ação sua** (envio o passo a passo):\n"
        for s in manuais[:4]:
            msg += f"   • {s['nome']}\n"

    msg += (
        f"\n---\n\n"
        f"Depois de configurar tudo, você terá uma equipe com:\n"
        f"👔 Lucas (CEO) · 💰 Pedro (CFO) · 📣 Mariana (CMO)\n"
        f"⚙️ Carla (COO) · 🚀 Rafael (CPO) · 📊 Dani (Dados)\n"
        f"🎯 Zé (Coach) · 💡 Beto (Otimizador) · 🔍 Diana (Mercado)\n\n"
        f"**Posso começar agora? Digite SIM para autorizar ou AJUSTAR para modificar algo.**"
    )

    sessao["historico"].append({"role": "assistant", "content": msg})
    salvar_sessao(tenant_id, sessao)

    return {
        "mensagem": msg,
        "fase": "aguardando_autorizacao",
        "classificacao": classificacao,
        "progresso": 100,
    }


async def _processar_autorizacao(tenant_id: str, sessao: dict, resposta: str) -> dict:
    """Processa a autorização do dono para iniciar a configuração."""
    resposta_lower = resposta.lower().strip()

    if any(w in resposta_lower for w in ["sim", "yes", "autorizo", "pode", "vai", "começar", "ok", "s"]):
        sessao["autorizado"] = True

        # Gera o DNA e salva na memória
        dna = gerar_dna_empresa(sessao["respostas"], sessao["classificacao"])
        sessao["dna_gerado"] = True
        salvar_sessao(tenant_id, sessao)

        # Salva DNA no memoria.json do tenant
        await _salvar_dna_na_memoria(tenant_id, dna)

        # Notifica Lucas
        await _notificar_lucas(tenant_id, dna, sessao["classificacao"])

        nome_dono = sessao["respostas"].get("nome_dono", "")
        nome_empresa = sessao["respostas"].get("nome_empresa", "")

        msg = (
            f"🚀 **Perfeito, {nome_dono}! Iniciando a configuração da {nome_empresa}...**\n\n"
            f"✅ DNA da empresa salvo\n"
            f"✅ Banco de dados criado no Supabase\n"
            f"✅ Lucas (CEO) recebeu o briefing completo\n"
            f"✅ Diretoria sendo configurada agora\n\n"
            f"Em **poucos minutos** sua equipe de IA estará operacional.\n\n"
            f"Você pode acompanhar tudo no **Mural** em tempo real:\n"
            f"👉 `/mural`\n\n"
            f"Lucas vai te contatar logo com a primeira análise da empresa. 💪"
        )

        sessao["historico"].append({"role": "assistant", "content": msg})
        salvar_sessao(tenant_id, sessao)

        return {
            "mensagem": msg,
            "fase": "concluido",
            "dna": dna,
        }

    elif any(w in resposta_lower for w in ["ajustar", "mudar", "corrigir", "não", "nao", "recomeçar"]):
        msg = (
            "Sem problema! O que você gostaria de ajustar?\n\n"
            "Pode me dizer qual informação está errada ou incompleta."
        )
        sessao["historico"].append({"role": "assistant", "content": msg})
        sessao["pergunta_idx"] = 0  # Reinicia diagnóstico
        salvar_sessao(tenant_id, sessao)
        return {"mensagem": msg, "fase": "ajustando"}

    else:
        # Resposta ambígua
        msg = (
            "Não entendi bem. Por favor, responda:\n\n"
            "✅ **SIM** — para eu começar a configurar sua equipe agora\n"
            "🔧 **AJUSTAR** — para corrigir alguma informação"
        )
        return {"mensagem": msg, "fase": "aguardando_autorizacao"}


async def _salvar_dna_na_memoria(tenant_id: str, dna: dict):
    """Salva o DNA da empresa no memoria.json."""
    mem_file = BASE_DIR / "nucleo" / "data" / "memoria.json"
    try:
        if mem_file.exists():
            mem = json.loads(mem_file.read_text())
        else:
            mem = {}
        mem["empresa"] = dna
        mem["tenant_id"] = tenant_id
        mem_file.write_text(json.dumps(mem, ensure_ascii=False, indent=2))
        logger.info(f"✅ DNA da empresa {dna.get('nome')} salvo na memória")
    except Exception as e:
        logger.error(f"Erro ao salvar DNA: {e}")


async def _notificar_lucas(tenant_id: str, dna: dict, classificacao: dict):
    """Envia briefing completo para o Lucas (CEO) iniciar a configuração da diretoria."""
    try:
        # Importa o sistema de notificação
        from nucleo.autonomo import notificar_dono
        import httpx as _httpx

        google_key = os.getenv("GOOGLE_API_KEY", "")
        ramo = dna.get("ramo", "")
        nome = dna.get("nome", "")
        meta = dna.get("meta_faturamento", "")
        dor = dna.get("maior_dor", "")
        produto = dna.get("produto", "")
        preco = dna.get("preco", "")
        publico = dna.get("publico_alvo", "")
        canais = dna.get("canais_aquisicao", "")
        integracoes = dna.get("integracoes_sugeridas", [])
        kpis = dna.get("kpis_principais", [])

        # Lucas gera o briefing para a diretoria
        system_lucas = (
            "Você é Lucas, CEO. Acaba de receber o DNA completo de uma nova empresa. "
            "Sua missão: gerar um briefing executivo de 1 página para toda a diretoria, "
            "dizendo o que cada agente precisa fazer nas próximas 24h para configurar essa empresa. "
            "Seja específico. Use os dados reais da empresa."
        )

        prompt = (
            f"NOVA EMPRESA ONBOARDING:\n"
            f"Nome: {nome}\n"
            f"Ramo: {ramo}\n"
            f"Produto: {produto}\n"
            f"Preço: {preco}\n"
            f"Público-alvo: {publico}\n"
            f"Canais de aquisição: {canais}\n"
            f"Meta: {meta}\n"
            f"Maior dor: {dor}\n"
            f"KPIs principais: {', '.join(kpis)}\n"
            f"Integrações prioritárias: {', '.join(integracoes)}\n\n"
            f"Gere o briefing para a diretoria com instruções específicas para:\n"
            f"Mariana (CMO), Pedro (CFO), Rafael (CPO), Carla (COO), Diana (CNO), Dani (Dados)\n"
            f"Formato WhatsApp. Máximo 500 palavras."
        )

        async with _httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={google_key}",
                json={
                    "system_instruction": {"parts": [{"text": system_lucas}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600}
                }
            )
            briefing = r.json()["candidates"][0]["content"]["parts"][0]["text"]

        msg = f"👔 *Lucas — Nova Empresa Onboarding*\n\n*{nome}*\n\n{briefing}"
        await notificar_dono(msg)

        # Log da ação
        log_file = BASE_DIR / "nucleo" / "data" / "acoes_autonomas.json"
        try:
            logs = json.loads(log_file.read_text()) if log_file.exists() else []
        except Exception:
            logs = []
        logs.append({
            "ts": datetime.now().isoformat(),
            "agente": "alex",
            "acao": "onboarding_concluido",
            "resultado": f"DNA da empresa {nome} gerado e Lucas notificado"
        })
        log_file.write_text(json.dumps(logs[-500:], ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"Erro ao notificar Lucas: {e}")


def _label_ramo(ramo: str) -> str:
    labels = {
        "produto_digital": "Produto Digital / Infoproduto",
        "ecommerce":       "E-commerce / Produto Físico",
        "servico":         "Prestação de Serviços",
        "saas":            "SaaS / Software",
        "infoproduto":     "Infoproduto / Afiliados",
        "consultoria":     "Consultoria / Assessoria",
        "saude":           "Saúde / Clínica",
        "imoveis":         "Imóveis / Imobiliária",
        "alimentacao":     "Alimentação / Delivery",
        "varejo_fisico":   "Varejo Físico",
    }
    return labels.get(ramo, ramo)

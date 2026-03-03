"""
Alex — Classificador de Modelo de Negócio

Analisa as respostas do diagnóstico e classifica:
- Tipo de negócio (ramo)
- Modelo de receita
- Ferramentas necessárias
- KPIs principais
- Integrações prioritárias
"""

import json

# ── Mapa de palavras-chave → ramo ────────────────────────────────────────

KEYWORDS_RAMO = {
    "produto_digital": [
        "curso", "ebook", "mentoria", "infoproduto", "hotmart", "kiwify",
        "eduzz", "digital", "online", "treinamento", "masterclass", "workshop",
        "plataforma ead", "aula", "videoaula", "conteudo", "membro",
    ],
    "ecommerce": [
        "loja", "produto físico", "estoque", "shopify", "mercado livre",
        "shopee", "amazon", "woocommerce", "ecommerce", "e-commerce",
        "mercadoria", "prateleira", "varejo online", "loja virtual",
    ],
    "servico": [
        "serviço", "consultoria", "agendamento", "cliente", "atendimento",
        "visita", "técnico", "manutenção", "instalação", "reparo",
        "prestador", "freelancer", "autônomo", "projeto", "hora",
    ],
    "saas": [
        "software", "saas", "assinatura", "plataforma", "sistema",
        "app", "aplicativo", "api", "ferramenta", "tecnologia", "startup",
        "recorrência", "mensalidade", "licença", "plano",
    ],
    "infoproduto": [
        "afiliado", "comissão", "produto digital", "lançamento",
        "lista", "leads", "funil", "copy", "perpétuo", "evergreen",
    ],
    "consultoria": [
        "consultoria", "assessoria", "coaching", "mentoria presencial",
        "gestão", "estratégia", "diagnóstico", "empresa", "b2b",
        "corporativo", "proposta", "contrato",
    ],
    "saude": [
        "clínica", "consultório", "médico", "dentista", "psicólogo",
        "fisioterapeuta", "nutricionista", "saúde", "paciente",
        "prontuário", "consulta", "exame", "telemedicina",
    ],
    "imoveis": [
        "imóvel", "imobiliária", "corretor", "aluguel", "venda",
        "apartamento", "casa", "terreno", "creci", "construtora",
        "incorporadora", "condomínio",
    ],
    "alimentacao": [
        "restaurante", "lanchonete", "delivery", "ifood", "cardápio",
        "comida", "refeição", "pizzaria", "hamburguer", "food",
        "dark kitchen", "açaí",
    ],
    "varejo_fisico": [
        "loja física", "ponto de venda", "pdv", "caixa", "varejo",
        "mercado", "supermercado", "farmácia", "pet shop",
        "boutique", "moda", "roupas",
    ],
}

# ── KPIs por ramo ────────────────────────────────────────────────────────

KPIS_POR_RAMO = {
    "produto_digital": ["MRR", "CAC", "LTV", "Taxa de conclusão de curso", "Churn", "NPS"],
    "ecommerce":       ["GMV", "Ticket médio", "Taxa de conversão", "CAC", "Taxa de devolução", "Estoque"],
    "servico":         ["Faturamento mensal", "Taxa de ocupação", "NPS", "CAC", "Ticket médio por projeto"],
    "saas":            ["MRR", "Churn", "DAU/MAU", "CAC", "LTV", "Conversão trial→pago"],
    "infoproduto":     ["Faturamento por lançamento", "CAC", "ROI de anúncios", "Taxa de conversão"],
    "consultoria":     ["Faturamento mensal", "Horas vendidas", "Taxa de renovação", "NPS", "Pipeline"],
    "saude":           ["Agendamentos/mês", "Taxa de ocupação", "Ticket médio", "NPS", "Retorno"],
    "imoveis":         ["Captações/mês", "Visitas/semana", "Taxa de conversão", "Comissão média"],
    "alimentacao":     ["Faturamento/dia", "Ticket médio", "Avaliação iFood", "Custo CMV", "Pedidos/dia"],
    "varejo_fisico":   ["Faturamento/dia", "Ticket médio", "Fluxo de clientes", "Giro de estoque"],
}

# ── Modelos de receita por ramo ──────────────────────────────────────────

MODELO_RECEITA = {
    "produto_digital": "Venda pontual + possível recorrência (membership)",
    "ecommerce":       "Venda de produto físico com margem",
    "servico":         "Venda de hora ou projeto",
    "saas":            "Assinatura recorrente (MRR)",
    "infoproduto":     "Lançamentos + perpétuo",
    "consultoria":     "Projeto ou retainer mensal",
    "saude":           "Consulta avulsa ou plano",
    "imoveis":         "Comissão sobre transação",
    "alimentacao":     "Venda direta de produto com alta rotatividade",
    "varejo_fisico":   "Venda de produto com margem em loja física",
}

# ── Integrações prioritárias por ramo ────────────────────────────────────

INTEGRACOES_PRIORITARIAS = {
    "produto_digital": ["Hotmart ou Kiwify", "WhatsApp API", "Meta Ads", "Email Marketing"],
    "ecommerce":       ["Shopify ou Bling", "Mercado Livre", "Melhor Envio", "Meta Ads"],
    "servico":         ["Cal.com ou Calendly", "WhatsApp API", "Pipedrive", "Asaas"],
    "saas":            ["Stripe ou Asaas", "Supabase", "Intercom", "Google Analytics"],
    "infoproduto":     ["Hotmart", "Meta Ads", "Email Marketing", "WhatsApp API"],
    "consultoria":     ["Google Calendar", "Pipedrive", "DocuSign", "WhatsApp API"],
    "saude":           ["Doctoralia", "WhatsApp API", "Google Calendar", "Asaas"],
    "imoveis":         ["VivaReal / Zap", "WhatsApp API", "Jetimob CRM", "Calendly"],
    "alimentacao":     ["iFood", "Anota AI (WhatsApp)", "Goomer", "Mercado Pago"],
    "varejo_fisico":   ["Bling ERP", "Mercado Pago", "WhatsApp API", "Meta Ads"],
}


def classificar_ramo(texto: str) -> dict:
    """
    Analisa o texto do diagnóstico e retorna a classificação do negócio.
    Retorna o ramo com maior score de palavras-chave encontradas.
    """
    texto_lower = texto.lower()
    scores = {}

    for ramo, keywords in KEYWORDS_RAMO.items():
        score = sum(1 for kw in keywords if kw in texto_lower)
        if score > 0:
            scores[ramo] = score

    if not scores:
        return {"ramo": "servico", "confianca": "baixa", "scores": {}}

    ramo_detectado = max(scores, key=scores.get)
    score_max = scores[ramo_detectado]
    confianca = "alta" if score_max >= 3 else "media" if score_max >= 2 else "baixa"

    return {
        "ramo": ramo_detectado,
        "confianca": confianca,
        "scores": scores,
        "kpis": KPIS_POR_RAMO.get(ramo_detectado, []),
        "modelo_receita": MODELO_RECEITA.get(ramo_detectado, ""),
        "integracoes_prioritarias": INTEGRACOES_PRIORITARIAS.get(ramo_detectado, []),
    }


def gerar_dna_empresa(respostas: dict, classificacao: dict) -> dict:
    """
    Gera o DNA estruturado da empresa a partir das respostas do diagnóstico.
    Este DNA vai para o memoria.json e é usado por toda a diretoria.
    """
    ramo = classificacao.get("ramo", "servico")

    return {
        # Identidade
        "nome":             respostas.get("nome_empresa", ""),
        "dono":             respostas.get("nome_dono", ""),
        "ramo":             ramo,
        "descricao":        respostas.get("descricao_negocio", ""),

        # Produto / Serviço
        "produto":          respostas.get("produto_servico", ""),
        "preco":            respostas.get("preco_ticket", ""),
        "diferenciais":     respostas.get("diferenciais", ""),

        # Mercado
        "publico_alvo":     respostas.get("publico_alvo", ""),
        "concorrentes":     respostas.get("concorrentes", ""),
        "canais_aquisicao": respostas.get("canais_aquisicao", ""),

        # Operação
        "equipe":           respostas.get("tamanho_equipe", ""),
        "ferramentas_atuais": respostas.get("ferramentas_atuais", ""),
        "maior_dor":        respostas.get("maior_dor", ""),

        # Financeiro
        "faturamento_atual": respostas.get("faturamento_atual", ""),
        "meta_faturamento":  respostas.get("meta_faturamento", ""),
        "prazo_meta":        respostas.get("prazo_meta", ""),

        # Modelo de negócio (gerado pelo classificador)
        "modelo_receita":   classificacao.get("modelo_receita", ""),
        "kpis_principais":  classificacao.get("kpis", []),
        "integracoes_sugeridas": classificacao.get("integracoes_prioritarias", []),

        # Metadata
        "onboarding_completo": True,
        "data_onboarding": __import__("datetime").datetime.now().isoformat(),
        "versao_dna": "1.0",
    }

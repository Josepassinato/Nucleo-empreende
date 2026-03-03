"""
Nucleo Empreende - Universo de Servicos Configuráveis por Agentes
Referência completa para o Agente Alex usar no onboarding.
automacao: "automatico" | "parcial" | "manual"
"""

UNIVERSO_SERVICOS = {

  "comunicacao_marketing": {
    "label": "Comunicação e Marketing Digital",
    "icone": "📣",
    "servicos": [
      {"nome": "WhatsApp Business API (Twilio)",    "automacao": "automatico", "custo": "pago",     "api": "Twilio API",          "descricao": "Cria conta Twilio, configura numero, ativa sandbox WhatsApp"},
      {"nome": "WhatsApp Business API (Z-API)",     "automacao": "automatico", "custo": "pago",     "api": "Z-API REST",           "descricao": "Alternativa BR, melhor custo, autentica via QR code"},
      {"nome": "Meta Ads (Facebook/Instagram)",     "automacao": "parcial",    "custo": "pago",     "api": "Meta Graph API",       "descricao": "Cria conta Business - dono precisa verificar identidade"},
      {"nome": "Google Ads",                        "automacao": "parcial",    "custo": "pago",     "api": "Google Ads API",       "descricao": "Cria conta, aprovacao de pagamento requer interacao humana"},
      {"nome": "Email Marketing (Brevo)",           "automacao": "automatico", "custo": "freemium", "api": "Brevo API",            "descricao": "Cria conta, configura dominio, ativa templates automaticos"},
      {"nome": "Email Marketing (Mailchimp)",       "automacao": "automatico", "custo": "freemium", "api": "Mailchimp API",        "descricao": "Cria conta, listas, sequencias de automacao"},
      {"nome": "SMS Marketing (Twilio SMS)",        "automacao": "automatico", "custo": "pago",     "api": "Twilio SMS API",       "descricao": "Configura numero, ativa campanhas SMS"},
      {"nome": "Telegram Bot",                      "automacao": "automatico", "custo": "gratuito", "api": "Telegram BotFather",   "descricao": "Cria bot, configura webhooks, ativa comandos"},
      {"nome": "RD Station Marketing",              "automacao": "automatico", "custo": "pago",     "api": "RD Station API",       "descricao": "CRM de marketing BR - cria conta e configura funil"},
      {"nome": "ActiveCampaign",                    "automacao": "automatico", "custo": "pago",     "api": "ActiveCampaign API",   "descricao": "Cria conta, configura automacoes e tags"},
      {"nome": "Linktree / Stan.store",             "automacao": "automatico", "custo": "freemium", "api": "REST API",             "descricao": "Cria perfil, adiciona links dos canais de venda"},
    ]
  },

  "produtos_digitais": {
    "label": "Vendas de Produtos Digitais",
    "icone": "💻",
    "servicos": [
      {"nome": "Hotmart",     "automacao": "parcial",    "custo": "percentual", "api": "Hotmart API v2",   "descricao": "Configura produto, preco e checkout - conta criada manualmente"},
      {"nome": "Kiwify",      "automacao": "parcial",    "custo": "percentual", "api": "Kiwify API",       "descricao": "Configura produto apos conta criada - processo simples"},
      {"nome": "Eduzz",       "automacao": "parcial",    "custo": "percentual", "api": "Eduzz API",        "descricao": "Alternativa BR - configura funil de vendas"},
      {"nome": "Monetizze",   "automacao": "parcial",    "custo": "percentual", "api": "Monetizze API",    "descricao": "Configura produtos e afiliados apos conta aprovada"},
      {"nome": "Teachable",   "automacao": "automatico", "custo": "pago",       "api": "Teachable API",    "descricao": "Cria escola, cursos, pricing - totalmente via API"},
      {"nome": "Thinkific",   "automacao": "automatico", "custo": "freemium",   "api": "Thinkific API",    "descricao": "Plataforma EAD internacional - configura tudo"},
      {"nome": "Kajabi",      "automacao": "automatico", "custo": "pago",       "api": "Kajabi API",       "descricao": "All-in-one - cria site, curso e email"},
      {"nome": "Memberkit",   "automacao": "automatico", "custo": "pago",       "api": "Memberkit API",    "descricao": "Area de membros BR - configuracao automatica completa"},
      {"nome": "Cademi",      "automacao": "parcial",    "custo": "pago",       "api": "Cademi API",       "descricao": "Plataforma BR - configura apos criacao de conta"},
    ]
  },

  "pagamentos_financas": {
    "label": "Pagamentos e Financas",
    "icone": "💰",
    "servicos": [
      {"nome": "Mercado Pago", "automacao": "parcial",    "custo": "percentual", "api": "MP API v2",       "descricao": "Configura integracao - conta deve ser criada pelo dono (CPF/CNPJ)"},
      {"nome": "Pagar.me",     "automacao": "parcial",    "custo": "percentual", "api": "Pagar.me API",    "descricao": "Gateway BR robusto - KYC exige documentos do dono"},
      {"nome": "Asaas",        "automacao": "parcial",    "custo": "freemium",   "api": "Asaas API",       "descricao": "Cobranca recorrente BR - configura planos apos conta aprovada"},
      {"nome": "Stripe",       "automacao": "parcial",    "custo": "percentual", "api": "Stripe API",      "descricao": "Internacional - KYC automatico, dono confirma dados bancarios"},
      {"nome": "PagSeguro",    "automacao": "manual",     "custo": "percentual", "api": "Sem API completa","descricao": "Verificacao rigorosa - orientacao passo a passo para o dono"},
      {"nome": "Conta Azul",   "automacao": "automatico", "custo": "pago",       "api": "Conta Azul API",  "descricao": "ERP financeiro BR - cria conta, categorias, plano de contas"},
      {"nome": "Nibo",         "automacao": "automatico", "custo": "pago",       "api": "Nibo API",        "descricao": "Gestao financeira PME - configura contas e DRE"},
      {"nome": "Omie",         "automacao": "automatico", "custo": "pago",       "api": "Omie API",        "descricao": "ERP completo BR - configura modulos financeiros"},
      {"nome": "Stark Bank",   "automacao": "automatico", "custo": "pago",       "api": "Stark Bank API",  "descricao": "Banco para empresas BR - API excelente, controla tudo"},
    ]
  },

  "ecommerce_fisico": {
    "label": "E-commerce e Produtos Fisicos",
    "icone": "📦",
    "servicos": [
      {"nome": "Mercado Livre", "automacao": "parcial",    "custo": "percentual", "api": "ML API v2",         "descricao": "Cria anuncios, precifica e gerencia estoque - conta dono cria"},
      {"nome": "Shopee",        "automacao": "parcial",    "custo": "percentual", "api": "Shopee Open API",   "descricao": "Sincroniza catalogo e precos apos conta aprovada"},
      {"nome": "Amazon Seller", "automacao": "manual",     "custo": "pago",       "api": "SP-API",            "descricao": "Aprovacao rigorosa - orienta processo e configura depois"},
      {"nome": "Shopify",       "automacao": "automatico", "custo": "pago",       "api": "Shopify Admin API", "descricao": "Cria loja, adiciona produtos, configura pagamento e frete"},
      {"nome": "WooCommerce",   "automacao": "automatico", "custo": "gratuito",   "api": "WC REST API",       "descricao": "Instala, configura tema e produtos em servidor proprio"},
      {"nome": "Nuvemshop",     "automacao": "automatico", "custo": "pago",       "api": "Nuvemshop API",     "descricao": "Loja virtual BR - cria e configura completamente"},
      {"nome": "Bling ERP",     "automacao": "automatico", "custo": "pago",       "api": "Bling API v3",      "descricao": "Configura estoque, NF-e e integracoes marketplace"},
      {"nome": "Tiny ERP",      "automacao": "automatico", "custo": "pago",       "api": "Tiny API",          "descricao": "Alternativa ao Bling - configura NF-e e estoque"},
    ]
  },

  "logistica_transporte": {
    "label": "Logistica e Transportadoras",
    "icone": "🚚",
    "servicos": [
      {"nome": "Correios (SIGEP Web)", "automacao": "parcial",    "custo": "por_envio", "api": "SIGEP Web API",    "descricao": "Contrato Correios exige CNPJ - configura apos aprovacao"},
      {"nome": "Jadlog",               "automacao": "automatico", "custo": "por_envio", "api": "Jadlog API",       "descricao": "Cria conta, configura modalidades e gera etiquetas"},
      {"nome": "Loggi",                "automacao": "automatico", "custo": "por_envio", "api": "Loggi API",        "descricao": "Entrega urbana - cria conta e solicita coletas"},
      {"nome": "Melhor Envio",         "automacao": "automatico", "custo": "por_envio", "api": "Melhor Envio API", "descricao": "Multi-transportadora BR - agrega e compara fretes"},
      {"nome": "Intelipost",           "automacao": "automatico", "custo": "pago",      "api": "Intelipost API",   "descricao": "Plataforma multi-carrier BR - centraliza todas as transportadoras"},
      {"nome": "DHL Express",          "automacao": "parcial",    "custo": "por_envio", "api": "DHL API",          "descricao": "Internacional - configura apos conta comercial aprovada"},
    ]
  },

  "servicos_agendamento": {
    "label": "Servicos e Agendamento",
    "icone": "📅",
    "servicos": [
      {"nome": "Cal.com",         "automacao": "automatico", "custo": "freemium", "api": "Cal.com API",         "descricao": "Cria calendario, tipos de reuniao, integra Google Calendar"},
      {"nome": "Calendly",        "automacao": "automatico", "custo": "pago",     "api": "Calendly API v2",     "descricao": "Configura tipos de evento, disponibilidade e pagamento"},
      {"nome": "Google Calendar", "automacao": "automatico", "custo": "gratuito", "api": "Google Calendar API", "descricao": "Cria calendarios por equipe, sincroniza agendamentos"},
      {"nome": "Pipedrive",       "automacao": "automatico", "custo": "pago",     "api": "Pipedrive API",       "descricao": "CRM completo - cria funil, campos customizados e relatorios"},
      {"nome": "HubSpot CRM",     "automacao": "automatico", "custo": "freemium", "api": "HubSpot API",         "descricao": "Configura CRM, pipeline de vendas e automacoes de email"},
      {"nome": "Kommo (amoCRM)",  "automacao": "automatico", "custo": "pago",     "api": "Kommo API",           "descricao": "CRM conversacional - configura pipeline e automacoes WhatsApp"},
      {"nome": "Notion",          "automacao": "automatico", "custo": "freemium", "api": "Notion API",          "descricao": "Wiki interna - cria base de conhecimento e SOPs da empresa"},
    ]
  },

  "atendimento_cliente": {
    "label": "Atendimento ao Cliente",
    "icone": "🎧",
    "servicos": [
      {"nome": "Zendesk Support",  "automacao": "automatico", "custo": "pago",     "api": "Zendesk API",    "descricao": "Cria conta, configura filas, macros e SLAs"},
      {"nome": "Freshdesk",        "automacao": "automatico", "custo": "freemium", "api": "Freshdesk API",  "descricao": "Help desk - configura grupos, prioridades e emails"},
      {"nome": "Chatwoot (OS)",    "automacao": "automatico", "custo": "gratuito", "api": "Chatwoot API",   "descricao": "Instala na VPS, configura canais WhatsApp/email/chat"},
      {"nome": "Octadesk",         "automacao": "automatico", "custo": "pago",     "api": "Octadesk API",   "descricao": "Omnichannel BR - integra WhatsApp, email, redes sociais"},
      {"nome": "Typebot (OS)",     "automacao": "automatico", "custo": "gratuito", "api": "Typebot API",    "descricao": "Cria fluxos de atendimento e integra com WhatsApp"},
      {"nome": "Tidio",            "automacao": "automatico", "custo": "freemium", "api": "Tidio API",      "descricao": "Chat + chatbot - configura respostas automaticas"},
      {"nome": "NPS (Delighted)",  "automacao": "automatico", "custo": "freemium", "api": "Delighted API",  "descricao": "Configura envio automatico de NPS pos-compra"},
    ]
  },

  "gestao_interna_erp": {
    "label": "Gestao Interna e ERP",
    "icone": "⚙️",
    "servicos": [
      {"nome": "Omie ERP",         "automacao": "automatico", "custo": "pago",     "api": "Omie API",         "descricao": "ERP BR completo - configura modulos financeiro, estoque, NF-e"},
      {"nome": "Google Workspace", "automacao": "automatico", "custo": "pago",     "api": "Admin SDK",        "descricao": "Cria dominio, emails da equipe, Drive compartilhado"},
      {"nome": "Microsoft 365",    "automacao": "automatico", "custo": "pago",     "api": "MS Graph API",     "descricao": "Configura emails, Teams e SharePoint da empresa"},
      {"nome": "Slack",            "automacao": "automatico", "custo": "freemium", "api": "Slack API",        "descricao": "Cria workspace, canais por departamento e bots"},
      {"nome": "Clicksign",        "automacao": "automatico", "custo": "pago",     "api": "Clicksign API",    "descricao": "Assinatura eletronica BR - templates de contrato"},
      {"nome": "Gupy (RH)",        "automacao": "automatico", "custo": "pago",     "api": "Gupy API",         "descricao": "Configura vagas, fluxo de selecao e testes"},
    ]
  },

  "dados_bi_automacao": {
    "label": "Dados, BI e Automacao",
    "icone": "📊",
    "servicos": [
      {"nome": "Google Analytics 4", "automacao": "automatico", "custo": "gratuito", "api": "GA4 API",           "descricao": "Cria propriedade, configura eventos e conversoes"},
      {"nome": "Meta Pixel",          "automacao": "automatico", "custo": "gratuito", "api": "Meta API",          "descricao": "Instala pixel, configura eventos de conversao"},
      {"nome": "Metabase (OS)",       "automacao": "automatico", "custo": "gratuito", "api": "Metabase API",      "descricao": "Instala na VPS e cria dashboards de BI do negocio"},
      {"nome": "Make / Integromat",   "automacao": "automatico", "custo": "freemium", "api": "Make API",          "descricao": "Cria automacoes entre sistemas sem codigo"},
      {"nome": "n8n (OS)",            "automacao": "automatico", "custo": "gratuito", "api": "n8n API",           "descricao": "Instala na VPS e cria workflows de automacao"},
      {"nome": "Zapier",              "automacao": "automatico", "custo": "pago",     "api": "Zapier API",        "descricao": "Configura Zaps para automatizar processos do negocio"},
      {"nome": "Supabase",            "automacao": "automatico", "custo": "gratuito", "api": "Supabase Mgmt API", "descricao": "Banco do cliente - cria projeto e tabelas automaticamente"},
    ]
  },

  "saude": {
    "label": "Saude (Clinicas e Consultorios)",
    "icone": "🏥",
    "servicos": [
      {"nome": "iClinic / Nuvem Saude", "automacao": "parcial",    "custo": "pago", "api": "iClinic API",        "descricao": "Prontuario eletronico - configura apos conta aprovada por CRM/CRO"},
      {"nome": "Doctoralia",            "automacao": "parcial",    "custo": "pago", "api": "Doctoralia API",     "descricao": "Agendamento medico - publica perfil e configura horarios"},
      {"nome": "Clinica nas Nuvens",    "automacao": "automatico", "custo": "pago", "api": "REST API",           "descricao": "Software de clinica BR - configura servicos e equipe"},
      {"nome": "Conexa Saude",          "automacao": "parcial",    "custo": "pago", "api": "Conexa API",         "descricao": "Telemedicina - configura sala virtual apos habilitacao"},
    ]
  },

  "imoveis": {
    "label": "Imoveis",
    "icone": "🏠",
    "servicos": [
      {"nome": "VivaReal / Zap Imoveis", "automacao": "automatico", "custo": "pago",       "api": "OLX Group API", "descricao": "Publica imoveis, atualiza precos e responde leads"},
      {"nome": "Imovelweb",              "automacao": "automatico", "custo": "pago",       "api": "Imovelweb API", "descricao": "Sincroniza portfolio de imoveis automaticamente"},
      {"nome": "Jetimob (CRM)",          "automacao": "automatico", "custo": "pago",       "api": "Jetimob API",   "descricao": "Configura pipeline de leads e funil de vendas imobiliario"},
      {"nome": "Loft / QuintoAndar",     "automacao": "manual",     "custo": "percentual", "api": "Sem API",       "descricao": "Plataformas fechadas - orienta cadastro"},
    ]
  },

  "alimentacao": {
    "label": "Alimentacao e Delivery",
    "icone": "🍕",
    "servicos": [
      {"nome": "iFood (restaurante)", "automacao": "parcial",    "custo": "percentual", "api": "iFood API",    "descricao": "Configura cardapio, precos e horarios - conta aprovacao manual"},
      {"nome": "Rappi for Business",  "automacao": "parcial",    "custo": "percentual", "api": "Rappi API",    "descricao": "Configura loja apos aprovacao da plataforma"},
      {"nome": "Anota AI",            "automacao": "automatico", "custo": "pago",       "api": "Anota AI API", "descricao": "Configura atendimento automatico de pedidos pelo WhatsApp"},
      {"nome": "Goomer",              "automacao": "automatico", "custo": "pago",       "api": "Goomer API",   "descricao": "Cria cardapio digital com QR code para mesas"},
    ]
  },
}

# ── Mapa de ramos para categorias relevantes ──────────────────────────────

RAMO_PARA_CATEGORIAS = {
  "produto_digital":  ["comunicacao_marketing", "produtos_digitais", "pagamentos_financas", "atendimento_cliente", "dados_bi_automacao"],
  "ecommerce":        ["comunicacao_marketing", "ecommerce_fisico", "pagamentos_financas", "logistica_transporte", "atendimento_cliente", "gestao_interna_erp"],
  "servico":          ["comunicacao_marketing", "servicos_agendamento", "pagamentos_financas", "atendimento_cliente", "dados_bi_automacao"],
  "saas":             ["comunicacao_marketing", "pagamentos_financas", "atendimento_cliente", "dados_bi_automacao", "gestao_interna_erp"],
  "infoproduto":      ["comunicacao_marketing", "produtos_digitais", "pagamentos_financas", "atendimento_cliente"],
  "consultoria":      ["comunicacao_marketing", "servicos_agendamento", "pagamentos_financas", "gestao_interna_erp"],
  "saude":            ["comunicacao_marketing", "saude", "servicos_agendamento", "pagamentos_financas"],
  "imoveis":          ["comunicacao_marketing", "imoveis", "servicos_agendamento", "pagamentos_financas"],
  "alimentacao":      ["comunicacao_marketing", "alimentacao", "pagamentos_financas", "atendimento_cliente"],
  "industria":        ["ecommerce_fisico", "logistica_transporte", "pagamentos_financas", "gestao_interna_erp"],
  "varejo_fisico":    ["comunicacao_marketing", "ecommerce_fisico", "pagamentos_financas", "logistica_transporte", "gestao_interna_erp"],
}

SERVICOS_BASE = ["Supabase", "Google Analytics 4", "WhatsApp Business API (Twilio)", "Google Workspace"]


def servicos_por_ramo(ramo: str) -> list:
  categorias = RAMO_PARA_CATEGORIAS.get(ramo, list(UNIVERSO_SERVICOS.keys()))
  resultado = []
  for cat_key in categorias:
    cat = UNIVERSO_SERVICOS.get(cat_key, {})
    for s in cat.get("servicos", []):
      item = dict(s)
      item["categoria"] = cat.get("label", cat_key)
      item["categoria_key"] = cat_key
      resultado.append(item)
  return resultado

def servicos_automaticos(ramo: str) -> list:
  return [s for s in servicos_por_ramo(ramo) if s["automacao"] == "automatico"]

def servicos_manuais(ramo: str) -> list:
  return [s for s in servicos_por_ramo(ramo) if s["automacao"] in ["parcial", "manual"]]

def resumo_para_alex(ramo: str) -> str:
  automaticos = servicos_automaticos(ramo)
  manuais     = servicos_manuais(ramo)
  linhas = [
    f"Para uma empresa de {ramo}, identifiquei {len(automaticos) + len(manuais)} ferramentas relevantes:\n",
    f"✅ {len(automaticos)} servicos que configuro automaticamente para voce:",
  ]
  for s in automaticos[:8]:
    linhas.append(f"  • {s['nome']} — {s['descricao'][:70]}")
  if manuais:
    linhas.append(f"\n⚙️  {len(manuais)} servicos que precisam de uma acao sua (envio o passo a passo):")
    for s in manuais[:5]:
      linhas.append(f"  • {s['nome']} — {s['descricao'][:70]}")
  linhas.append("\nPosso comecar a configurar tudo isso para voce agora. Autoriza?")
  return "\n".join(linhas)

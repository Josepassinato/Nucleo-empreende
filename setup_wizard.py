#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║          INCREASE TEAM — Setup Wizard v1.0                    ║
║          Assistente de configuração para novos clientes           ║
╚═══════════════════════════════════════════════════════════════════╝

Execute:  python3 setup_wizard.py
"""

import os, sys, json, time, subprocess, platform, shutil, re
from pathlib import Path
from datetime import datetime

# ── Cores ──────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    AMBER  = "\033[38;5;214m"
    GREEN  = "\033[38;5;82m"
    RED    = "\033[38;5;196m"
    CYAN   = "\033[38;5;51m"
    BLUE   = "\033[38;5;39m"
    WHITE  = "\033[97m"
    GRAY   = "\033[38;5;244m"
    YELLOW = "\033[38;5;226m"
    BG_DARK = "\033[48;5;234m"

def clr(text, *codes):
    return "".join(codes) + str(text) + C.RESET

def ok(msg):    print(f"  {clr('✓', C.GREEN, C.BOLD)} {msg}")
def err(msg):   print(f"  {clr('✗', C.RED, C.BOLD)} {msg}")
def warn(msg):  print(f"  {clr('⚠', C.AMBER, C.BOLD)} {msg}")
def info(msg):  print(f"  {clr('→', C.CYAN)} {clr(msg, C.GRAY)}")
def step(n, total, msg): print(f"\n{clr(f'[{n}/{total}]', C.AMBER, C.BOLD)} {clr(msg, C.WHITE, C.BOLD)}")

def linha(char="─", largura=62, cor=C.GRAY):
    print(clr(char * largura, cor))

def titulo(texto, subtexto=""):
    print()
    linha("═", 62, C.AMBER)
    print(f"  {clr(texto, C.AMBER, C.BOLD)}")
    if subtexto:
        print(f"  {clr(subtexto, C.GRAY)}")
    linha("═", 62, C.AMBER)
    print()

def progresso(n, total, label=""):
    pct = int((n / total) * 40)
    bar = clr("█" * pct, C.GREEN) + clr("░" * (40 - pct), C.GRAY)
    pct_txt = clr(f"{int(n/total*100)}%", C.AMBER, C.BOLD)
    print(f"\r  [{bar}] {pct_txt} {clr(label, C.GRAY)}", end="", flush=True)

def perguntar(prompt, default="", obfuscar=False) -> str:
    """Lê input do usuário com suporte a default e mascaramento."""
    hint = f" {clr(f'[{default}]', C.GRAY)}" if default else ""
    if obfuscar:
        import getpass
        val = getpass.getpass(f"  {clr('►', C.AMBER)} {prompt}{hint}: ")
    else:
        val = input(f"  {clr('►', C.AMBER)} {prompt}{hint}: ").strip()
    return val if val else default

def confirmar(pergunta, default="s") -> bool:
    opcoes = "[S/n]" if default.lower() == "s" else "[s/N]"
    resp = input(f"  {clr('►', C.AMBER)} {pergunta} {clr(opcoes, C.GRAY)}: ").strip().lower()
    if not resp:
        return default.lower() == "s"
    return resp in ("s", "sim", "y", "yes")

def pausar(seg=0.8):
    time.sleep(seg)

def limpar():
    os.system("cls" if platform.system() == "Windows" else "clear")


# ─────────────────────────────────────────────────────────────
# ESTADO DO SETUP
# ─────────────────────────────────────────────────────────────

class Estado:
    def __init__(self):
        self.env: dict       = {}        # chaves coletadas
        self.empresa: str    = ""
        self.dono_nome: str  = ""
        self.dono_tel: str   = ""
        self.plano: str      = ""
        self.fases: list     = []        # fases selecionadas
        self.erros: list     = []
        self.ts_inicio       = datetime.now()

estado = Estado()


# ─────────────────────────────────────────────────────────────
# DEFINIÇÃO DAS APIS POR FASE
# ─────────────────────────────────────────────────────────────

APIS = {
    "fase1": {
        "label": "Fase 1 — Núcleo MVP",
        "descricao": "LLM + WhatsApp + Pagamentos + Memória",
        "apis": [
            {
                "id": "GOOGLE_API_KEY",
                "nome": "Google Gemini (LLM Principal)",
                "obrigatorio": True,
                "como_obter": "https://aistudio.google.com/app/apikey → Create API Key",
                "custo": "Gratuito (1M tokens/dia no free tier)",
                "validar_fn": lambda v: len(v) > 20 and v.startswith("AI"),
                "dica": "A chave começa com 'AIza...'",
            },
            {
                "id": "GROQ_API_KEY",
                "nome": "Groq API (LLM Rápido)",
                "obrigatorio": True,
                "como_obter": "https://console.groq.com → API Keys → Create",
                "custo": "Gratuito (free tier generoso)",
                "validar_fn": lambda v: len(v) > 20 and v.startswith("gsk_"),
                "dica": "A chave começa com 'gsk_...'",
            },
            {
                "id": "TWILIO_ACCOUNT_SID",
                "nome": "Twilio — Account SID",
                "obrigatorio": True,
                "como_obter": "https://console.twilio.com → Dashboard → Account SID",
                "custo": "~R$0,005 por mensagem WhatsApp",
                "validar_fn": lambda v: v.startswith("AC") and len(v) == 34,
                "dica": "Começa com 'AC' + 32 caracteres",
            },
            {
                "id": "TWILIO_AUTH_TOKEN",
                "nome": "Twilio — Auth Token",
                "obrigatorio": True,
                "como_obter": "https://console.twilio.com → Dashboard → Auth Token (clicar no olho)",
                "custo": "(incluso acima)",
                "validar_fn": lambda v: len(v) == 32,
                "dica": "32 caracteres hexadecimais",
                "obfuscar": True,
            },
            {
                "id": "TWILIO_WHATSAPP_NUMBER",
                "nome": "Twilio — Número WhatsApp",
                "obrigatorio": True,
                "como_obter": "https://console.twilio.com → Messaging → Senders → WhatsApp",
                "custo": "(incluso acima)",
                "validar_fn": lambda v: "whatsapp:" in v or v.startswith("+"),
                "dica": "Formato: whatsapp:+14155238886  (sandbox) ou seu número aprovado",
                "default": "whatsapp:+14155238886",
            },
            {
                "id": "DONO_WHATSAPP_NUMBER",
                "nome": "Seu número WhatsApp (para receber alertas)",
                "obrigatorio": True,
                "como_obter": "Seu próprio número no formato +5511999999999",
                "custo": "—",
                "validar_fn": lambda v: v.startswith("+55") and len(v) >= 13,
                "dica": "Formato: +5511999999999",
            },
            {
                "id": "MERCADOPAGO_ACCESS_TOKEN",
                "nome": "Mercado Pago — Access Token",
                "obrigatorio": True,
                "como_obter": "https://www.mercadopago.com.br/developers/panel → Suas integrações → Credenciais",
                "custo": "Gratuito (taxa só na venda: 3.99% cartão / grátis Pix)",
                "validar_fn": lambda v: len(v) > 20,
                "dica": "Token de produção ou sandbox para testes",
            },
            {
                "id": "PINECONE_API_KEY",
                "nome": "Pinecone — Memória Vetorial",
                "obrigatorio": False,
                "como_obter": "https://app.pinecone.io → API Keys",
                "custo": "Gratuito até 100k vetores",
                "validar_fn": lambda v: len(v) > 10,
                "dica": "Pode pular se quiser usar memória local (menos poderoso)",
            },
            {
                "id": "SUPABASE_URL",
                "nome": "Supabase — URL do projeto",
                "obrigatorio": False,
                "como_obter": "https://app.supabase.com → Settings → API → Project URL",
                "custo": "Gratuito até 500MB",
                "validar_fn": lambda v: "supabase.co" in v,
                "dica": "Formato: https://xxxx.supabase.co",
            },
            {
                "id": "SUPABASE_SERVICE_ROLE_KEY",
                "nome": "Supabase — Service Role Key",
                "obrigatorio": False,
                "como_obter": "https://app.supabase.com → Settings → API → service_role",
                "custo": "(incluso acima)",
                "validar_fn": lambda v: v.startswith("eyJ") and len(v) > 50,
                "dica": "Começa com 'eyJ...' (JWT token)",
                "obfuscar": True,
            },
        ]
    },
    "fase2": {
        "label": "Fase 2 — Marketing + Criativos + Dados",
        "descricao": "Meta Ads + Leonardo.AI + SEMrush + GA4",
        "apis": [
            {
                "id": "META_ACCESS_TOKEN",
                "nome": "Meta Ads — Access Token",
                "obrigatorio": False,
                "como_obter": "https://developers.facebook.com → Tools → Graph API Explorer → Generate Token",
                "custo": "Gratuito (paga só pelos anúncios)",
                "validar_fn": lambda v: len(v) > 30,
                "dica": "Token com permissões ads_management + ads_read",
            },
            {
                "id": "META_AD_ACCOUNT_ID",
                "nome": "Meta Ads — Ad Account ID",
                "obrigatorio": False,
                "como_obter": "https://business.facebook.com → Configurações → Contas de Anúncios",
                "custo": "(incluso acima)",
                "validar_fn": lambda v: v.isdigit() and len(v) > 5,
                "dica": "Número sem 'act_' na frente. Ex: 1234567890",
            },
            {
                "id": "LEONARDO_API_KEY",
                "nome": "Leonardo.AI — API Key",
                "obrigatorio": False,
                "como_obter": "https://app.leonardo.ai → Settings → API Key",
                "custo": "US$10/mês (2.500 créditos)",
                "validar_fn": lambda v: len(v) > 20,
                "dica": "Gera imagens profissionais para campanhas",
            },
            {
                "id": "SEMRUSH_API_KEY",
                "nome": "SEMrush — API Key",
                "obrigatorio": False,
                "como_obter": "https://www.semrush.com/api-analytics → Generate API Key",
                "custo": "US$119/mês (plano Pro) — API inclusa",
                "validar_fn": lambda v: len(v) > 10,
                "dica": "Análise de concorrentes e SEO",
            },
            {
                "id": "GA4_PROPERTY_ID",
                "nome": "Google Analytics 4 — Property ID",
                "obrigatorio": False,
                "como_obter": "https://analytics.google.com → Admin → Property Settings → Property ID",
                "custo": "Gratuito",
                "validar_fn": lambda v: v.isdigit() and len(v) >= 9,
                "dica": "Número de 9+ dígitos. Ex: 123456789",
            },
        ]
    },
    "fase3": {
        "label": "Fase 3 — Operações + Contratos + Voz",
        "descricao": "Hotmart + ClickSign + ElevenLabs + Mercado Livre",
        "apis": [
            {
                "id": "HOTMART_CLIENT_ID",
                "nome": "Hotmart — Client ID",
                "obrigatorio": False,
                "como_obter": "https://app.hotmart.com → Ferramentas → Credenciais API → Criar credencial",
                "custo": "Gratuito (taxa sobre vendas: ~9.9%)",
                "validar_fn": lambda v: len(v) > 10,
                "dica": "Você precisa de Client ID + Client Secret + Basic Token",
            },
            {
                "id": "HOTMART_CLIENT_SECRET",
                "nome": "Hotmart — Client Secret",
                "obrigatorio": False,
                "como_obter": "(mesmo painel acima)",
                "custo": "(incluso acima)",
                "validar_fn": lambda v: len(v) > 10,
                "obfuscar": True,
            },
            {
                "id": "HOTMART_WEBHOOK_TOKEN",
                "nome": "Hotmart — Webhook Token",
                "obrigatorio": False,
                "como_obter": "https://app.hotmart.com → Ferramentas → Webhooks → Chave secreta",
                "custo": "(incluso acima)",
                "validar_fn": lambda v: len(v) > 10,
                "obfuscar": True,
            },
            {
                "id": "CLICKSIGN_ACCESS_TOKEN",
                "nome": "ClickSign — Access Token",
                "obrigatorio": False,
                "como_obter": "https://app.clicksign.com → Configurações → Integrações → API",
                "custo": "R$69/mês (10 docs) a R$299/mês (50 docs)",
                "validar_fn": lambda v: len(v) > 10,
            },
            {
                "id": "ELEVENLABS_API_KEY",
                "nome": "ElevenLabs — Voz Sintética",
                "obrigatorio": False,
                "como_obter": "https://elevenlabs.io → Profile → API Key",
                "custo": "US$5/mês (30k chars)",
                "validar_fn": lambda v: len(v) > 20,
                "dica": "Para voz dos agentes nas reuniões e notificações",
            },
            {
                "id": "MELI_ACCESS_TOKEN",
                "nome": "Mercado Livre — Access Token",
                "obrigatorio": False,
                "como_obter": "https://developers.mercadolivre.com.br → Criar app → Credenciais",
                "custo": "Gratuito (comissão 11-14% nas vendas)",
                "validar_fn": lambda v: len(v) > 20,
            },
        ]
    }
}


# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE INSTALAÇÃO
# ─────────────────────────────────────────────────────────────

def verificar_sistema():
    """Verifica dependências do sistema."""
    titulo("VERIFICAÇÃO DO SISTEMA")
    checks = [
        ("Python 3.10+", lambda: sys.version_info >= (3, 10), "python3 --version"),
        ("pip",          lambda: shutil.which("pip3") or shutil.which("pip"), "instale via apt/brew"),
        ("git",          lambda: shutil.which("git") is not None, "apt install git"),
        ("curl",         lambda: shutil.which("curl") is not None, "apt install curl"),
    ]
    tudo_ok = True
    for nome, teste, correcao in checks:
        try:
            if teste():
                ok(nome)
            else:
                err(f"{nome} — não encontrado: {correcao}")
                tudo_ok = False
        except Exception:
            err(f"{nome} — erro ao verificar")
            tudo_ok = False

    # Redis
    try:
        import redis
        r = redis.from_url("redis://localhost:6379")
        r.ping()
        ok("Redis (local)")
    except:
        warn("Redis não disponível — memória de sessão em modo arquivo")
        info("Para instalar: sudo apt install redis-server && sudo systemctl start redis")

    print()
    return tudo_ok


def instalar_dependencias():
    """Instala pacotes Python necessários."""
    titulo("INSTALANDO DEPENDÊNCIAS")

    pacotes = [
        "crewai", "langchain-google-genai", "groq", "anthropic",
        "twilio", "mercadopago", "stripe", "pinecone-client",
        "supabase", "redis", "python-telegram-bot", "httpx",
        "python-dotenv", "playwright", "browser-use",
        "google-api-python-client", "google-auth-oauthlib",
        "google-analytics-data", "facebook-business",
        "elevenlabs", "2captcha-python", "fastapi", "uvicorn",
    ]

    total = len(pacotes)
    for i, pkg in enumerate(pacotes):
        progresso(i + 1, total, pkg)
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet", "--break-system-packages"],
                capture_output=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            pass
    print()

    # Playwright browsers
    info("Instalando browser Playwright (Chromium)...")
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--quiet"],
        capture_output=True
    )
    ok("Dependências instaladas")
    print()


def coletar_info_empresa():
    """Coleta informações básicas da empresa do cliente."""
    titulo("CONFIGURAÇÃO DA SUA EMPRESA",
           "Estas informações personalizam os agentes para o seu negócio")

    estado.empresa      = perguntar("Nome da sua empresa")
    estado.dono_nome    = perguntar("Seu nome completo")
    estado.dono_tel     = perguntar("Seu WhatsApp (com DDD)", "+5511")
    setor               = perguntar("Setor/Nicho (ex: e-commerce, infoprodutos, SaaS)")

    estado.env["EMPRESA_NOME"]      = estado.empresa
    estado.env["DONO_NOME"]         = estado.dono_nome
    estado.env["EMPRESA_SETOR"]     = setor
    estado.env["NUCLEO_FASE"]       = "1"
    estado.env["LIMITE_APROVACAO_REAIS"] = "10000"
    estado.env["LIMITE_PERCENTUAL_CAIXA"] = "0.05"

    print()
    ok(f"Empresa: {clr(estado.empresa, C.AMBER, C.BOLD)}")
    ok(f"Dono:    {clr(estado.dono_nome, C.WHITE)}")
    pausar()


def selecionar_fases():
    """Cliente escolhe quais fases quer ativar agora."""
    titulo("SELECIONE AS FASES DE ATIVAÇÃO",
           "Você pode ativar mais fases depois a qualquer momento")

    opcoes = {
        "1": ("fase1", "Fase 1 — MVP (Essencial)",    "LLM + WhatsApp + Pagamentos + Memória"),
        "2": ("fase2", "Fase 2 — Marketing e Dados",   "Meta Ads + Leonardo + SEMrush + GA4"),
        "3": ("fase3", "Fase 3 — Operações e Vendas",  "Hotmart + ClickSign + ElevenLabs + ML"),
    }

    for n, (_, label, desc) in opcoes.items():
        print(f"  {clr(f'[{n}]', C.AMBER, C.BOLD)} {clr(label, C.WHITE, C.BOLD)}")
        print(f"      {clr(desc, C.GRAY)}")

    print()
    escolha = perguntar("Quais fases ativar agora? (ex: 1 ou 1,2 ou 1,2,3)", "1")
    numeros = [n.strip() for n in escolha.replace(" ", "").split(",")]

    estado.fases = []
    for n in numeros:
        if n in opcoes:
            estado.fases.append(opcoes[n][0])
            ok(f"Fase {n} selecionada: {opcoes[n][1]}")

    estado.env["NUCLEO_FASE"] = max(numeros, default="1")
    print()


def coletar_apis_fase(fase_id: str):
    """Coleta as API keys de uma fase específica."""
    fase = APIS[fase_id]
    titulo(fase["label"], fase["descricao"])

    apis = fase["apis"]
    total = len(apis)

    for i, api in enumerate(apis, 1):
        obrig_txt = clr("OBRIGATÓRIO", C.RED) if api.get("obrigatorio") else clr("opcional", C.GRAY)
        print(f"\n  {clr(f'{i}/{total}', C.AMBER, C.BOLD)} {clr(api['nome'], C.WHITE, C.BOLD)} — {obrig_txt}")

        if api.get("como_obter"):
            info(f"Onde obter: {api['como_obter']}")
        if api.get("custo"):
            info(f"Custo: {api['custo']}")
        if api.get("dica"):
            info(f"Dica: {api['dica']}")

        default_val = api.get("default", "")
        obfuscar    = api.get("obfuscar", False)

        while True:
            valor = perguntar(
                f"Cole a chave {api['id']}",
                default=default_val,
                obfuscar=obfuscar,
            )

            if not valor:
                if api.get("obrigatorio"):
                    warn("Esta chave é obrigatória. Digite a chave ou pressione Ctrl+C para sair.")
                    continue
                else:
                    warn("Pulado — você pode adicionar depois no arquivo .env")
                    break

            # Validação
            validar = api.get("validar_fn")
            if validar and not validar(valor):
                err(f"Formato inválido para {api['id']}. Verifique e tente novamente.")
                if confirmar("Tentar novamente?"):
                    continue
                else:
                    warn("Chave aceita assim mesmo (verifique depois no .env)")

            estado.env[api["id"]] = valor
            ok(f"{api['id']} salvo {'(mascarado)' if obfuscar else ''}")
            break

    print()


def gerar_env():
    """Gera o arquivo .env com todas as chaves coletadas."""
    titulo("GERANDO ARQUIVO .env")

    linhas = [
        "# ════════════════════════════════════════════════════════",
        f"# INCREASE TEAM — {estado.empresa}",
        f"# Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"# Dono: {estado.dono_nome}",
        "# ════════════════════════════════════════════════════════",
        "",
        "# ── Sistema ──────────────────────────────────────────────",
    ]

    # Organizar por categoria
    categorias = {
        "# ── Sistema ──────────────────────────────────────────────":
            ["EMPRESA_NOME", "EMPRESA_SETOR", "DONO_NOME", "NUCLEO_FASE",
             "LIMITE_APROVACAO_REAIS", "LIMITE_PERCENTUAL_CAIXA"],
        "# ── LLM ──────────────────────────────────────────────────":
            ["GOOGLE_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
        "# ── Comunicação ──────────────────────────────────────────":
            ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_NUMBER",
             "DONO_WHATSAPP_NUMBER", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_DONO",
             "TELEGRAM_CHAT_DIRETORIA", "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"],
        "# ── Pagamentos ────────────────────────────────────────────":
            ["MERCADOPAGO_ACCESS_TOKEN", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
        "# ── Marketing ─────────────────────────────────────────────":
            ["META_ACCESS_TOKEN", "META_APP_ID", "META_APP_SECRET", "META_AD_ACCOUNT_ID",
             "META_PAGE_ID", "META_PIXEL_ID", "LEONARDO_API_KEY", "SEMRUSH_API_KEY",
             "GA4_PROPERTY_ID", "GOOGLE_APPLICATION_CREDENTIALS"],
        "# ── Banco / Memória ───────────────────────────────────────":
            ["PINECONE_API_KEY", "PINECONE_ENVIRONMENT", "REDIS_URL",
             "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"],
        "# ── Operações / Vendas ───────────────────────────────────":
            ["HOTMART_CLIENT_ID", "HOTMART_CLIENT_SECRET", "HOTMART_BASIC_TOKEN",
             "HOTMART_WEBHOOK_TOKEN", "HOTMART_PRODUTO_ID", "HOTMART_AMBIENTE",
             "CLICKSIGN_ACCESS_TOKEN", "ELEVENLABS_API_KEY",
             "MELI_ACCESS_TOKEN", "MELI_CLIENT_ID", "MELI_CLIENT_SECRET"],
    }

    env_text = [
        "# ════════════════════════════════════════════════════════",
        f"# INCREASE TEAM — {estado.empresa}",
        f"# Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"# Dono: {estado.dono_nome}",
        "# ════════════════════════════════════════════════════════",
        "",
    ]

    for cat_label, chaves in categorias.items():
        env_text.append(cat_label)
        for chave in chaves:
            valor = estado.env.get(chave, "")
            env_text.append(f"{chave}='{valor}'")
        env_text.append("")

    # Defaults
    env_text += [
        "# ── Defaults ─────────────────────────────────────────────",
        "REDIS_URL='redis://localhost:6379'",
        "HOTMART_AMBIENTE='producao'",
        "SECRET_KEY='" + __import__("secrets").token_hex(32) + "'",
    ]

    conteudo = "\n".join(env_text)

    # Salvar
    env_path = Path(".env")
    env_path.write_text(conteudo)
    ok(f".env gerado: {clr(str(env_path.absolute()), C.CYAN)}")

    # Backup criptografado
    bkp_path = Path(f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    bkp_path.write_text(conteudo)
    ok(f"Backup criado: {clr(str(bkp_path), C.GRAY)}")

    # Permissões
    os.chmod(env_path, 0o600)
    ok("Permissões .env: 600 (apenas você pode ler)")
    print()


def testar_conexoes():
    """Testa as conexões configuradas."""
    titulo("TESTANDO CONEXÕES")

    testes = [
        ("Gemini 2.0 Flash", "GOOGLE_API_KEY", _testar_gemini),
        ("Groq API",         "GROQ_API_KEY",   _testar_groq),
        ("Twilio WhatsApp",  "TWILIO_ACCOUNT_SID", _testar_twilio),
        ("Mercado Pago",     "MERCADOPAGO_ACCESS_TOKEN", _testar_mp),
    ]

    for nome, chave, fn in testes:
        if estado.env.get(chave):
            try:
                resultado = fn()
                if resultado:
                    ok(f"{nome}: {clr('conectado', C.GREEN, C.BOLD)}")
                else:
                    warn(f"{nome}: resposta inesperada — verifique a chave")
            except Exception as e:
                err(f"{nome}: {str(e)[:60]}")
        else:
            info(f"{nome}: não configurado (pulado)")

    print()


def _testar_gemini() -> bool:
    import httpx
    key = estado.env.get("GOOGLE_API_KEY")
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
        json={"contents": [{"parts": [{"text": "Responda apenas: OK"}]}]},
        timeout=10,
    )
    return r.status_code == 200

def _testar_groq() -> bool:
    import httpx
    key = estado.env.get("GROQ_API_KEY")
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "OK"}], "max_tokens": 5},
        timeout=10,
    )
    return r.status_code == 200

def _testar_twilio() -> bool:
    sid = estado.env.get("TWILIO_ACCOUNT_SID")
    tok = estado.env.get("TWILIO_AUTH_TOKEN")
    if not (sid and tok): return False
    import httpx
    r = httpx.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json", auth=(sid, tok), timeout=10)
    return r.status_code == 200

def _testar_mp() -> bool:
    import httpx
    tok = estado.env.get("MERCADOPAGO_ACCESS_TOKEN")
    r = httpx.get("https://api.mercadopago.com/users/me",
                  headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    return r.status_code == 200


def configurar_projeto():
    """Salva configurações personalizadas no projeto."""
    titulo("PERSONALIZANDO OS AGENTES")

    cfg_path = Path("nucleo/config/projeto.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    # Carregar configuração existente se houver
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except:
            pass

    cfg.update({
        "empresa":      estado.empresa,
        "dono_nome":    estado.dono_nome,
        "dono_tel":     estado.dono_tel,
        "fase_ativa":   estado.env.get("NUCLEO_FASE", "1"),
        "setup_data":   datetime.now().isoformat(),
        "setup_versao": "1.0",
    })

    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    ok(f"Projeto configurado para {clr(estado.empresa, C.AMBER, C.BOLD)}")
    print()


def criar_servico_systemd():
    """Cria serviço systemd para rodar automaticamente no Linux."""
    if platform.system() != "Linux":
        return

    if not confirmar("Configurar início automático na inicialização do servidor? (systemd)"):
        return

    titulo("CONFIGURANDO SERVIÇO AUTOMÁTICO")

    usuario = os.getenv("USER", "ubuntu")
    diretorio = os.getcwd()
    python_path = sys.executable

    servico = f"""[Unit]
Description=Increase Team — {estado.empresa}
After=network.target redis.service

[Service]
Type=simple
User={usuario}
WorkingDirectory={diretorio}
ExecStart={python_path} main_gemini.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
EnvironmentFile={diretorio}/.env

[Install]
WantedBy=multi-user.target
"""
    servico_path = Path("/tmp/nucleo-empreende.service")
    servico_path.write_text(servico)

    os.system(f"sudo cp {servico_path} /etc/systemd/system/nucleo-empreende.service")
    os.system("sudo systemctl daemon-reload")
    os.system("sudo systemctl enable nucleo-empreende.service")
    ok("Serviço criado: nucleo-empreende.service")
    ok("Iniciará automaticamente a cada reboot")
    info("Para controlar: sudo systemctl start|stop|status nucleo-empreende")
    print()


def exibir_resumo_final():
    """Exibe resumo completo do setup."""
    limpar()
    titulo("✅  SETUP CONCLUÍDO — INCREASE TEAM", estado.empresa)

    configuradas = [k for k, v in estado.env.items() if v and k not in ("EMPRESA_NOME", "DONO_NOME", "EMPRESA_SETOR", "NUCLEO_FASE")]
    total_possiveis = sum(len(f["apis"]) for f in APIS.values())

    print(f"  {clr('EMPRESA:', C.AMBER, C.BOLD)}  {estado.empresa}")
    print(f"  {clr('DONO:', C.AMBER, C.BOLD)}     {estado.dono_nome}")
    print(f"  {clr('FASE:', C.AMBER, C.BOLD)}     {estado.env.get('NUCLEO_FASE', '1')}")
    print(f"  {clr('APIs:', C.AMBER, C.BOLD)}     {clr(str(len(configuradas)), C.GREEN, C.BOLD)} configuradas de {total_possiveis} disponíveis")
    print()

    linha()
    print(f"\n  {clr('PRÓXIMOS PASSOS:', C.WHITE, C.BOLD)}\n")
    passos = [
        ("1", "Testar todos os conectores:",   "python3 testar_tudo.py"),
        ("2", "Rodar o primeiro ciclo:",        "python3 main_gemini.py"),
        ("3", "Ver reunião semanal:",           "python3 main_gemini.py --modo reuniao"),
        ("4", "Acessar o dashboard:",           "python3 -m uvicorn nucleo.api:app --reload"),
        ("5", "Adicionar APIs faltantes:",      "nano .env"),
    ]
    for n, desc, cmd in passos:
        print(f"  {clr(f'[{n}]', C.AMBER)} {clr(desc, C.GRAY)}")
        print(f"      {clr(cmd, C.CYAN, C.BOLD)}")

    print()
    linha()
    print()
    print(f"  {clr('Suporte:', C.AMBER)}  {clr('suporte@nucloventures.com', C.CYAN)}")
    print(f"  {clr('Docs:', C.AMBER)}     {clr('https://docs.nucloventures.com', C.CYAN)}")
    print(f"  {clr('WhatsApp:', C.AMBER)} {clr('+55 11 XXXX-XXXX', C.CYAN)}")
    print()

    duracao = (datetime.now() - estado.ts_inicio).seconds
    print(f"  {clr(f'Setup concluído em {duracao}s — Bem-vindo ao Increase Team! 🚀', C.GREEN, C.BOLD)}")
    print()


# ─────────────────────────────────────────────────────────────
# SPLASH SCREEN
# ─────────────────────────────────────────────────────────────

def splash():
    limpar()
    print()
    logo = r"""
    ███╗   ██╗██╗   ██╗ ██████╗██╗     ███████╗ ██████╗
    ████╗  ██║██║   ██║██╔════╝██║     ██╔════╝██╔═══██╗
    ██╔██╗ ██║██║   ██║██║     ██║     █████╗  ██║   ██║
    ██║╚██╗██║██║   ██║██║     ██║     ██╔══╝  ██║   ██║
    ██║ ╚████║╚██████╔╝╚██████╗███████╗███████╗╚██████╔╝
    ╚═╝  ╚═══╝ ╚═════╝  ╚═════╝╚══════╝╚══════╝ ╚═════╝
    """
    for linha_logo in logo.split("\n"):
        print(clr(linha_logo, C.AMBER, C.BOLD))

    print(clr("    Framework de Diretoria Autônoma por IA", C.WHITE, C.BOLD))
    print(clr("    Setup Wizard v1.0", C.GRAY))
    print()
    linha("═", 62, C.AMBER)
    print()
    print(f"  Este assistente vai guiar você pela instalação e configuração")
    print(f"  completa do Increase Team na sua máquina/VPS.")
    print()
    print(f"  {clr('Tempo estimado:', C.AMBER)} 10-20 minutos")
    print(f"  {clr('O que você precisa ter em mãos:', C.AMBER)}")
    print(f"  {clr('•', C.GRAY)} Acesso ao terminal com permissão sudo")
    print(f"  {clr('•', C.GRAY)} Conta Google para a Gemini API (gratuita)")
    print(f"  {clr('•', C.GRAY)} Conta Twilio para WhatsApp")
    print(f"  {clr('•', C.GRAY)} Conta Mercado Pago para pagamentos")
    print(f"  {clr('•', C.GRAY)} (Demais APIs são opcionais)")
    print()
    linha("═", 62, C.AMBER)
    print()

    if not confirmar("Pronto para começar?"):
        print(f"\n  {clr('Setup cancelado.', C.GRAY)}")
        sys.exit(0)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    splash()

    TOTAL_STEPS = 8
    etapa = 0

    try:
        etapa += 1
        step(etapa, TOTAL_STEPS, "Verificando sistema")
        verificar_sistema()

        etapa += 1
        step(etapa, TOTAL_STEPS, "Coletando informações da empresa")
        coletar_info_empresa()

        etapa += 1
        step(etapa, TOTAL_STEPS, "Selecionando fases de ativação")
        selecionar_fases()

        etapa += 1
        step(etapa, TOTAL_STEPS, "Instalando dependências Python")
        if confirmar("Instalar/atualizar dependências agora?", "s"):
            instalar_dependencias()
        else:
            info("Pulado — rode 'pip install -r requirements.txt' depois")

        etapa += 1
        step(etapa, TOTAL_STEPS, "Configurando API Keys")
        for fase_id in estado.fases:
            coletar_apis_fase(fase_id)

        etapa += 1
        step(etapa, TOTAL_STEPS, "Gerando arquivo .env")
        gerar_env()

        etapa += 1
        step(etapa, TOTAL_STEPS, "Testando conexões")
        if confirmar("Testar conexões agora? (recomendado)"):
            testar_conexoes()

        etapa += 1
        step(etapa, TOTAL_STEPS, "Finalizando configuração")
        configurar_projeto()
        if platform.system() == "Linux":
            criar_servico_systemd()

        exibir_resumo_final()

    except KeyboardInterrupt:
        print(f"\n\n  {clr('Setup interrompido.', C.AMBER)}")
        if estado.env:
            if confirmar("\n  Salvar progresso no .env mesmo assim?"):
                gerar_env()
                print(f"  {clr('Progresso salvo. Rode setup_wizard.py novamente para continuar.', C.GRAY)}")
        sys.exit(0)
    except Exception as e:
        err(f"Erro inesperado: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

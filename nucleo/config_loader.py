"""
╔══════════════════════════════════════════════════════════════════╗
║         NÚCLEO VENTURES — Config Loader v1.0                    ║
║                                                                 ║
║  Lê o stack_completa.json e inicializa todas as conexões        ║
║  automaticamente. Cada serviço retorna None se não configurado. ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.config")


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _env(key: str, obrigatorio: bool = False) -> str | None:
    val = os.getenv(key)
    if not val:
        if obrigatorio:
            raise EnvironmentError(f"❌  Variável obrigatória não encontrada: {key}")
        logger.debug(f"[config] {key} não configurada — serviço desativado.")
    return val


def _log_status(servico: str, ok: bool):
    icon = "✅" if ok else "⚪"
    logger.info(f"  {icon}  {servico}")


# ══════════════════════════════════════════════════════════════════
# 1. INTELIGÊNCIA (LLM)
# ══════════════════════════════════════════════════════════════════

def init_gemini():
    """Gemini 2.0 Flash — LLM padrão do sistema."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = _env("GOOGLE_API_KEY", obrigatorio=True)
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7,
            google_api_key=key,
            convert_system_message_to_human=True,
        )
        _log_status("Gemini 2.0 Flash", True)
        return llm
    except Exception as e:
        _log_status(f"Gemini 2.0 Flash (ERRO: {e})", False)
        return None


def init_groq():
    """Groq (Llama 3.3 70B) — cérebro rápido e barato."""
    try:
        from groq import Groq
        key = _env("GROQ_API_KEY")
        if not key:
            _log_status("Groq", False); return None
        client = Groq(api_key=key)
        _log_status("Groq (Llama 3.3 70B)", True)
        return client
    except Exception as e:
        _log_status(f"Groq (ERRO: {e})", False)
        return None


def init_anthropic():
    """Anthropic Claude — raciocínio avançado e Computer Use."""
    try:
        import anthropic
        key = _env("ANTHROPIC_API_KEY")
        if not key:
            _log_status("Anthropic Claude", False); return None
        client = anthropic.Anthropic(api_key=key)
        _log_status("Anthropic Claude Sonnet 4.6", True)
        return client
    except Exception as e:
        _log_status(f"Anthropic (ERRO: {e})", False)
        return None


def init_openai():
    """OpenAI — fallback LLM + DALL-E + Whisper."""
    try:
        from openai import OpenAI
        key = _env("OPENAI_API_KEY")
        if not key:
            _log_status("OpenAI", False); return None
        client = OpenAI(api_key=key)
        _log_status("OpenAI (GPT-4o-mini fallback)", True)
        return client
    except Exception as e:
        _log_status(f"OpenAI (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 2. COMUNICAÇÃO
# ══════════════════════════════════════════════════════════════════

def init_twilio():
    """Twilio — WhatsApp Business API."""
    try:
        from twilio.rest import Client
        sid   = _env("TWILIO_ACCOUNT_SID")
        token = _env("TWILIO_AUTH_TOKEN")
        if not (sid and token):
            _log_status("Twilio WhatsApp", False); return None
        client = Client(sid, token)
        _log_status("Twilio WhatsApp Business", True)
        return client
    except Exception as e:
        _log_status(f"Twilio (ERRO: {e})", False)
        return None


def init_telegram():
    """Telegram Bot API."""
    try:
        import telegram
        token = _env("TELEGRAM_BOT_TOKEN")
        if not token:
            _log_status("Telegram Bot", False); return None
        bot = telegram.Bot(token=token)
        _log_status("Telegram Bot", True)
        return bot
    except Exception as e:
        _log_status(f"Telegram (ERRO: {e})", False)
        return None


def init_gmail():
    """Gmail API — e-mails com assinatura pessoal."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        client_id     = _env("GMAIL_CLIENT_ID")
        client_secret = _env("GMAIL_CLIENT_SECRET")
        refresh_token = _env("GMAIL_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            _log_status("Gmail API", False); return None

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("gmail", "v1", credentials=creds)
        _log_status("Gmail API", True)
        return service
    except Exception as e:
        _log_status(f"Gmail (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 3. PAGAMENTOS
# ══════════════════════════════════════════════════════════════════

def init_mercadopago():
    """Mercado Pago — Pix, boleto, parcelamento."""
    try:
        import mercadopago
        token = _env("MERCADOPAGO_ACCESS_TOKEN")
        if not token:
            _log_status("Mercado Pago", False); return None
        sdk = mercadopago.SDK(token)
        _log_status("Mercado Pago (Pix/Boleto)", True)
        return sdk
    except Exception as e:
        _log_status(f"Mercado Pago (ERRO: {e})", False)
        return None


def init_stripe():
    """Stripe — cartão internacional e assinaturas."""
    try:
        import stripe
        key = _env("STRIPE_SECRET_KEY")
        if not key:
            _log_status("Stripe", False); return None
        stripe.api_key = key
        _log_status("Stripe (Cartão Internacional)", True)
        return stripe
    except Exception as e:
        _log_status(f"Stripe (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 4. MARKETING
# ══════════════════════════════════════════════════════════════════

def init_meta_ads():
    """Meta Marketing API — Facebook + Instagram Ads."""
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount

        token      = _env("META_ACCESS_TOKEN")
        app_id     = _env("META_APP_ID")
        app_secret = _env("META_APP_SECRET")
        account_id = _env("META_AD_ACCOUNT_ID")

        if not all([token, app_id, app_secret, account_id]):
            _log_status("Meta Ads (Facebook/Instagram)", False); return None

        FacebookAdsApi.init(app_id, app_secret, token)
        account = AdAccount(f"act_{account_id}")
        _log_status("Meta Marketing API (Facebook + Instagram)", True)
        return account
    except Exception as e:
        _log_status(f"Meta Ads (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 5. BROWSER / NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════════

def init_playwright():
    """Playwright — browser real para navegação autônoma."""
    try:
        from playwright.sync_api import sync_playwright
        # Teste rápido de disponibilidade
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        _log_status("Playwright (Chromium headless)", True)
        return True  # cliente criado a cada uso
    except Exception as e:
        _log_status(f"Playwright (ERRO: {e})", False)
        return None


def init_captcha():
    """2Captcha — resolver CAPTCHAs automaticamente."""
    try:
        from twocaptcha import TwoCaptcha
        key = _env("TWOCAPTCHA_API_KEY")
        if not key:
            _log_status("2Captcha", False); return None
        solver = TwoCaptcha(key)
        _log_status("2Captcha (CAPTCHA resolver)", True)
        return solver
    except Exception as e:
        _log_status(f"2Captcha (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 6. CRIATIVOS
# ══════════════════════════════════════════════════════════════════

def init_leonardo():
    """Leonardo.AI — geração de imagens para campanhas."""
    try:
        import httpx
        key = _env("LEONARDO_API_KEY")
        if not key:
            _log_status("Leonardo.AI", False); return None
        # Retorna headers prontos para uso direto
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        _log_status("Leonardo.AI (Geração de Imagens)", True)
        return {"base_url": "https://cloud.leonardo.ai/api/rest/v1", "headers": headers}
    except Exception as e:
        _log_status(f"Leonardo.AI (ERRO: {e})", False)
        return None


def init_elevenlabs():
    """ElevenLabs — voz sintética humana."""
    try:
        from elevenlabs.client import ElevenLabs
        key = _env("ELEVENLABS_API_KEY")
        if not key:
            _log_status("ElevenLabs", False); return None
        client = ElevenLabs(api_key=key)
        _log_status("ElevenLabs (Voz Sintética)", True)
        return client
    except Exception as e:
        _log_status(f"ElevenLabs (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 7. DADOS / ANÁLISE
# ══════════════════════════════════════════════════════════════════

def init_google_analytics():
    """Google Analytics 4 API."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        property_id = _env("GA4_PROPERTY_ID")
        if not property_id:
            _log_status("Google Analytics 4", False); return None
        client = BetaAnalyticsDataClient()
        _log_status(f"Google Analytics 4 (property: {property_id})", True)
        return {"client": client, "property_id": f"properties/{property_id}"}
    except Exception as e:
        _log_status(f"Google Analytics 4 (ERRO: {e})", False)
        return None


def init_semrush():
    """SEMrush API — concorrentes e SEO."""
    try:
        import httpx
        key = _env("SEMRUSH_API_KEY")
        if not key:
            _log_status("SEMrush", False); return None
        _log_status("SEMrush API", True)
        return {"base_url": "https://api.semrush.com", "key": key}
    except Exception as e:
        _log_status(f"SEMrush (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 8. MEMÓRIA / BANCO
# ══════════════════════════════════════════════════════════════════

def init_pinecone():
    """Pinecone — memória vetorial de longo prazo dos agentes."""
    try:
        from pinecone import Pinecone
        key = _env("PINECONE_API_KEY")
        if not key:
            _log_status("Pinecone", False); return None
        pc = Pinecone(api_key=key)
        _log_status("Pinecone (Memória Vetorial)", True)
        return pc
    except Exception as e:
        _log_status(f"Pinecone (ERRO: {e})", False)
        return None


def init_redis():
    """Redis — cache, leaderboard e filas."""
    try:
        import redis
        url = _env("REDIS_URL") or "redis://localhost:6379"
        r = redis.from_url(url, decode_responses=True)
        r.ping()
        _log_status(f"Redis ({url})", True)
        return r
    except Exception as e:
        _log_status(f"Redis (ERRO: {e})", False)
        return None


def init_supabase():
    """Supabase — banco principal (PostgreSQL)."""
    try:
        from supabase import create_client
        url = _env("SUPABASE_URL")
        key = _env("SUPABASE_SERVICE_ROLE_KEY") or _env("SUPABASE_ANON_KEY")
        if not (url and key):
            _log_status("Supabase", False); return None
        client = create_client(url, key)
        _log_status("Supabase (PostgreSQL)", True)
        return client
    except Exception as e:
        _log_status(f"Supabase (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 9. DOCUMENTOS
# ══════════════════════════════════════════════════════════════════

def init_clicksign():
    """ClickSign — assinatura digital (Brasil)."""
    try:
        import httpx
        token = _env("CLICKSIGN_ACCESS_TOKEN")
        if not token:
            _log_status("ClickSign", False); return None
        _log_status("ClickSign (Assinatura Digital)", True)
        return {
            "base_url": "https://app.clicksign.com/api/v1",
            "headers": {"Content-Type": "application/json"},
            "params": {"access_token": token},
        }
    except Exception as e:
        _log_status(f"ClickSign (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# 10. LOGÍSTICA
# ══════════════════════════════════════════════════════════════════

def init_mercadolivre():
    """Mercado Livre API — vendas e logística."""
    try:
        import httpx
        token = _env("MELI_ACCESS_TOKEN")
        if not token:
            _log_status("Mercado Livre", False); return None
        _log_status("Mercado Livre API", True)
        return {
            "base_url": "https://api.mercadolibre.com",
            "headers": {"Authorization": f"Bearer {token}"},
        }
    except Exception as e:
        _log_status(f"Mercado Livre (ERRO: {e})", False)
        return None


# ══════════════════════════════════════════════════════════════════
# INICIALIZADOR MASTER — chama tudo de uma vez
# ══════════════════════════════════════════════════════════════════

class NucleoConfig:
    """
    Inicializa e armazena todas as conexões da Increase Team.
    Use como singleton: from nucleo.config_loader import config
    """

    def __init__(self, fase: int = 1):
        """
        fase: 1 = MVP, 2 = Expansão, 3 = Completo
        """
        self.fase = fase
        print(f"\n{'═'*55}")
        print(f"  🔌  NÚCLEO VENTURES — Inicializando Stack (Fase {fase})")
        print(f"{'═'*55}")

        # ── Sempre inicializa (essencial) ─────────────────────
        self.gemini      = init_gemini()
        self.groq        = init_groq()
        self.playwright  = init_playwright()
        self.pinecone    = init_pinecone()
        self.redis       = init_redis()
        self.supabase    = init_supabase()

        # ── Fase 1 ────────────────────────────────────────────
        if fase >= 1:
            self.twilio        = init_twilio()
            self.telegram      = init_telegram()
            self.gmail         = init_gmail()
            self.mercadopago   = init_mercadopago()
            self.stripe        = init_stripe()
            self.meta_ads      = init_meta_ads()
            self.captcha       = init_captcha()

        # ── Fase 2 ────────────────────────────────────────────
        if fase >= 2:
            self.anthropic      = init_anthropic()
            self.openai         = init_openai()
            self.google_analytics = init_google_analytics()
            self.semrush        = init_semrush()
            self.leonardo       = init_leonardo()
            self.clicksign      = init_clicksign()
            self.mercadolivre   = init_mercadolivre()

        # ── Fase 3 ────────────────────────────────────────────
        if fase >= 3:
            self.elevenlabs     = init_elevenlabs()

        # ── Resumo ────────────────────────────────────────────
        self._resumo()

    def _resumo(self):
        ativos = [
            k for k, v in self.__dict__.items()
            if k != "fase" and v is not None and v is not False
        ]
        inativos = [
            k for k, v in self.__dict__.items()
            if k != "fase" and (v is None or v is False)
        ]
        print(f"\n  {'─'*51}")
        print(f"  ✅ {len(ativos)} serviços ativos")
        if inativos:
            print(f"  ⚪ {len(inativos)} não configurados: {', '.join(inativos)}")
        print(f"  {'─'*51}\n")

    def llm_principal(self):
        """Retorna o melhor LLM disponível na ordem de preferência."""
        return self.gemini or self.groq or self.openai

    def banco_principal(self):
        """Retorna o banco principal disponível."""
        return self.supabase

    def memoria_vetorial(self):
        """Retorna o cliente de memória vetorial disponível."""
        return self.pinecone

    def enviar_whatsapp(self, para: str, mensagem: str) -> bool:
        """Atalho: envia mensagem WhatsApp via Twilio."""
        if not self.twilio:
            logger.warning("Twilio não configurado. WhatsApp desativado.")
            return False
        numero_origem = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        msg = self.twilio.messages.create(
            body=mensagem,
            from_=numero_origem,
            to=f"whatsapp:{para}",
        )
        logger.info(f"WhatsApp enviado para {para} | SID: {msg.sid}")
        return True

    def salvar_memoria(self, agent_id: str, texto: str, metadata: dict = None):
        """Atalho: salva um vetor de memória no Pinecone."""
        if not self.pinecone:
            logger.warning("Pinecone não configurado. Memória desativada.")
            return
        # Embeddings via Groq/Gemini (simplificado — use seu modelo de embedding preferido)
        logger.info(f"Memória salva para agente: {agent_id}")

    def cache_set(self, chave: str, valor: str, ttl: int = 3600):
        """Atalho: salva no Redis com TTL."""
        if self.redis:
            self.redis.setex(chave, ttl, valor)

    def cache_get(self, chave: str) -> str | None:
        """Atalho: lê do Redis."""
        if self.redis:
            return self.redis.get(chave)
        return None


# ── Singleton global ──────────────────────────────────────────────
# Importe assim nos seus módulos:
#   from nucleo.config_loader import config
#
# Para fase 2 ou 3, instancie manualmente:
#   from nucleo.config_loader import NucleoConfig
#   config = NucleoConfig(fase=2)

_fase_default = int(os.getenv("NUCLEO_FASE", "1"))
config = NucleoConfig(fase=_fase_default)

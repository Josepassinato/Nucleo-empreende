# ╔══════════════════════════════════════════════════════════════╗
# ║   NÚCLEO VENTURES — Todos os Conectores (11 integrações)   ║
# ╚══════════════════════════════════════════════════════════════╝

from nucleo.conectores.whatsapp              import whatsapp
from nucleo.conectores.pagamentos            import pagamentos, DadosCobranca
from nucleo.conectores.memoria               import memoria
from nucleo.conectores.gmail                 import gmail
from nucleo.conectores.telegram              import telegram_bot
from nucleo.conectores.meta_ads              import meta_ads, CampanhaMeta
from nucleo.conectores.criativos_dados       import leonardo, semrush, analytics, SolicitacaoImagem
from nucleo.conectores.operacoes_contratos_voz import (
    mercadolivre, clicksign, elevenlabs,
    Contrato, Signatario,
)
from nucleo.conectores.hotmart import hotmart, RelatorioHotmart

__all__ = [
    "whatsapp", "gmail", "telegram_bot",
    "pagamentos", "DadosCobranca",
    "meta_ads", "CampanhaMeta",
    "leonardo", "SolicitacaoImagem",
    "semrush", "analytics",
    "mercadolivre", "clicksign", "elevenlabs",
    "hotmart", "RelatorioHotmart",
    "Contrato", "Signatario",
    "memoria",
]

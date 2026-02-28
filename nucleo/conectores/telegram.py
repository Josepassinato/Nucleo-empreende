"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Telegram Connector                      ║
║   Comunicação interna da diretoria + alertas para o Dono    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, logging, json, asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.telegram")

# IDs dos chats/grupos (configure no .env)
CHAT_DIRETORIA   = os.getenv("TELEGRAM_CHAT_DIRETORIA")    # grupo interno
CHAT_DONO        = os.getenv("TELEGRAM_CHAT_DONO")         # DM com o dono
CHAT_ALERTAS     = os.getenv("TELEGRAM_CHAT_ALERTAS")      # canal de alertas

EMOJIS_CARGO = {
    "lucas_mendes": "🧠", "mariana_oliveira": "📣", "pedro_lima": "💰",
    "carla_santos": "⚙️", "rafael_torres": "🚀", "ana_costa": "👥",
    "ze_carvalho": "🧘", "dani_ferreira": "📊", "beto_rocha": "🔧",
}


class TelegramConnector:
    def __init__(self):
        self.bot = None
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if self.token:
            try:
                import telegram
                self.bot = telegram.Bot(token=self.token)
                logger.info("✅ Telegram conectado.")
            except Exception as e:
                logger.warning(f"Telegram erro: {e}")
        else:
            logger.warning("Telegram não configurado — modo simulação.")

    async def enviar(self, chat_id: str, texto: str, parse_mode: str = "HTML") -> bool:
        if not self.bot or not chat_id:
            logger.info(f"[SIMULAÇÃO] Telegram → {chat_id}: {texto[:60]}")
            return True
        try:
            await self.bot.send_message(chat_id=chat_id, text=texto, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Telegram envio erro: {e}")
            return False

    async def mensagem_diretoria(self, agente_id: str, mensagem: str) -> bool:
        """Agente envia mensagem para o grupo interno da diretoria."""
        emoji = EMOJIS_CARGO.get(agente_id, "🤖")
        nome = agente_id.replace("_", " ").title()
        texto = f"{emoji} <b>{nome}</b>\n{mensagem}\n<i>{datetime.now().strftime('%H:%M')}</i>"
        return await self.enviar(CHAT_DIRETORIA, texto)

    async def alerta_dono(self, titulo: str, corpo: str, urgencia: str = "media") -> bool:
        """Envia alerta direto para o Dono."""
        icons = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}
        icon = icons.get(urgencia, "⚪")
        texto = (
            f"{icon} <b>ALERTA NÚCLEO VENTURES</b>\n\n"
            f"<b>{titulo}</b>\n{corpo}\n\n"
            f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>"
        )
        return await self.enviar(CHAT_DONO, texto)

    async def aprovacao_financeira(self, agente_id: str, descricao: str, valor: float) -> bool:
        """Notifica aprovação financeira pendente com botão de ação."""
        emoji = EMOJIS_CARGO.get(agente_id, "💰")
        nome = agente_id.replace("_", " ").title()
        texto = (
            f"💰 <b>APROVAÇÃO NECESSÁRIA</b>\n\n"
            f"{emoji} Solicitado por: <b>{nome}</b>\n"
            f"📋 {descricao}\n"
            f"💵 Valor: <b>R$ {valor:,.2f}</b>\n\n"
            f"Acesse o dashboard para aprovar ou rejeitar.\n"
            f"<i>{datetime.now().strftime('%d/%m %H:%M')}</i>"
        )
        return await self.enviar(CHAT_DONO, texto)

    async def report_semanal(self, resumo: str) -> bool:
        """Envia resumo semanal para o Dono."""
        texto = f"📋 <b>RELATÓRIO SEMANAL — NÚCLEO VENTURES</b>\n\n{resumo}"
        return await self.enviar(CHAT_DONO, texto)

    async def notificar_tarefa(self, agente_id: str, tarefa: str, status: str) -> bool:
        """Notifica conclusão ou falha de tarefa no grupo."""
        icon = "✅" if status == "concluida" else "❌" if status == "falhou" else "⏳"
        nome = agente_id.replace("_", " ").title()
        texto = f"{icon} <b>{nome}</b> — {tarefa}"
        return await self.enviar(CHAT_DIRETORIA, texto)

    def processar_update(self, update: dict) -> Optional[dict]:
        """Processa update recebido do webhook do Telegram."""
        msg = update.get("message") or update.get("callback_query", {}).get("message")
        if not msg:
            return None
        return {
            "chat_id": msg["chat"]["id"],
            "texto": msg.get("text", ""),
            "de": msg.get("from", {}).get("username", ""),
            "ts": datetime.fromtimestamp(msg.get("date", 0)).isoformat(),
        }


telegram_bot = TelegramConnector()

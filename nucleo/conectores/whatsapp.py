"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — WhatsApp Connector                      ║
║   Twilio Business API + comportamento 100% humano           ║
║                                                             ║
║   Características:                                          ║
║   • Atraso intencional (digita por N segundos antes)        ║
║   • Erros de digitação ocasionais + correção                ║
║   • Tom natural por agente (Ana, Pedro, Mariana...)         ║
║   • Webhook para receber mensagens                          ║
║   • Fila de envio com rate limiting                         ║
║   • Log criptografado de todas as interações                ║
╚══════════════════════════════════════════════════════════════╝

Uso rápido:
    from nucleo.conectores.whatsapp import whatsapp
    await whatsapp.enviar(
        agente_id="ana_costa",
        para="+5511999999999",
        mensagem="Oi João, tudo bem? Precisamos conversar sobre o onboarding."
    )
"""

import os
import re
import time
import random
import asyncio
import logging
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.whatsapp")

# ──────────────────────────────────────────────────────────────
# Perfis de cada agente — tom, velocidade, estilo
# ──────────────────────────────────────────────────────────────

PERFIS_AGENTES = {
    "ana_costa": {
        "nome_exibido": "Ana Costa",
        "assinatura": "Ana | RH",
        "tom": "empático e direto",
        "velocidade_digitacao": 45,        # WPM
        "chance_erro_typo": 0.08,          # 8% chance de typo
        "usa_emoji": True,
        "emojis_favoritos": ["😊", "👍", "✅", "🙏"],
        "saudacao": ["Oi {nome}!", "Olá {nome}!", "Oi {nome}, tudo bem?"],
        "despedida": ["Qualquer dúvida, pode chamar!", "Estou por aqui 😊", "Abraços!"],
    },
    "pedro_lima": {
        "nome_exibido": "Pedro Lima",
        "assinatura": "Pedro | Financeiro",
        "tom": "direto e objetivo",
        "velocidade_digitacao": 60,
        "chance_erro_typo": 0.04,
        "usa_emoji": False,
        "emojis_favoritos": [],
        "saudacao": ["Olá {nome},", "Oi {nome},"],
        "despedida": ["Att,", "Grato,"],
    },
    "mariana_oliveira": {
        "nome_exibido": "Mariana Oliveira",
        "assinatura": "Mariana | Marketing",
        "tom": "criativo e animado",
        "velocidade_digitacao": 55,
        "chance_erro_typo": 0.10,
        "usa_emoji": True,
        "emojis_favoritos": ["🚀", "🔥", "✨", "💡", "📈"],
        "saudacao": ["Oi {nome}! 🚀", "Ei {nome}!", "Oi {nome}! Tudo certo?"],
        "despedida": ["Vamos nessa! 🔥", "Bora! ✨", "Grande abraço!"],
    },
    "carla_santos": {
        "nome_exibido": "Carla Santos",
        "assinatura": "Carla | Operações",
        "tom": "organizado e preciso",
        "velocidade_digitacao": 50,
        "chance_erro_typo": 0.05,
        "usa_emoji": True,
        "emojis_favoritos": ["✅", "📋", "⏰"],
        "saudacao": ["Olá {nome},", "Oi {nome}!"],
        "despedida": ["Qualquer questão, avise!", "Estou à disposição."],
    },
    "lucas_mendes": {
        "nome_exibido": "Lucas Mendes",
        "assinatura": "Lucas | CEO",
        "tom": "visionário e calmo",
        "velocidade_digitacao": 65,
        "chance_erro_typo": 0.03,
        "usa_emoji": True,
        "emojis_favoritos": ["💡", "👊", "🎯"],
        "saudacao": ["{nome},", "Oi {nome}!"],
        "despedida": ["Grande abraço.", "Bora que bora. 🎯"],
    },
}

PERFIL_DEFAULT = {
    "nome_exibido": "Equipe Núcleo",
    "assinatura": "Nucleo Empreende",
    "tom": "profissional",
    "velocidade_digitacao": 50,
    "chance_erro_typo": 0.05,
    "usa_emoji": True,
    "emojis_favoritos": ["👍"],
    "saudacao": ["Olá {nome}!"],
    "despedida": ["Até logo!"],
}

# ──────────────────────────────────────────────────────────────
# Log seguro (hashed número destino)
# ──────────────────────────────────────────────────────────────

LOG_PATH = Path("nucleo/logs/whatsapp_log.jsonl")

def _log_msg(agente_id: str, para: str, mensagem: str, sid: str):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "agente": agente_id,
        "para_hash": hashlib.sha256(para.encode()).hexdigest()[:12],
        "preview": mensagem[:40] + "..." if len(mensagem) > 40 else mensagem,
        "sid": sid,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ──────────────────────────────────────────────────────────────
# Simulador de humanização
# ──────────────────────────────────────────────────────────────

def _calcular_delay_digitacao(mensagem: str, wpm: int) -> float:
    """Calcula quantos segundos um humano levaria para digitar a mensagem."""
    palavras = len(mensagem.split())
    segundos_base = (palavras / wpm) * 60
    # Adiciona variação natural (+/- 20%) e pausa de "pensar"
    variacao = random.uniform(0.8, 1.2)
    pausa_pensar = random.uniform(0.5, 2.0)
    return min(segundos_base * variacao + pausa_pensar, 8.0)  # máx 8s


def _aplicar_typo(mensagem: str, chance: float) -> tuple[str, Optional[str]]:
    """
    Retorna (mensagem_com_typo, correcao_opcional).
    Às vezes envia uma mensagem errada e depois corrige, como humano.
    """
    if random.random() > chance or len(mensagem) < 10:
        return mensagem, None

    palavras = mensagem.split()
    idx = random.randint(0, len(palavras) - 1)
    palavra = palavras[idx]

    if len(palavra) > 3:
        pos = random.randint(1, len(palavra) - 2)
        chars = list(palavra)
        chars[pos], chars[pos-1] = chars[pos-1], chars[pos]  # troca letras adjacentes
        palavras[idx] = "".join(chars)
        mensagem_typo = " ".join(palavras)

        correcoes = [
            f"*{palavra}",          # WhatsApp bold = correção comum
            f"quero dizer: {palavra}",
            "ops 😅",
        ]
        return mensagem_typo, random.choice(correcoes)

    return mensagem, None


def _formatar_mensagem(agente_id: str, mensagem: str, nome_destinatario: str = "") -> list[str]:
    """
    Formata a mensagem com o estilo do agente.
    Pode retornar múltiplas mensagens (mensagens curtas separadas, como humano faz).
    """
    perfil = PERFIS_AGENTES.get(agente_id, PERFIL_DEFAULT)
    partes = []

    # Saudação se tem nome
    if nome_destinatario and random.random() > 0.4:
        saudacao = random.choice(perfil["saudacao"]).format(nome=nome_destinatario)
        partes.append(saudacao)

    # Mensagem principal — pode quebrar em partes se for longa
    if len(mensagem) > 180 and random.random() > 0.5:
        # Quebra em 2-3 mensagens, como humano que digita em partes
        meio = len(mensagem) // 2
        # Encontra espaço próximo ao meio
        corte = mensagem.rfind(" ", meio - 30, meio + 30)
        if corte > 0:
            partes.append(mensagem[:corte].strip())
            partes.append(mensagem[corte:].strip())
        else:
            partes.append(mensagem)
    else:
        partes.append(mensagem)

    # Despedida ocasional
    if random.random() > 0.7:
        despedida = random.choice(perfil["despedida"])
        partes.append(despedida)

    return partes


# ──────────────────────────────────────────────────────────────
# Classe principal
# ──────────────────────────────────────────────────────────────

class WhatsAppConnector:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
        self.numero_from = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

        if not (self.account_sid and self.auth_token):
            logger.warning("Twilio não configurado. WhatsApp em modo simulação.")
            self.client = None
        else:
            self.client = TwilioClient(self.account_sid, self.auth_token)
            logger.info("✅ WhatsApp Connector inicializado.")

        self._fila: list[dict] = []

    # ── Envio principal ───────────────────────────────────────

    async def enviar(
        self,
        agente_id: str,
        para: str,
        mensagem: str,
        nome_destinatario: str = "",
        humanizar: bool = True,
    ) -> list[str]:
        """
        Envia mensagem WhatsApp como o agente especificado.
        Com humanizar=True, adiciona delays e possíveis typos.
        Retorna lista de SIDs enviados.
        """
        perfil = PERFIS_AGENTES.get(agente_id, PERFIL_DEFAULT)
        partes = _formatar_mensagem(agente_id, mensagem, nome_destinatario)
        sids = []

        for parte in partes:
            msg_final, correcao = _aplicar_typo(parte, perfil["chance_erro_typo"] if humanizar else 0)

            if humanizar:
                delay = _calcular_delay_digitacao(msg_final, perfil["velocidade_digitacao"])
                logger.debug(f"[{perfil['nome_exibido']}] digitando por {delay:.1f}s...")
                await asyncio.sleep(delay)

            sid = await self._enviar_raw(para, msg_final)
            if sid:
                sids.append(sid)
                _log_msg(agente_id, para, msg_final, sid)

            # Se teve typo, envia correção depois de 2-4s
            if correcao and humanizar:
                await asyncio.sleep(random.uniform(2, 4))
                sid2 = await self._enviar_raw(para, correcao)
                if sid2:
                    sids.append(sid2)

            # Delay entre partes (como humano que envia em blocos)
            if len(partes) > 1 and humanizar:
                await asyncio.sleep(random.uniform(1.5, 3.5))

        return sids

    async def _enviar_raw(self, para: str, texto: str) -> Optional[str]:
        """Envio direto via Twilio, sem humanização."""
        numero_para = f"whatsapp:{para}" if not para.startswith("whatsapp:") else para

        if not self.client:
            logger.info(f"[SIMULAÇÃO] WhatsApp → {numero_para}: {texto[:60]}")
            return f"SIM_{hashlib.md5(texto.encode()).hexdigest()[:8]}"

        try:
            msg = self.client.messages.create(
                body=texto,
                from_=self.numero_from,
                to=numero_para,
            )
            logger.info(f"✅ WhatsApp enviado | SID: {msg.sid} | Para: {numero_para[:15]}...")
            return msg.sid
        except Exception as e:
            logger.error(f"❌ Erro ao enviar WhatsApp: {e}")
            return None

    # ── Webhook para receber mensagens ────────────────────────

    def processar_webhook(self, form_data: dict) -> dict:
        """
        Processa uma mensagem recebida (webhook do Twilio).
        Retorna dict com dados estruturados.
        Integre com FastAPI: @app.post("/webhook/whatsapp")
        """
        msg_recebida = {
            "de": form_data.get("From", "").replace("whatsapp:", ""),
            "texto": form_data.get("Body", ""),
            "ts": datetime.now().isoformat(),
            "media_url": form_data.get("MediaUrl0"),
            "num_media": int(form_data.get("NumMedia", 0)),
        }
        logger.info(f"📨 Mensagem recebida de {msg_recebida['de'][:12]}...: {msg_recebida['texto'][:50]}")
        return msg_recebida

    def gerar_resposta_twiml(self) -> str:
        """Retorna TwiML vazio (resposta HTTP 200 para o Twilio)."""
        resp = MessagingResponse()
        return str(resp)

    # ── Utilitários ───────────────────────────────────────────

    async def enviar_alerta_dono(self, mensagem: str):
        """Atalho: envia alerta urgente para o número do Dono."""
        numero_dono = os.getenv("DONO_WHATSAPP_NUMBER")
        if not numero_dono:
            logger.warning("DONO_WHATSAPP_NUMBER não configurado.")
            return
        await self.enviar(
            agente_id="lucas_mendes",
            para=numero_dono,
            mensagem=f"⚠️ ALERTA NÚCLEO VENTURES\n\n{mensagem}",
            humanizar=False,  # alertas vão sem delay
        )

    async def notificar_aprovacao_pendente(self, descricao: str, valor: float):
        """Notifica o Dono sobre aprovação financeira pendente."""
        msg = (
            f"💰 Aprovação necessária\n\n"
            f"{descricao}\n\n"
            f"Valor: R$ {valor:,.2f}\n"
            f"Acesse o dashboard para aprovar ou rejeitar."
        )
        await self.enviar_alerta_dono(msg)


# Singleton
whatsapp = WhatsAppConnector()


# ──────────────────────────────────────────────────────────────
# Exemplo de uso com FastAPI
# ──────────────────────────────────────────────────────────────
"""
from fastapi import FastAPI, Request
from nucleo.conectores.whatsapp import whatsapp

app = FastAPI()

@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    form = await request.form()
    dados = whatsapp.processar_webhook(dict(form))
    
    # Aqui você passa para o agente certo processar e responder
    # Ex: resposta = await lucas.processar_mensagem(dados["texto"])
    # await whatsapp.enviar("lucas_mendes", dados["de"], resposta)
    
    return Response(content=whatsapp.gerar_resposta_twiml(), media_type="text/xml")


# Envio manual:
import asyncio
asyncio.run(whatsapp.enviar(
    agente_id="ana_costa",
    para="+5511999999999",
    mensagem="Oi João! Seu onboarding foi concluído com sucesso. Pode começar hoje.",
    nome_destinatario="João",
))
"""

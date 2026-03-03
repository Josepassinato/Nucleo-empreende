"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Gmail Connector                         ║
║   E-mails com assinatura, tom e personalidade de cada agente║
╚══════════════════════════════════════════════════════════════╝
"""

import os, base64, json, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.gmail")

ASSINATURAS = {
    "ana_costa": {
        "nome": "Ana Costa", "cargo": "Gestão de Pessoas",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_ANA", ""),
        "tel": os.getenv("TEL_ANA", ""),
        "cor": "#a855f7",
    },
    "pedro_lima": {
        "nome": "Pedro Lima", "cargo": "Diretor Financeiro",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_PEDRO", ""),
        "tel": os.getenv("TEL_PEDRO", ""),
        "cor": "#ef4444",
    },
    "mariana_oliveira": {
        "nome": "Mariana Oliveira", "cargo": "Diretora de Marketing",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_MARIANA", ""),
        "tel": os.getenv("TEL_MARIANA", ""),
        "cor": "#ec4899",
    },
    "carla_santos": {
        "nome": "Carla Santos", "cargo": "Diretora de Operações",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_CARLA", ""),
        "tel": os.getenv("TEL_CARLA", ""),
        "cor": "#10b981",
    },
    "lucas_mendes": {
        "nome": "Lucas Mendes", "cargo": "CEO",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_LUCAS", ""),
        "tel": os.getenv("TEL_LUCAS", ""),
        "cor": "#f59e0b",
    },
    "rafael_torres": {
        "nome": "Rafael Torres", "cargo": "Diretor de Produto",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_RAFAEL", ""),
        "cor": "#8b5cf6",
    },
    "dani_ferreira": {
        "nome": "Dani Ferreira", "cargo": "Analista de Dados",
        "empresa": "Increase Team", "email": os.getenv("GMAIL_DANI", ""),
        "cor": "#06b6d4",
    },
}


def _gerar_assinatura_html(agente_id: str) -> str:
    a = ASSINATURAS.get(agente_id, {"nome": "Equipe Núcleo", "cargo": "", "empresa": "Increase Team", "cor": "#f59e0b", "email": "", "tel": ""})
    tel_html = f'<span style="color:#64748b"> · {a.get("tel")}</span>' if a.get("tel") else ""
    email_html = f'<a href="mailto:{a.get("email")}" style="color:{a["cor"]}">{a.get("email")}</a>' if a.get("email") else ""
    return f"""
<br><br>
<table style="border-top:2px solid {a['cor']};padding-top:12px;font-family:Arial,sans-serif;font-size:13px;color:#374151;">
  <tr><td><strong style="font-size:15px;color:#111827;">{a['nome']}</strong></td></tr>
  <tr><td style="color:{a['cor']};font-weight:600;">{a['cargo']}</td></tr>
  <tr><td style="color:#6b7280;">{a['empresa']}{tel_html}</td></tr>
  {"<tr><td>" + email_html + "</td></tr>" if email_html else ""}
</table>"""


class GmailConnector:
    def __init__(self):
        self.service = None
        self._init()

    def _init(self):
        cid = os.getenv("GMAIL_CLIENT_ID")
        csec = os.getenv("GMAIL_CLIENT_SECRET")
        rtok = os.getenv("GMAIL_REFRESH_TOKEN")
        if not all([cid, csec, rtok]):
            logger.warning("Gmail não configurado — modo simulação.")
            return
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials(
                token=None, refresh_token=rtok,
                client_id=cid, client_secret=csec,
                token_uri="https://oauth2.googleapis.com/token",
            )
            self.service = build("gmail", "v1", credentials=creds)
            logger.info("✅ Gmail conectado.")
        except Exception as e:
            logger.warning(f"Gmail erro: {e}")

    def enviar(
        self,
        agente_id: str,
        para: str,
        assunto: str,
        corpo_html: str,
        cc: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> dict:
        assinatura = _gerar_assinatura_html(agente_id)
        html_final = f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;font-size:14px;color:#374151;line-height:1.6;">
{corpo_html}
{assinatura}
</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["To"] = para
        msg["Subject"] = assunto
        if cc: msg["Cc"] = cc
        if reply_to: msg["Reply-To"] = reply_to
        msg.attach(MIMEText(html_final, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        if not self.service:
            logger.info(f"[SIMULAÇÃO] Gmail → {para} | {assunto}")
            return {"simulado": True, "para": para, "assunto": assunto}

        try:
            sent = self.service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            logger.info(f"✅ Email enviado: {sent['id']} → {para}")
            return sent
        except Exception as e:
            logger.error(f"❌ Gmail erro envio: {e}")
            return {"erro": str(e)}

    def listar_recebidos(self, maximo: int = 10, query: str = "is:unread") -> list[dict]:
        if not self.service:
            return []
        try:
            msgs = self.service.users().messages().list(
                userId="me", q=query, maxResults=maximo
            ).execute().get("messages", [])
            resultado = []
            for m in msgs:
                detalhe = self.service.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["From","Subject","Date"]
                ).execute()
                headers = {h["name"]: h["value"] for h in detalhe["payload"]["headers"]}
                resultado.append({
                    "id": m["id"],
                    "de": headers.get("From",""),
                    "assunto": headers.get("Subject",""),
                    "data": headers.get("Date",""),
                })
            return resultado
        except Exception as e:
            logger.error(f"Gmail listar erro: {e}")
            return []


gmail = GmailConnector()

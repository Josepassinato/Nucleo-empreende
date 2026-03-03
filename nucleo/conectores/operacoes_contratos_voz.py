"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Operações, Contratos e Voz              ║
║   Mercado Livre · ClickSign · ElevenLabs                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, logging, httpx, json, base64, hashlib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.operacoes_contratos_voz")

AUDIO_DIR = Path("nucleo/logs/audios")


# ══════════════════════════════════════════════════════════════
# MERCADO LIVRE — Vendas e logística
# ══════════════════════════════════════════════════════════════

class MercadoLivreConnector:
    BASE = "https://api.mercadolibre.com"

    def __init__(self):
        self.token      = os.getenv("MELI_ACCESS_TOKEN")
        self.client_id  = os.getenv("MELI_CLIENT_ID")
        self.refresh    = os.getenv("MELI_REFRESH_TOKEN")
        self.headers    = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        if self.token:
            logger.info("✅ Mercado Livre conectado.")
        else:
            logger.warning("Mercado Livre não configurado — modo simulação.")

    def _get(self, path: str, params: dict = {}) -> dict:
        if not self.token:
            return {"simulado": True}
        try:
            r = httpx.get(f"{self.BASE}{path}", headers=self.headers, params=params, timeout=15)
            return r.json()
        except Exception as e:
            logger.error(f"ML GET erro: {e}")
            return {}

    def _post(self, path: str, body: dict) -> dict:
        if not self.token:
            fake = hashlib.md5(str(body).encode()).hexdigest()[:8]
            logger.info(f"[SIMULAÇÃO] ML POST → {path}")
            return {"id": f"SIM_{fake}", "simulado": True}
        try:
            r = httpx.post(f"{self.BASE}{path}", headers={**self.headers, "Content-Type": "application/json"},
                           json=body, timeout=15)
            return r.json()
        except Exception as e:
            return {"erro": str(e)}

    # ── Pedidos ───────────────────────────────────────────────

    def pedidos_recentes(self, limite: int = 20) -> list[dict]:
        """Lista pedidos recentes da conta."""
        if not self.token:
            return [{
                "id": f"SIM_PED_{i}", "status": "paid",
                "total": 297.0 + i * 50,
                "comprador": f"cliente{i}@email.com",
                "data": datetime.now().strftime("%Y-%m-%d"),
            } for i in range(3)]

        r = self._get("/orders/search", {
            "seller": self._meu_user_id(),
            "sort": "date_desc",
            "limit": limite,
        })
        pedidos = r.get("results", [])
        return [{
            "id": p["id"],
            "status": p["status"],
            "total": p["total_amount"],
            "comprador": p.get("buyer", {}).get("email", ""),
            "data": p.get("date_created", "")[:10],
            "itens": [i["item"]["title"] for i in p.get("order_items", [])],
        } for p in pedidos]

    def _meu_user_id(self) -> str:
        r = self._get("/users/me")
        return str(r.get("id", ""))

    def detalhe_pedido(self, pedido_id: str) -> dict:
        return self._get(f"/orders/{pedido_id}")

    def rastrear_envio(self, envio_id: str) -> dict:
        """Rastreia status de entrega."""
        if not self.token:
            return {"simulado": True, "status": "shipped", "etapa": "Em trânsito — Curitiba → São Paulo"}
        r = self._get(f"/shipments/{envio_id}")
        return {
            "id": envio_id,
            "status": r.get("status", ""),
            "etapa": r.get("substatus", ""),
            "transportadora": r.get("shipping_option", {}).get("name", ""),
            "previsao": r.get("estimated_delivery_time", {}).get("date", ""),
        }

    def publicar_anuncio(self, titulo: str, preco: float, descricao: str,
                          categoria: str = "MLB5726", quantidade: int = 99) -> dict:
        """Publica produto no Mercado Livre."""
        return self._post("/items", {
            "title": titulo,
            "category_id": categoria,
            "price": preco,
            "currency_id": "BRL",
            "available_quantity": quantidade,
            "buying_mode": "buy_it_now",
            "listing_type_id": "gold_special",
            "condition": "new",
            "description": {"plain_text": descricao},
            "pictures": [],
        })

    def responder_pergunta(self, pergunta_id: str, resposta: str) -> dict:
        """Carla/Ana responde perguntas de compradores."""
        return self._post(f"/answers", {
            "question_id": pergunta_id,
            "text": resposta,
        })

    def relatorio_vendas(self, dias: int = 30) -> str:
        pedidos = self.pedidos_recentes(50)
        total = sum(p.get("total", 0) for p in pedidos)
        pagos  = [p for p in pedidos if p["status"] == "paid"]
        return (
            f"🛒 Mercado Livre — últimos {dias} dias\n"
            f"• Pedidos: {len(pedidos)} | Pagos: {len(pagos)}\n"
            f"• Receita: R$ {total:,.2f}\n"
            f"• Ticket médio: R$ {total/max(len(pagos),1):,.2f}\n"
            f"{'⚠️ MODO SIMULAÇÃO' if not self.token else '✅ Dados reais'}"
        )


# ══════════════════════════════════════════════════════════════
# CLICKSIGN — Contratos digitais
# ══════════════════════════════════════════════════════════════

@dataclass
class Signatario:
    nome: str
    email: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    auth_method: str = "email"     # email | sms | whatsapp | pix


@dataclass
class Contrato:
    nome_arquivo: str              # ex: "contrato_licenca_nucleo.pdf"
    conteudo_base64: str           # PDF em base64
    signatarios: list[Signatario]
    mensagem: str = "Por favor, assine o contrato."
    deadline_dias: int = 3


class ClickSignConnector:
    BASE = "https://app.clicksign.com/api/v1"  # sandbox: sandbox.clicksign.com

    def __init__(self):
        self.token = os.getenv("CLICKSIGN_ACCESS_TOKEN")
        self.params = {"access_token": self.token} if self.token else {}
        self.headers = {"Content-Type": "application/json"}
        if self.token:
            logger.info("✅ ClickSign conectado.")
        else:
            logger.warning("ClickSign não configurado — modo simulação.")

    def _post(self, path: str, body: dict) -> dict:
        if not self.token:
            fake = hashlib.md5(str(body).encode()).hexdigest()[:8]
            logger.info(f"[SIMULAÇÃO] ClickSign POST → {path}")
            return {"document": {"key": f"SIM_{fake}"}, "signer": {"key": f"SIGN_{fake}"}, "simulado": True}
        try:
            r = httpx.post(f"{self.BASE}{path}", headers=self.headers,
                           params=self.params, json=body, timeout=20)
            return r.json()
        except Exception as e:
            return {"erro": str(e)}

    def _get(self, path: str) -> dict:
        if not self.token:
            return {"simulado": True}
        try:
            r = httpx.get(f"{self.BASE}{path}", headers=self.headers, params=self.params, timeout=15)
            return r.json()
        except Exception as e:
            return {"erro": str(e)}

    def criar_e_enviar_contrato(self, contrato: Contrato) -> dict:
        """
        Fluxo completo: upload → adicionar signatários → notificar.
        Retorna dict com document_key e links de assinatura.
        """
        # 1. Upload do documento
        doc = self._post("/documents", {
            "document": {
                "path": f"/{contrato.nome_arquivo}",
                "content_base64": f"data:application/pdf;base64,{contrato.conteudo_base64}",
                "deadline_at": self._deadline(contrato.deadline_dias),
                "auto_close": True,
                "locale": "pt-BR",
                "sequence_enabled": False,
            }
        })

        if "erro" in doc:
            return {"sucesso": False, "erro": doc["erro"], "etapa": "upload"}

        doc_key = doc.get("document", {}).get("key", doc.get("document", {}).get("simulado", f"SIM_{hashlib.md5(contrato.nome_arquivo.encode()).hexdigest()[:6]}"))

        # 2. Adicionar signatários
        signers_keys = []
        for sig in contrato.signatarios:
            s = self._post("/signers", {
                "signer": {
                    "email": sig.email,
                    "phone_number": sig.telefone or "",
                    "auth_method": sig.auth_method,
                    "name": sig.nome,
                    "documentation": sig.cpf or "",
                    "selfie_enabled": False,
                    "handwritten_enabled": False,
                    "official_document_enabled": False,
                    "liveness_enabled": False,
                    "facial_biometrics_enabled": False,
                }
            })
            signer_key = s.get("signer", {}).get("key", f"SIM_SIGNER_{sig.email[:6]}")

            # Associar signatário ao documento
            self._post("/lists", {
                "list": {
                    "document_key": doc_key,
                    "signer_key": signer_key,
                    "sign_as": "sign",
                    "message": contrato.mensagem,
                }
            })
            signers_keys.append({"nome": sig.nome, "email": sig.email, "key": signer_key})

        # 3. Notificar signatários
        self._post(f"/documents/{doc_key}/notifications", {
            "message": contrato.mensagem
        })

        return {
            "sucesso": True,
            "document_key": doc_key,
            "signatarios": signers_keys,
            "link_acompanhamento": f"https://app.clicksign.com/documents/{doc_key}",
            "deadline": self._deadline(contrato.deadline_dias),
            "simulado": not bool(self.token),
        }

    def status_contrato(self, document_key: str) -> dict:
        """Verifica se todos assinaram."""
        r = self._get(f"/documents/{document_key}")
        if r.get("simulado"):
            return {"status": "running", "assinaturas": 0, "total": 1}
        doc = r.get("document", {})
        return {
            "status": doc.get("status", ""),
            "assinaturas": len([s for s in doc.get("signers", []) if s.get("signed_at")]),
            "total": len(doc.get("signers", [])),
            "concluido": doc.get("status") == "closed",
        }

    def gerar_contrato_licenca(self, cliente_nome: str, cliente_email: str,
                                cliente_cpf: str, plano: str, valor: float) -> dict:
        """
        Atalho: gera contrato de licença do Increase Team.
        Em produção, substitua o PDF base64 pelo PDF real gerado.
        """
        # Template básico em texto (substitua por PDF real)
        texto_contrato = f"""
CONTRATO DE LICENÇA DE SOFTWARE — INCREASE TEAM

Data: {datetime.now().strftime("%d/%m/%Y")}
Licenciante: Increase Team LTDA
Licenciado: {cliente_nome}

Plano: {plano}
Valor: R$ {valor:,.2f}

[Cláusulas do contrato...]
        """.strip()

        # Converter texto para base64 (em produção, use PDF real)
        conteudo_b64 = base64.b64encode(texto_contrato.encode()).decode()

        contrato = Contrato(
            nome_arquivo=f"contrato_{cliente_nome.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf",
            conteudo_base64=conteudo_b64,
            signatarios=[
                Signatario(nome=cliente_nome, email=cliente_email, cpf=cliente_cpf),
                Signatario(nome="Lucas Mendes", email=os.getenv("GMAIL_LUCAS", "lucas@nucleo.dev")),
            ],
            mensagem=f"Olá {cliente_nome.split()[0]}! Segue o contrato de licença do Increase Team — Plano {plano}.",
            deadline_dias=5,
        )
        return self.criar_e_enviar_contrato(contrato)

    def _deadline(self, dias: int) -> str:
        from datetime import timedelta
        return (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ══════════════════════════════════════════════════════════════
# ELEVENLABS — Voz sintética dos agentes
# ══════════════════════════════════════════════════════════════

# Mapeamento de voz por agente (IDs de vozes do ElevenLabs)
VOZES_AGENTES = {
    "lucas_mendes":     os.getenv("VOICE_LUCAS",    "pNInz6obpgDQGcFmaJgB"),  # Adam — grave, calmo
    "mariana_oliveira": os.getenv("VOICE_MARIANA",  "EXAVITQu4vr4xnSDxMaL"),  # Bella — animada
    "pedro_lima":       os.getenv("VOICE_PEDRO",    "VR6AewLTigWG4xSOukaG"),  # Arnold — sério
    "ana_costa":        os.getenv("VOICE_ANA",      "ThT5KcBeYPX3keUQqHPh"),  # Dorothy — calorosa
    "carla_santos":     os.getenv("VOICE_CARLA",    "AZnzlk1XvdvUeBnXmlld"),  # Domi — profissional
    "rafael_torres":    os.getenv("VOICE_RAFAEL",   "CYw3kZ02Hs0563khs1Fj"),  # Dave — jovial
    "dani_ferreira":    os.getenv("VOICE_DANI",     "D38z5RcWu1voky8WS1ja"),  # Fin — analítico
    "ze_carvalho":      os.getenv("VOICE_ZE",       "IKne3meq5aSn9XLyUdCD"),  # Charlie — calmo
    "beto_rocha":       os.getenv("VOICE_BETO",     "TX3LPaxmHKxFdv7VOQHJ"),  # Liam — rápido
}

CONFIGS_VOZ = {
    "lucas_mendes":     {"stability": 0.75, "similarity_boost": 0.75, "style": 0.20},
    "mariana_oliveira": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.60},
    "pedro_lima":       {"stability": 0.90, "similarity_boost": 0.70, "style": 0.05},
    "ana_costa":        {"stability": 0.65, "similarity_boost": 0.80, "style": 0.40},
    "dani_ferreira":    {"stability": 0.80, "similarity_boost": 0.75, "style": 0.15},
}
CONFIG_DEFAULT = {"stability": 0.70, "similarity_boost": 0.75, "style": 0.25}


class ElevenLabsConnector:
    BASE = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.key = os.getenv("ELEVENLABS_API_KEY")
        self.headers = {"xi-api-key": self.key} if self.key else {}
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        if self.key:
            logger.info("✅ ElevenLabs conectado.")
        else:
            logger.warning("ElevenLabs não configurado — modo simulação.")

    def falar(
        self,
        agente_id: str,
        texto: str,
        salvar_como: Optional[str] = None,
        modelo: str = "eleven_multilingual_v2",
    ) -> dict:
        """
        Converte texto em voz com a personalidade do agente.
        Salva MP3 em nucleo/logs/audios/ e retorna o caminho.
        """
        voice_id = VOZES_AGENTES.get(agente_id, VOZES_AGENTES["lucas_mendes"])
        config   = CONFIGS_VOZ.get(agente_id, CONFIG_DEFAULT)

        nome_arquivo = salvar_como or f"{agente_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        caminho = AUDIO_DIR / nome_arquivo

        if not self.key:
            logger.info(f"[SIMULAÇÃO] ElevenLabs: {agente_id} diria → '{texto[:60]}'")
            return {"simulado": True, "texto": texto, "agente": agente_id, "arquivo": str(caminho)}

        try:
            r = httpx.post(
                f"{self.BASE}/text-to-speech/{voice_id}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={
                    "text": texto,
                    "model_id": modelo,
                    "voice_settings": config,
                },
                timeout=30,
            )
            if r.status_code == 200:
                caminho.write_bytes(r.content)
                logger.info(f"✅ Áudio gerado: {caminho} ({len(r.content)//1024}KB)")
                return {
                    "sucesso": True,
                    "arquivo": str(caminho),
                    "tamanho_kb": len(r.content) // 1024,
                    "agente": agente_id,
                    "duracao_estimada_seg": len(texto.split()) / 2.5,  # ~150 WPM
                }
            else:
                return {"erro": r.text, "status": r.status_code}
        except Exception as e:
            logger.error(f"ElevenLabs erro: {e}")
            return {"erro": str(e)}

    def ata_reuniao_audio(self, ata_texto: str) -> dict:
        """
        Gera áudio da ata da reunião semanal narrada pelo Lucas (CEO).
        Quebra o texto em partes se muito longo.
        """
        # ElevenLabs tem limite de ~5000 chars por request
        max_chars = 4500
        if len(ata_texto) <= max_chars:
            return self.falar("lucas_mendes", ata_texto, "ata_reuniao_semanal.mp3")

        # Quebra em partes
        partes = [ata_texto[i:i+max_chars] for i in range(0, len(ata_texto), max_chars)]
        arquivos = []
        for i, parte in enumerate(partes):
            r = self.falar("lucas_mendes", parte, f"ata_parte_{i+1}.mp3")
            arquivos.append(r.get("arquivo", ""))

        return {"partes": len(partes), "arquivos": arquivos}

    def notificacao_voz(self, agente_id: str, mensagem: str) -> dict:
        """Gera áudio de notificação rápida de um agente."""
        return self.falar(agente_id, mensagem, f"notif_{agente_id}_{datetime.now().strftime('%H%M')}.mp3")

    def listar_vozes(self) -> list[dict]:
        """Lista vozes disponíveis na conta."""
        if not self.key:
            return []
        try:
            r = httpx.get(f"{self.BASE}/voices", headers=self.headers)
            return [{"id": v["voice_id"], "nome": v["name"]} for v in r.json().get("voices", [])]
        except:
            return []


# Singletons
mercadolivre = MercadoLivreConnector()
clicksign    = ClickSignConnector()
elevenlabs   = ElevenLabsConnector()

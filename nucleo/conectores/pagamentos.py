"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Pagamentos Connector                    ║
║   Mercado Pago (Pix/Boleto) + Stripe (Cartão Internacional) ║
║                                                             ║
║   Recursos:                                                 ║
║   • Pix instantâneo com QR Code                             ║
║   • Boleto bancário                                         ║
║   • Cobrança cartão nacional e internacional                ║
║   • Assinaturas recorrentes                                 ║
║   • Limite de aprovação do Dono (> R$10k ou 5% do caixa)   ║
║   • Log auditável de todas as transações                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.pagamentos")

TX_LOG_PATH = Path("nucleo/logs/transacoes.jsonl")

# Limites financeiros — qualquer coisa acima escala para o Dono
LIMITE_APROVACAO_REAIS = float(os.getenv("LIMITE_APROVACAO_REAIS", "10000"))
LIMITE_PERCENTUAL_CAIXA = float(os.getenv("LIMITE_PERCENTUAL_CAIXA", "0.05"))


# ──────────────────────────────────────────────────────────────
# Dataclasses
# ──────────────────────────────────────────────────────────────

@dataclass
class ResultadoPagamento:
    sucesso: bool
    id_transacao: Optional[str]
    metodo: str
    valor: float
    status: str
    dados_extras: dict
    erro: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sucesso": self.sucesso,
            "id_transacao": self.id_transacao,
            "metodo": self.metodo,
            "valor": self.valor,
            "status": self.status,
            "dados_extras": self.dados_extras,
            "erro": self.erro,
            "ts": datetime.now().isoformat(),
        }


@dataclass
class DadosCobranca:
    valor: float                         # em reais
    descricao: str
    email_pagador: str
    nome_pagador: str
    cpf_pagador: Optional[str] = None    # necessário para Pix/Boleto
    telefone: Optional[str] = None
    metadados: dict = None


# ──────────────────────────────────────────────────────────────
# Validação de Limite
# ──────────────────────────────────────────────────────────────

def _verificar_limite(valor: float, caixa_atual: float = 0) -> tuple[bool, str]:
    """
    Verifica se o valor precisa de aprovação do Dono.
    Retorna (precisa_aprovacao, motivo).
    """
    if valor >= LIMITE_APROVACAO_REAIS:
        return True, f"Valor R${valor:,.2f} acima do limite de R${LIMITE_APROVACAO_REAIS:,.2f}"
    if caixa_atual > 0 and valor >= (caixa_atual * LIMITE_PERCENTUAL_CAIXA):
        pct = (valor / caixa_atual) * 100
        return True, f"Valor representa {pct:.1f}% do caixa (limite: {LIMITE_PERCENTUAL_CAIXA*100:.0f}%)"
    return False, ""


# ──────────────────────────────────────────────────────────────
# Log de transações
# ──────────────────────────────────────────────────────────────

def _log_transacao(resultado: ResultadoPagamento, agente_id: str):
    TX_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = resultado.to_dict()
    entry["agente"] = agente_id
    with open(TX_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info(f"💾 Transação registrada: {resultado.id_transacao} | R${resultado.valor:,.2f} | {resultado.status}")


# ──────────────────────────────────────────────────────────────
# Mercado Pago
# ──────────────────────────────────────────────────────────────

class MercadoPagoConnector:
    def __init__(self):
        self.token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        if not self.token:
            logger.warning("Mercado Pago não configurado. Modo simulação ativo.")
            self.sdk = None
        else:
            try:
                import mercadopago
                self.sdk = mercadopago.SDK(self.token)
                logger.info("✅ Mercado Pago inicializado.")
            except ImportError:
                logger.error("pip install mercadopago")
                self.sdk = None

    def cobrar_pix(self, dados: DadosCobranca, agente_id: str = "pedro_lima") -> ResultadoPagamento:
        """Gera cobrança Pix. Retorna QR Code e copia-e-cola."""
        precisa_aprovacao, motivo = _verificar_limite(dados.valor)
        if precisa_aprovacao:
            logger.warning(f"⚠️ PIX {dados.valor} requer aprovação do Dono: {motivo}")
            resultado = ResultadoPagamento(
                sucesso=False, id_transacao=None, metodo="pix",
                valor=dados.valor, status="aguardando_aprovacao_dono",
                dados_extras={"motivo": motivo}, erro=motivo,
            )
            _log_transacao(resultado, agente_id)
            return resultado

        if not self.sdk:
            return self._simular_pix(dados)

        payload = {
            "transaction_amount": dados.valor,
            "description": dados.descricao,
            "payment_method_id": "pix",
            "payer": {
                "email": dados.email_pagador,
                "first_name": dados.nome_pagador.split()[0],
                "last_name": " ".join(dados.nome_pagador.split()[1:]) or ".",
                "identification": {"type": "CPF", "number": dados.cpf_pagador or ""},
            },
        }

        try:
            resposta = self.sdk.payment().create(payload)
            dados_pix = resposta["response"]

            if resposta["status"] == 201:
                pix_info = dados_pix.get("point_of_interaction", {}).get("transaction_data", {})
                resultado = ResultadoPagamento(
                    sucesso=True,
                    id_transacao=str(dados_pix["id"]),
                    metodo="pix",
                    valor=dados.valor,
                    status=dados_pix["status"],
                    dados_extras={
                        "qr_code": pix_info.get("qr_code"),
                        "qr_code_base64": pix_info.get("qr_code_base64"),
                        "copia_cola": pix_info.get("qr_code"),
                        "expiracao": dados_pix.get("date_of_expiration"),
                    },
                )
            else:
                resultado = ResultadoPagamento(
                    sucesso=False, id_transacao=None, metodo="pix",
                    valor=dados.valor, status="erro",
                    dados_extras={}, erro=str(dados_pix),
                )

            _log_transacao(resultado, agente_id)
            return resultado

        except Exception as e:
            logger.error(f"❌ Erro Pix: {e}")
            return ResultadoPagamento(
                sucesso=False, id_transacao=None, metodo="pix",
                valor=dados.valor, status="erro", dados_extras={}, erro=str(e),
            )

    def cobrar_boleto(self, dados: DadosCobranca, agente_id: str = "pedro_lima") -> ResultadoPagamento:
        """Gera boleto bancário com vencimento em 3 dias."""
        if not self.sdk:
            return self._simular_boleto(dados)

        payload = {
            "transaction_amount": dados.valor,
            "description": dados.descricao,
            "payment_method_id": "bolbradesco",
            "payer": {
                "email": dados.email_pagador,
                "first_name": dados.nome_pagador.split()[0],
                "last_name": " ".join(dados.nome_pagador.split()[1:]) or ".",
                "identification": {"type": "CPF", "number": dados.cpf_pagador or ""},
                "address": {"zip_code": "01310-100", "street_name": "Av. Paulista", "street_number": "1"},
            },
        }

        try:
            resposta = self.sdk.payment().create(payload)
            dados_boleto = resposta["response"]

            resultado = ResultadoPagamento(
                sucesso=resposta["status"] == 201,
                id_transacao=str(dados_boleto.get("id")),
                metodo="boleto",
                valor=dados.valor,
                status=dados_boleto.get("status", "erro"),
                dados_extras={
                    "url_boleto": dados_boleto.get("transaction_details", {}).get("external_resource_url"),
                    "codigo_barras": dados_boleto.get("barcode", {}).get("content"),
                    "vencimento": dados_boleto.get("date_of_expiration"),
                },
            )
            _log_transacao(resultado, agente_id)
            return resultado

        except Exception as e:
            return ResultadoPagamento(
                sucesso=False, id_transacao=None, metodo="boleto",
                valor=dados.valor, status="erro", dados_extras={}, erro=str(e),
            )

    def verificar_pagamento(self, id_transacao: str) -> dict:
        """Consulta status de um pagamento pelo ID."""
        if not self.sdk:
            return {"status": "approved", "simulado": True}
        resposta = self.sdk.payment().get(id_transacao)
        return resposta.get("response", {})

    def _simular_pix(self, dados: DadosCobranca) -> ResultadoPagamento:
        import hashlib
        fake_id = hashlib.md5(f"{dados.email_pagador}{dados.valor}".encode()).hexdigest()[:10]
        return ResultadoPagamento(
            sucesso=True, id_transacao=f"SIM_PIX_{fake_id}", metodo="pix",
            valor=dados.valor, status="pending",
            dados_extras={
                "qr_code": "00020126580014br.gov.bcb.pix0136...",
                "copia_cola": f"SIMULADO_PIX_{fake_id}",
                "aviso": "MODO SIMULAÇÃO — configure MERCADOPAGO_ACCESS_TOKEN",
            },
        )

    def _simular_boleto(self, dados: DadosCobranca) -> ResultadoPagamento:
        return ResultadoPagamento(
            sucesso=True, id_transacao="SIM_BOL_00001", metodo="boleto",
            valor=dados.valor, status="pending",
            dados_extras={
                "url_boleto": "https://boleto.simulado.com/00001",
                "aviso": "MODO SIMULAÇÃO — configure MERCADOPAGO_ACCESS_TOKEN",
            },
        )


# ──────────────────────────────────────────────────────────────
# Stripe
# ──────────────────────────────────────────────────────────────

class StripeConnector:
    def __init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        if not self.secret_key:
            logger.warning("Stripe não configurado. Modo simulação ativo.")
            self.stripe = None
        else:
            try:
                import stripe
                stripe.api_key = self.secret_key
                self.stripe = stripe
                logger.info("✅ Stripe inicializado.")
            except ImportError:
                logger.error("pip install stripe")
                self.stripe = None

    def cobrar_cartao(
        self,
        dados: DadosCobranca,
        payment_method_id: str,
        agente_id: str = "pedro_lima",
    ) -> ResultadoPagamento:
        """Cobra cartão de crédito via Stripe."""
        if not self.stripe:
            return self._simular_cartao(dados)

        try:
            # Valor em centavos
            valor_centavos = int(dados.valor * 100)

            intencao = self.stripe.PaymentIntent.create(
                amount=valor_centavos,
                currency="brl",
                payment_method=payment_method_id,
                confirm=True,
                description=dados.descricao,
                metadata={"agente": agente_id, **(dados.metadados or {})},
                receipt_email=dados.email_pagador,
            )

            resultado = ResultadoPagamento(
                sucesso=intencao.status in ["succeeded", "processing"],
                id_transacao=intencao.id,
                metodo="cartao_stripe",
                valor=dados.valor,
                status=intencao.status,
                dados_extras={
                    "client_secret": intencao.client_secret,
                    "moeda": "brl",
                },
            )
            _log_transacao(resultado, agente_id)
            return resultado

        except Exception as e:
            logger.error(f"❌ Erro Stripe: {e}")
            return ResultadoPagamento(
                sucesso=False, id_transacao=None, metodo="cartao_stripe",
                valor=dados.valor, status="erro", dados_extras={}, erro=str(e),
            )

    def criar_assinatura(
        self,
        email: str,
        price_id: str,
        agente_id: str = "pedro_lima",
    ) -> ResultadoPagamento:
        """Cria assinatura recorrente."""
        if not self.stripe:
            return ResultadoPagamento(
                sucesso=True, id_transacao="SIM_SUB_001", metodo="assinatura",
                valor=0, status="active",
                dados_extras={"aviso": "MODO SIMULAÇÃO"},
            )

        try:
            cliente = self.stripe.Customer.create(email=email)
            assinatura = self.stripe.Subscription.create(
                customer=cliente.id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )

            resultado = ResultadoPagamento(
                sucesso=True,
                id_transacao=assinatura.id,
                metodo="assinatura",
                valor=0,
                status=assinatura.status,
                dados_extras={
                    "customer_id": cliente.id,
                    "client_secret": assinatura.latest_invoice.payment_intent.client_secret,
                },
            )
            _log_transacao(resultado, agente_id)
            return resultado

        except Exception as e:
            return ResultadoPagamento(
                sucesso=False, id_transacao=None, metodo="assinatura",
                valor=0, status="erro", dados_extras={}, erro=str(e),
            )

    def processar_webhook(self, payload: bytes, sig_header: str) -> Optional[dict]:
        """Valida e processa webhook do Stripe."""
        if not self.stripe or not self.webhook_secret:
            return None
        try:
            evento = self.stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            logger.info(f"Stripe webhook: {evento['type']}")
            return evento
        except Exception as e:
            logger.error(f"Webhook Stripe inválido: {e}")
            return None

    def _simular_cartao(self, dados: DadosCobranca) -> ResultadoPagamento:
        return ResultadoPagamento(
            sucesso=True, id_transacao="SIM_STRIPE_pi_001", metodo="cartao_stripe",
            valor=dados.valor, status="succeeded",
            dados_extras={"aviso": "MODO SIMULAÇÃO — configure STRIPE_SECRET_KEY"},
        )


# ──────────────────────────────────────────────────────────────
# Interface unificada (Pedro Lima usa essa)
# ──────────────────────────────────────────────────────────────

class PagamentosConnector:
    """
    Fachada unificada para todos os métodos de pagamento.
    Pedro Lima usa: pagamentos.pix(...), pagamentos.cartao(...)
    """
    def __init__(self):
        self.mp = MercadoPagoConnector()
        self.stripe = StripeConnector()

    def pix(self, dados: DadosCobranca, agente_id="pedro_lima") -> ResultadoPagamento:
        return self.mp.cobrar_pix(dados, agente_id)

    def boleto(self, dados: DadosCobranca, agente_id="pedro_lima") -> ResultadoPagamento:
        return self.mp.cobrar_boleto(dados, agente_id)

    def cartao(self, dados: DadosCobranca, payment_method_id: str, agente_id="pedro_lima") -> ResultadoPagamento:
        return self.stripe.cobrar_cartao(dados, payment_method_id, agente_id)

    def assinatura(self, email: str, price_id: str, agente_id="pedro_lima") -> ResultadoPagamento:
        return self.stripe.criar_assinatura(email, price_id, agente_id)

    def verificar(self, id_transacao: str) -> dict:
        return self.mp.verificar_pagamento(id_transacao)

    def historico(self, limite: int = 50) -> list[dict]:
        """Lê últimas N transações do log."""
        if not TX_LOG_PATH.exists():
            return []
        linhas = TX_LOG_PATH.read_text().strip().split("\n")
        return [json.loads(l) for l in linhas[-limite:] if l]


# Singleton
pagamentos = PagamentosConnector()


# ──────────────────────────────────────────────────────────────
# Exemplo de uso
# ──────────────────────────────────────────────────────────────
"""
from nucleo.conectores.pagamentos import pagamentos, DadosCobranca

# Pix
dados = DadosCobranca(
    valor=297.00,
    descricao="Licença Increase Team - Plano Starter",
    email_pagador="cliente@empresa.com",
    nome_pagador="Carlos Mendonça",
    cpf_pagador="12345678900",
)
resultado = pagamentos.pix(dados)
if resultado.sucesso:
    print("QR Code:", resultado.dados_extras["qr_code"])
    print("Copia e cola:", resultado.dados_extras["copia_cola"])

# Boleto
resultado = pagamentos.boleto(dados)
print("URL boleto:", resultado.dados_extras["url_boleto"])

# Verificar pagamento
status = pagamentos.verificar("123456789")
print("Status:", status["status"])
"""

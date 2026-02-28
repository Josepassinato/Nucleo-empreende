"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Hotmart Connector                       ║
║                                                             ║
║   Recursos:                                                 ║
║   • Vendas: listar, filtrar, detalhar                       ║
║   • Assinaturas: status, cancelamentos, reativações         ║
║   • Afiliados: listar, comissões, performance               ║
║   • Cupons: criar, listar, desativar                        ║
║   • Webhooks: receber e processar eventos em tempo real     ║
║   • Relatórios: faturamento, churn, LTV, ticket médio       ║
║   • Abandono de carrinho: leads não convertidos             ║
╚══════════════════════════════════════════════════════════════╝

Uso rápido:
    from nucleo.conectores.hotmart import hotmart

    # Relatório do mês
    print(hotmart.relatorio_mensal())

    # Processar webhook de compra aprovada
    dados = hotmart.processar_webhook(payload, token_hotmart)
    if dados["evento"] == "PURCHASE_APPROVED":
        # dispara onboarding, contrato, WhatsApp...
"""

import os, json, logging, hashlib, hmac
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.hotmart")

# ──────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────

BASE_SANDBOX    = "https://sandbox.hotmart.com"
BASE_PRODUCAO   = "https://developers.hotmart.com"
BASE_AUTH       = "https://api-sec-vlc.hotmart.com"

AMBIENTE = os.getenv("HOTMART_AMBIENTE", "sandbox")  # "sandbox" | "producao"
BASE_URL = BASE_PRODUCAO if AMBIENTE == "producao" else BASE_SANDBOX

# ──────────────────────────────────────────────────────────────
# Dataclasses
# ──────────────────────────────────────────────────────────────

@dataclass
class VendaHotmart:
    id: str
    status: str                    # APPROVED | CANCELLED | REFUNDED | CHARGEBACK
    produto: str
    comprador_nome: str
    comprador_email: str
    valor: float
    comissao_produtor: float
    data: str
    forma_pagamento: str
    parcelas: int = 1
    assinatura_id: Optional[str] = None
    afiliado_email: Optional[str] = None

@dataclass
class RelatorioHotmart:
    periodo: str
    faturamento_bruto: float
    faturamento_liquido: float
    total_vendas: int
    vendas_aprovadas: int
    cancelamentos: int
    reembolsos: int
    churn_rate: float
    ticket_medio: float
    novos_assinantes: int
    assinantes_ativos: int
    top_produtos: list = field(default_factory=list)
    top_afiliados: list = field(default_factory=list)

# ──────────────────────────────────────────────────────────────
# Autenticação OAuth 2.0
# ──────────────────────────────────────────────────────────────

class HotmartAuth:
    def __init__(self):
        self.client_id     = os.getenv("HOTMART_CLIENT_ID")
        self.client_secret = os.getenv("HOTMART_CLIENT_SECRET")
        self.basic_token   = os.getenv("HOTMART_BASIC_TOKEN")
        self._access_token: Optional[str] = None
        self._expira_em: Optional[datetime] = None

    def token(self) -> Optional[str]:
        """Retorna access token válido, renovando se necessário."""
        if self._access_token and self._expira_em and datetime.now() < self._expira_em:
            return self._access_token
        return self._renovar_token()

    def _renovar_token(self) -> Optional[str]:
        if not (self.client_id and self.client_secret and self.basic_token):
            logger.warning("Hotmart: credenciais OAuth não configuradas.")
            return None
        try:
            r = httpx.post(
                f"{BASE_AUTH}/security/oauth/token",
                headers={
                    "Authorization": f"Basic {self.basic_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=15,
            )
            data = r.json()
            if "access_token" in data:
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self._expira_em = datetime.now() + timedelta(seconds=expires_in - 60)
                logger.info("✅ Hotmart token renovado.")
                return self._access_token
            else:
                logger.error(f"Hotmart auth erro: {data}")
                return None
        except Exception as e:
            logger.error(f"Hotmart auth exceção: {e}")
            return None

# ──────────────────────────────────────────────────────────────
# Conector principal
# ──────────────────────────────────────────────────────────────

class HotmartConnector:
    def __init__(self):
        self.auth = HotmartAuth()
        self.webhook_token = os.getenv("HOTMART_WEBHOOK_TOKEN")
        self.produto_id    = os.getenv("HOTMART_PRODUTO_ID")

        token = self.auth.token()
        if token:
            logger.info(f"✅ Hotmart conectado ({AMBIENTE}).")
        else:
            logger.warning("Hotmart não configurado — modo simulação.")

    # ── Headers ───────────────────────────────────────────────

    def _headers(self) -> dict:
        token = self.auth.token()
        if not token:
            return {}
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── HTTP helpers ──────────────────────────────────────────

    def _get(self, path: str, params: dict = {}) -> dict:
        headers = self._headers()
        if not headers:
            return self._simular_get(path)
        try:
            r = httpx.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            logger.warning(f"Hotmart GET {path}: {r.status_code} — {r.text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Hotmart GET exceção: {e}")
            return {}

    def _post(self, path: str, body: dict) -> dict:
        headers = self._headers()
        if not headers:
            fake = hashlib.md5(str(body).encode()).hexdigest()[:8]
            logger.info(f"[SIMULAÇÃO] Hotmart POST {path}")
            return {"id": f"SIM_{fake}", "simulado": True}
        try:
            r = httpx.post(f"{BASE_URL}{path}", headers=headers, json=body, timeout=20)
            return r.json()
        except Exception as e:
            return {"erro": str(e)}

    # ── VENDAS ────────────────────────────────────────────────

    def listar_vendas(
        self,
        status: Optional[str] = None,    # APPROVED | CANCELLED | REFUNDED
        dias: int = 30,
        max_resultados: int = 50,
    ) -> list[VendaHotmart]:
        """Lista vendas recentes com filtros opcionais."""
        inicio_ms = int((datetime.now() - timedelta(days=dias)).timestamp() * 1000)
        fim_ms    = int(datetime.now().timestamp() * 1000)

        params = {
            "start_date": inicio_ms,
            "end_date":   fim_ms,
            "max_results": max_resultados,
        }
        if status:
            params["transaction_status"] = status

        dados = self._get("/payments/api/v1/sales/history", params)

        if dados.get("simulado") or not dados:
            return self._simular_vendas(dias)

        items = dados.get("items", [])
        return [self._mapear_venda(i) for i in items]

    def detalhe_venda(self, codigo_transacao: str) -> Optional[VendaHotmart]:
        dados = self._get("/payments/api/v1/sales/history", {
            "transaction": codigo_transacao
        })
        items = dados.get("items", [])
        return self._mapear_venda(items[0]) if items else None

    def _mapear_venda(self, item: dict) -> VendaHotmart:
        prod  = item.get("product", {})
        comp  = item.get("buyer", {})
        pag   = item.get("payment", {})
        comis = item.get("commissions", {})

        return VendaHotmart(
            id=item.get("transaction", ""),
            status=item.get("transaction_status", ""),
            produto=prod.get("name", ""),
            comprador_nome=comp.get("name", ""),
            comprador_email=comp.get("email", ""),
            valor=float(pag.get("value", {}).get("value", 0)),
            comissao_produtor=float(comis.get("producer", {}).get("value", 0)),
            data=item.get("order_date", ""),
            forma_pagamento=pag.get("type", ""),
            parcelas=int(pag.get("installments_number", 1)),
            afiliado_email=item.get("affiliate", {}).get("user_email"),
        )

    # ── ASSINATURAS ───────────────────────────────────────────

    def listar_assinaturas(
        self,
        status: Optional[str] = None,   # ACTIVE | INACTIVE | CANCELLED | DELAYED
        produto_id: Optional[str] = None,
    ) -> list[dict]:
        """Lista todas as assinaturas ativas/canceladas."""
        params = {}
        if status:
            params["status"] = status
        if produto_id or self.produto_id:
            params["product_id"] = produto_id or self.produto_id

        dados = self._get("/payments/api/v1/subscriptions", params)
        if not dados or dados.get("simulado"):
            return self._simular_assinaturas()
        return dados.get("items", [])

    def cancelar_assinatura(self, subscriber_code: str) -> bool:
        """Cancela uma assinatura pelo código do assinante."""
        r = self._post(f"/payments/api/v1/subscriptions/{subscriber_code}/cancel", {})
        ok = r.get("subscription_status") == "CANCELLED" or r.get("simulado")
        if ok:
            logger.info(f"Assinatura {subscriber_code} cancelada.")
        return ok

    def reativar_assinatura(self, subscriber_code: str) -> bool:
        """Reativa uma assinatura cancelada."""
        r = self._post(f"/payments/api/v1/subscriptions/{subscriber_code}/reactivate", {})
        return r.get("simulado") or "erro" not in r

    def assinantes_ativos(self) -> int:
        subs = self.listar_assinaturas(status="ACTIVE")
        return len(subs)

    # ── AFILIADOS ─────────────────────────────────────────────

    def listar_afiliados(self, produto_id: Optional[str] = None) -> list[dict]:
        """Lista todos os afiliados e suas comissões."""
        pid = produto_id or self.produto_id
        params = {"product_id": pid} if pid else {}
        dados = self._get("/products/api/v1/affiliates", params)
        if not dados or dados.get("simulado"):
            return [
                {"nome": "Afiliado Top 1", "email": "af1@email.com", "vendas": 32, "comissao": 4480.0},
                {"nome": "Afiliado Top 2", "email": "af2@email.com", "vendas": 18, "comissao": 2520.0},
            ]
        return dados.get("items", [])

    def comissoes_afiliado(self, afiliado_email: str, dias: int = 30) -> dict:
        """Resumo de comissões de um afiliado específico."""
        vendas = self.listar_vendas(status="APPROVED", dias=dias)
        vendas_afiliado = [v for v in vendas if v.afiliado_email == afiliado_email]
        total = sum(v.comissao_produtor for v in vendas_afiliado)
        return {
            "afiliado": afiliado_email,
            "vendas": len(vendas_afiliado),
            "comissao_total": total,
            "ticket_medio": total / max(len(vendas_afiliado), 1),
        }

    # ── CUPONS ────────────────────────────────────────────────

    def criar_cupom(
        self,
        codigo: str,
        desconto_pct: float,
        produto_id: Optional[str] = None,
        usos_max: int = 100,
        validade_dias: int = 30,
    ) -> dict:
        """Cria cupom de desconto."""
        pid = produto_id or self.produto_id
        expira = (datetime.now() + timedelta(days=validade_dias)).strftime("%Y-%m-%d")
        return self._post("/products/api/v1/coupons", {
            "code": codigo.upper(),
            "discount": desconto_pct,
            "product_id": pid,
            "max_uses": usos_max,
            "expiration_date": expira,
        })

    def listar_cupons(self, produto_id: Optional[str] = None) -> list[dict]:
        pid = produto_id or self.produto_id
        dados = self._get("/products/api/v1/coupons", {"product_id": pid} if pid else {})
        return dados.get("items", [])

    # ── ABANDONO DE CARRINHO ──────────────────────────────────

    def carrinhos_abandonados(self, dias: int = 7) -> list[dict]:
        """Lista leads que iniciaram compra mas não concluíram."""
        inicio_ms = int((datetime.now() - timedelta(days=dias)).timestamp() * 1000)
        dados = self._get("/payments/api/v1/sales/history", {
            "transaction_status": "INCOMPLETE",
            "start_date": inicio_ms,
        })
        if dados.get("simulado") or not dados:
            return [
                {"nome": "Lead 1", "email": "lead1@email.com", "produto": "Nucleo Empreende", "data": datetime.now().strftime("%Y-%m-%d")},
                {"nome": "Lead 2", "email": "lead2@email.com", "produto": "Nucleo Empreende", "data": datetime.now().strftime("%Y-%m-%d")},
            ]
        return dados.get("items", [])

    # ── WEBHOOKS ──────────────────────────────────────────────

    def verificar_webhook(self, payload_raw: bytes, assinatura_recebida: str) -> bool:
        """
        Valida que o webhook veio realmente do Hotmart.
        Use no endpoint: @app.post("/webhook/hotmart")
        """
        if not self.webhook_token:
            logger.warning("HOTMART_WEBHOOK_TOKEN não configurado — validação pulada.")
            return True
        esperada = hmac.new(
            self.webhook_token.encode(),
            payload_raw,
            hashlib.sha1,
        ).hexdigest()
        return hmac.compare_digest(esperada, assinatura_recebida)

    def processar_webhook(self, payload: dict) -> dict:
        """
        Interpreta o payload do webhook e retorna dict estruturado.

        Eventos possíveis:
          PURCHASE_APPROVED        → venda aprovada
          PURCHASE_CANCELLED       → venda cancelada
          PURCHASE_REFUNDED        → reembolso
          PURCHASE_CHARGEBACK      → chargeback
          SUBSCRIPTION_CANCELLATION → assinatura cancelada
          PURCHASE_PROTEST         → protesto
          PURCHASE_DELAYED         → boleto ainda não pago

        Retorna dict com "evento", "venda", "acao_sugerida".
        """
        evento = payload.get("event", "DESCONHECIDO")
        dados_venda = payload.get("data", {})
        comprador = dados_venda.get("buyer", {})
        produto   = dados_venda.get("product", {})
        pag       = dados_venda.get("payment", {})

        venda = {
            "transaction":  dados_venda.get("purchase", {}).get("transaction", ""),
            "status":       dados_venda.get("purchase", {}).get("status", ""),
            "comprador_nome":  comprador.get("name", ""),
            "comprador_email": comprador.get("email", ""),
            "produto_nome":    produto.get("name", ""),
            "valor":    float(pag.get("value", {}).get("value", 0) if isinstance(pag.get("value"), dict) else pag.get("value", 0)),
            "parcelas": pag.get("installments_number", 1),
            "forma_pag": pag.get("type", ""),
        }

        # Ação sugerida para cada evento
        acoes = {
            "PURCHASE_APPROVED":         "✅ Disparar onboarding: WhatsApp + Email + Contrato ClickSign",
            "PURCHASE_CANCELLED":        "❌ Notificar Pedro Lima → investigar motivo",
            "PURCHASE_REFUNDED":         "💸 Registrar reembolso + notificar CFO",
            "PURCHASE_CHARGEBACK":       "🚨 ALERTA CRÍTICO → escalar para Lucas + Pedro imediatamente",
            "SUBSCRIPTION_CANCELLATION": "📉 Registrar churn → Zé Carvalho acionar retenção",
            "PURCHASE_DELAYED":          "⏳ Boleto pendente → enviar lembrete em 24h",
            "PURCHASE_PROTEST":          "⚠️ Protesto registrado → Pedro Lima avaliar",
        }

        resultado = {
            "evento":         evento,
            "venda":          venda,
            "acao_sugerida":  acoes.get(evento, f"Evento {evento} — verificar manualmente"),
            "ts":             datetime.now().isoformat(),
        }

        logger.info(f"Hotmart webhook: {evento} | {venda['comprador_email']} | R${venda['valor']:.2f}")
        self._log_evento(resultado)
        return resultado

    def _log_evento(self, dados: dict):
        log_path = Path("nucleo/logs/hotmart_eventos.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(dados, ensure_ascii=False) + "\n")

    # ── RELATÓRIOS ────────────────────────────────────────────

    def relatorio_mensal(self, mes_offset: int = 0) -> RelatorioHotmart:
        """
        Gera relatório completo do mês.
        mes_offset=0 → mês atual, mes_offset=1 → mês passado.
        """
        hoje = datetime.now()
        primeiro_dia = (hoje.replace(day=1) - timedelta(days=30 * mes_offset)).replace(day=1)
        ultimo_dia   = (primeiro_dia + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        dias = (ultimo_dia - primeiro_dia).days + 1
        periodo = primeiro_dia.strftime("%B/%Y")

        vendas = self.listar_vendas(dias=dias + 5)  # margem

        aprovadas    = [v for v in vendas if v.status == "APPROVED"]
        canceladas   = [v for v in vendas if v.status == "CANCELLED"]
        reembolsadas = [v for v in vendas if v.status == "REFUNDED"]

        fat_bruto   = sum(v.valor for v in aprovadas)
        fat_liquido = fat_bruto * 0.88  # aproximação (taxas Hotmart ~12%)

        total_vendas = len(vendas)
        ticket_medio = fat_bruto / max(len(aprovadas), 1)
        churn = len(canceladas) / max(total_vendas, 1) * 100

        # Top produtos
        produtos: dict = {}
        for v in aprovadas:
            produtos[v.produto] = produtos.get(v.produto, 0) + v.valor
        top_prods = sorted(produtos.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top afiliados
        afiliados: dict = {}
        for v in aprovadas:
            if v.afiliado_email:
                afiliados[v.afiliado_email] = afiliados.get(v.afiliado_email, 0) + v.valor
        top_afils = sorted(afiliados.items(), key=lambda x: x[1], reverse=True)[:5]

        return RelatorioHotmart(
            periodo=periodo,
            faturamento_bruto=fat_bruto,
            faturamento_liquido=fat_liquido,
            total_vendas=total_vendas,
            vendas_aprovadas=len(aprovadas),
            cancelamentos=len(canceladas),
            reembolsos=len(reembolsadas),
            churn_rate=round(churn, 2),
            ticket_medio=round(ticket_medio, 2),
            novos_assinantes=len(aprovadas),
            assinantes_ativos=self.assinantes_ativos(),
            top_produtos=top_prods,
            top_afiliados=top_afils,
        )

    def relatorio_texto(self, mes_offset: int = 0) -> str:
        """
        Versão texto do relatório — Pedro Lima apresenta na reunião.
        """
        r = self.relatorio_mensal(mes_offset)
        linhas = [
            f"🛒 HOTMART — {r.periodo.upper()}",
            f"",
            f"💰 Faturamento bruto:   R$ {r.faturamento_bruto:>10,.2f}",
            f"💵 Faturamento líquido: R$ {r.faturamento_liquido:>10,.2f}",
            f"",
            f"📦 Total transações:    {r.total_vendas:>6}",
            f"✅ Aprovadas:           {r.vendas_aprovadas:>6}",
            f"❌ Cancelamentos:       {r.cancelamentos:>6}",
            f"💸 Reembolsos:          {r.reembolsos:>6}",
            f"📉 Churn rate:          {r.churn_rate:>5.1f}%",
            f"🎫 Ticket médio:        R$ {r.ticket_medio:>8,.2f}",
            f"",
            f"👥 Assinantes ativos:   {r.assinantes_ativos:>6}",
        ]
        if r.top_produtos:
            linhas += ["", "🏆 Top produtos:"]
            for nome, valor in r.top_produtos[:3]:
                linhas.append(f"   • {nome[:30]:<30} R$ {valor:,.2f}")
        if r.top_afiliados:
            linhas += ["", "🤝 Top afiliados:"]
            for email, valor in r.top_afiliados[:3]:
                linhas.append(f"   • {email[:30]:<30} R$ {valor:,.2f}")
        return "\n".join(linhas)

    # ── SIMULAÇÕES ────────────────────────────────────────────

    def _simular_vendas(self, dias: int) -> list[VendaHotmart]:
        import random
        produtos = ["Nucleo Empreende Starter", "Nucleo Empreende Pro", "Nucleo Empreende Enterprise"]
        status_lista = ["APPROVED"] * 8 + ["CANCELLED"] + ["REFUNDED"]
        return [
            VendaHotmart(
                id=f"HP{1000+i}",
                status=random.choice(status_lista),
                produto=random.choice(produtos),
                comprador_nome=f"Cliente {i+1}",
                comprador_email=f"cliente{i+1}@empresa.com",
                valor=random.choice([297.0, 997.0, 2997.0, 4997.0]),
                comissao_produtor=0,
                data=(datetime.now() - timedelta(days=random.randint(0, dias))).strftime("%Y-%m-%d"),
                forma_pagamento=random.choice(["PIX", "CREDIT_CARD", "BOLETO"]),
                parcelas=random.choice([1, 3, 6, 12]),
                afiliado_email=f"af{random.randint(1,3)}@email.com" if random.random() > 0.5 else None,
            )
            for i in range(random.randint(18, 35))
        ]

    def _simular_get(self, path: str) -> dict:
        logger.info(f"[SIMULAÇÃO] Hotmart GET {path}")
        return {"simulado": True, "items": []}

    def _simular_assinaturas(self) -> list[dict]:
        return [
            {"subscriber_code": f"SUB_{i:04d}", "status": "ACTIVE",
             "email": f"assinante{i}@email.com", "produto": "Nucleo Empreende Pro"}
            for i in range(12)
        ]


# Singleton
hotmart = HotmartConnector()


# ──────────────────────────────────────────────────────────────
# Variáveis de ambiente necessárias (.env)
# ──────────────────────────────────────────────────────────────
"""
# ── Hotmart ───────────────────────────────────────────────────
HOTMART_CLIENT_ID=''          # Painel → Ferramentas → Credenciais API
HOTMART_CLIENT_SECRET=''
HOTMART_BASIC_TOKEN=''        # Base64(client_id:client_secret)
HOTMART_WEBHOOK_TOKEN=''      # Painel → Ferramentas → Webhooks → Chave secreta
HOTMART_PRODUTO_ID=''         # ID do seu produto principal
HOTMART_AMBIENTE='producao'   # 'sandbox' para testes
"""

# ──────────────────────────────────────────────────────────────
# Integração com FastAPI (webhook)
# ──────────────────────────────────────────────────────────────
"""
from fastapi import FastAPI, Request, Header, HTTPException
from nucleo.conectores.hotmart import hotmart
from nucleo.conectores.whatsapp import whatsapp
from nucleo.conectores.clicksign import clicksign
from nucleo.conectores.gmail import gmail

app = FastAPI()

@app.post("/webhook/hotmart")
async def webhook_hotmart(
    request: Request,
    x_hotmart_signature: str = Header(None),
):
    payload_raw = await request.body()

    # 1. Validar assinatura
    if not hotmart.verificar_webhook(payload_raw, x_hotmart_signature or ""):
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    payload = await request.json()
    evento = hotmart.processar_webhook(payload)

    # 2. Reagir ao evento
    if evento["evento"] == "PURCHASE_APPROVED":
        venda = evento["venda"]

        # WhatsApp de boas-vindas (Ana Costa)
        await whatsapp.enviar(
            "ana_costa", venda["comprador_email"],
            f"Olá {venda['comprador_nome'].split()[0]}! 🎉 "
            f"Seu acesso ao {venda['produto_nome']} foi aprovado. "
            "Vou te guiar nos próximos passos.",
            nome_destinatario=venda["comprador_nome"].split()[0],
        )

        # Contrato digital automático (Pedro Lima / ClickSign)
        clicksign.gerar_contrato_licenca(
            venda["comprador_nome"], venda["comprador_email"],
            "", "Pro", venda["valor"]
        )

    elif evento["evento"] == "PURCHASE_CHARGEBACK":
        # Alerta crítico para Pedro + Lucas
        from nucleo.conectores.telegram import telegram_bot
        await telegram_bot.alerta_dono(
            "🚨 CHARGEBACK DETECTADO",
            f"{evento['venda']['comprador_email']} — R$ {evento['venda']['valor']:.2f}",
            urgencia="alta",
        )

    return {"status": "ok", "evento": evento["evento"]}
"""

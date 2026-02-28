"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Meta Ads Connector                      ║
║   Facebook + Instagram: criar, monitorar e otimizar         ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, logging, httpx
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.meta_ads")

BASE_URL = "https://graph.facebook.com/v20.0"

@dataclass
class CampanhaMeta:
    nome: str
    objetivo: str          # OUTCOME_AWARENESS | OUTCOME_TRAFFIC | OUTCOME_LEADS | OUTCOME_SALES
    budget_diario: float   # em reais
    publico_alvo: dict
    criativos: list[dict]  # lista de imagens/textos
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None


class MetaAdsConnector:
    def __init__(self):
        self.token      = os.getenv("META_ACCESS_TOKEN")
        self.account_id = os.getenv("META_AD_ACCOUNT_ID")
        self.app_id     = os.getenv("META_APP_ID")
        self.pixel_id   = os.getenv("META_PIXEL_ID")

        if self.token and self.account_id:
            logger.info("✅ Meta Ads conectado.")
        else:
            logger.warning("Meta Ads não configurado — modo simulação.")

    def _get(self, endpoint: str, params: dict = {}) -> dict:
        if not self.token:
            return {"simulado": True, "data": []}
        params["access_token"] = self.token
        try:
            r = httpx.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
            return r.json()
        except Exception as e:
            logger.error(f"Meta GET erro: {e}")
            return {}

    def _post(self, endpoint: str, data: dict) -> dict:
        if not self.token:
            import hashlib
            fake_id = hashlib.md5(str(data).encode()).hexdigest()[:8]
            logger.info(f"[SIMULAÇÃO] Meta POST → {endpoint}")
            return {"id": f"SIM_{fake_id}", "simulado": True}
        data["access_token"] = self.token
        try:
            r = httpx.post(f"{BASE_URL}/{endpoint}", data=data, timeout=15)
            return r.json()
        except Exception as e:
            logger.error(f"Meta POST erro: {e}")
            return {}

    # ── Criar campanha completa ───────────────────────────────

    def criar_campanha(self, campanha: CampanhaMeta) -> dict:
        """Cria campanha, conjunto de anúncios e anúncio de uma vez."""
        # 1. Campanha
        c = self._post(f"act_{self.account_id}/campaigns", {
            "name": campanha.nome,
            "objective": campanha.objetivo,
            "status": "PAUSED",           # sempre começa pausada para revisão
            "special_ad_categories": "[]",
        })
        if "error" in c:
            return {"erro": c["error"], "etapa": "campanha"}

        campaign_id = c["id"]
        logger.info(f"Campanha criada: {campaign_id}")

        # 2. Conjunto de anúncios
        budget_centavos = int(campanha.budget_diario * 100)
        inicio = campanha.data_inicio or datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0000")

        cs = self._post(f"act_{self.account_id}/adsets", {
            "name": f"{campanha.nome} — Conjunto",
            "campaign_id": campaign_id,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "REACH",
            "daily_budget": budget_centavos,
            "targeting": json.dumps(campanha.publico_alvo),
            "start_time": inicio,
            "status": "PAUSED",
        })
        if "error" in cs:
            return {"erro": cs["error"], "etapa": "adset", "campaign_id": campaign_id}

        adset_id = cs["id"]

        # 3. Criativos + anúncios
        ads_criados = []
        for criativo in campanha.criativos[:3]:  # máx 3 variações
            ad = self._criar_anuncio(adset_id, criativo, campanha.nome)
            ads_criados.append(ad)

        return {
            "sucesso": True,
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "ads": ads_criados,
            "status": "PAUSED — aguardando aprovação para ativar",
        }

    def _criar_anuncio(self, adset_id: str, criativo: dict, nome_campanha: str) -> dict:
        cr = self._post(f"act_{self.account_id}/adcreatives", {
            "name": f"Criativo — {criativo.get('titulo', 'Sem título')}",
            "object_story_spec": json.dumps({
                "page_id": os.getenv("META_PAGE_ID", ""),
                "link_data": {
                    "message": criativo.get("texto", ""),
                    "link": criativo.get("url", "https://nucloventures.com.br"),
                    "call_to_action": {"type": criativo.get("cta", "LEARN_MORE")},
                    **({"picture": criativo["imagem_url"]} if criativo.get("imagem_url") else {}),
                },
            }),
        })

        ad = self._post(f"act_{self.account_id}/ads", {
            "name": f"{nome_campanha} — {criativo.get('titulo','Ad')}",
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": cr.get("id", "")}),
            "status": "PAUSED",
        })
        return {"creative_id": cr.get("id"), "ad_id": ad.get("id")}

    # ── Métricas ──────────────────────────────────────────────

    def metricas_campanha(self, campaign_id: str, dias: int = 7) -> dict:
        """Retorna métricas dos últimos N dias."""
        since = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")

        dados = self._get(f"{campaign_id}/insights", {
            "fields": "impressions,clicks,ctr,cpc,spend,reach,frequency,actions",
            "time_range": json.dumps({"since": since, "until": until}),
        })

        if dados.get("simulado"):
            return {
                "simulado": True,
                "impressoes": 45200, "cliques": 1356, "ctr": "3.0%",
                "cpc": "R$ 1.47", "gasto": f"R$ {dias * 50:.2f}",
                "alcance": 38000,
            }

        raw = dados.get("data", [{}])[0]
        return {
            "impressoes":  int(raw.get("impressions", 0)),
            "cliques":     int(raw.get("clicks", 0)),
            "ctr":         f"{float(raw.get('ctr', 0)):.2f}%",
            "cpc":         f"R$ {float(raw.get('cpc', 0)):.2f}",
            "gasto":       f"R$ {float(raw.get('spend', 0)):.2f}",
            "alcance":     int(raw.get("reach", 0)),
            "frequencia":  round(float(raw.get("frequency", 0)), 2),
        }

    def listar_campanhas(self, status: str = "ACTIVE") -> list[dict]:
        dados = self._get(f"act_{self.account_id}/campaigns", {
            "fields": "id,name,status,objective,daily_budget,created_time",
            "filtering": json.dumps([{"field": "effective_status", "operator": "IN", "value": [status]}]),
        })
        return dados.get("data", [])

    def pausar_campanha(self, campaign_id: str) -> bool:
        r = self._post(f"{campaign_id}", {"status": "PAUSED"})
        return "id" in r

    def ativar_campanha(self, campaign_id: str) -> bool:
        r = self._post(f"{campaign_id}", {"status": "ACTIVE"})
        return "id" in r

    def ajustar_budget(self, adset_id: str, novo_budget_reais: float) -> bool:
        r = self._post(f"{adset_id}", {"daily_budget": int(novo_budget_reais * 100)})
        return "id" in r

    def relatorio_resumido(self, dias: int = 7) -> str:
        """Gera texto resumido para o Lucas/Mariana lerem."""
        campanhas = self.listar_campanhas()
        if not campanhas:
            return "Nenhuma campanha ativa no momento."
        linhas = [f"📊 Meta Ads — últimos {dias} dias\n"]
        for c in campanhas[:5]:
            m = self.metricas_campanha(c["id"], dias)
            linhas.append(
                f"• {c['name']}: {m['impressoes']:,} impressões | "
                f"CTR {m['ctr']} | Gasto {m['gasto']}"
            )
        return "\n".join(linhas)


meta_ads = MetaAdsConnector()

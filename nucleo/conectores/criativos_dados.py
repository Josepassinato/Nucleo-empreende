"""
╔══════════════════════════════════════════════════════════════╗
║   NÚCLEO VENTURES — Criativos + Dados de Mercado            ║
║   Leonardo.AI · SEMrush · Google Analytics 4                ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, logging, httpx, json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("nucleo.criativos_dados")


# ══════════════════════════════════════════════════════════════
# LEONARDO.AI — Geração de imagens para campanhas
# ══════════════════════════════════════════════════════════════

@dataclass
class SolicitacaoImagem:
    prompt: str
    modelo_id: str = "ac614f96-1082-45bf-be9d-757f2d31c174"  # Leonardo Diffusion XL
    largura: int = 1024
    altura: int = 1024
    quantidade: int = 1
    guidance_scale: float = 7.0
    negativo: str = "blurry, low quality, distorted, watermark, text"


class LeonardoAIConnector:
    BASE = "https://cloud.leonardo.ai/api/rest/v1"

    def __init__(self):
        self.key = os.getenv("LEONARDO_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        } if self.key else {}
        if self.key:
            logger.info("✅ Leonardo.AI conectado.")
        else:
            logger.warning("Leonardo.AI não configurado — modo simulação.")

    def gerar_imagem(self, solicitacao: SolicitacaoImagem) -> dict:
        """Gera imagens e retorna URLs."""
        if not self.key:
            return {
                "simulado": True,
                "imagens": ["https://via.placeholder.com/1024x1024?text=Leonardo+AI+Simulado"],
                "generation_id": "SIM_GEN_001",
            }
        try:
            # 1. Criar geração
            r = httpx.post(f"{self.BASE}/generations", headers=self.headers, json={
                "modelId": solicitacao.modelo_id,
                "prompt": solicitacao.prompt,
                "negative_prompt": solicitacao.negativo,
                "width": solicitacao.largura,
                "height": solicitacao.altura,
                "num_images": solicitacao.quantidade,
                "guidance_scale": solicitacao.guidance_scale,
            }, timeout=30)
            gen_id = r.json()["sdGenerationJob"]["generationId"]

            # 2. Polling até ficar pronto (máx 60s)
            import time
            for _ in range(12):
                time.sleep(5)
                status = httpx.get(f"{self.BASE}/generations/{gen_id}", headers=self.headers).json()
                imgs = status.get("generations_by_pk", {}).get("generated_images", [])
                if imgs:
                    return {
                        "generation_id": gen_id,
                        "imagens": [i["url"] for i in imgs],
                        "nsfw": any(i.get("nsfw") for i in imgs),
                    }

            return {"erro": "Timeout na geração", "generation_id": gen_id}
        except Exception as e:
            logger.error(f"Leonardo erro: {e}")
            return {"erro": str(e)}

    def gerar_criativo_campanha(self, produto: str, tom: str = "profissional e moderno") -> dict:
        """Atalho: gera imagem pronta para campanha de marketing."""
        prompt = (
            f"Professional marketing photo for '{produto}'. "
            f"Style: {tom}. High quality, commercial photography, "
            f"clean background, vibrant colors. No text, no watermarks. "
            f"8k resolution, product advertising shot."
        )
        return self.gerar_imagem(SolicitacaoImagem(prompt=prompt, quantidade=2))

    def listar_modelos(self) -> list[dict]:
        if not self.key:
            return []
        try:
            r = httpx.get(f"{self.BASE}/platformModels", headers=self.headers)
            return r.json().get("custom_models", [])
        except:
            return []


# ══════════════════════════════════════════════════════════════
# SEMRUSH — Análise de concorrentes e SEO
# ══════════════════════════════════════════════════════════════

class SEMrushConnector:
    BASE = "https://api.semrush.com"

    def __init__(self):
        self.key = os.getenv("SEMRUSH_API_KEY")
        if self.key:
            logger.info("✅ SEMrush conectado.")
        else:
            logger.warning("SEMrush não configurado — modo simulação.")

    def _get(self, params: dict) -> str:
        if not self.key:
            return ""
        params["key"] = self.key
        try:
            r = httpx.get(self.BASE, params=params, timeout=15)
            return r.text
        except Exception as e:
            logger.error(f"SEMrush erro: {e}")
            return ""

    def _parse_csv(self, csv_text: str) -> list[dict]:
        if not csv_text or csv_text.startswith("ERROR"):
            return []
        linhas = csv_text.strip().split("\n")
        if len(linhas) < 2:
            return []
        headers = linhas[0].split(";")
        return [dict(zip(headers, l.split(";"))) for l in linhas[1:] if l]

    def trafego_organico(self, dominio: str, database: str = "br") -> dict:
        """Tráfego orgânico estimado de um domínio."""
        if not self.key:
            return {
                "simulado": True,
                "dominio": dominio,
                "visitas_mensais": 125000,
                "palavras_chave": 3420,
                "posicao_media": 8.5,
            }
        raw = self._get({
            "type": "domain_organic",
            "domain": dominio,
            "database": database,
            "export_columns": "Or,Ot,Oc,Ad",
            "display_limit": 1,
        })
        rows = self._parse_csv(raw)
        if rows:
            r = rows[0]
            return {
                "dominio": dominio,
                "keywords": int(r.get("Or", 0)),
                "trafego": int(r.get("Ot", 0)),
                "custo_trafego": r.get("Oc", "0"),
            }
        return {}

    def top_keywords(self, dominio: str, database: str = "br", limite: int = 10) -> list[dict]:
        """Top palavras-chave orgânicas de um domínio concorrente."""
        if not self.key:
            return [
                {"keyword": f"keyword_{i}", "position": i+1, "volume": 5000 - i*300}
                for i in range(min(limite, 5))
            ]
        raw = self._get({
            "type": "domain_organic",
            "domain": dominio,
            "database": database,
            "export_columns": "Ph,Po,Nq,Cp",
            "display_limit": limite,
            "display_sort": "nq_desc",
        })
        return self._parse_csv(raw)

    def comparar_concorrentes(self, dominios: list[str]) -> list[dict]:
        """Compara métricas de tráfego de múltiplos concorrentes."""
        resultado = []
        for d in dominios:
            t = self.trafego_organico(d)
            t["dominio"] = d
            resultado.append(t)
        resultado.sort(key=lambda x: x.get("trafego", 0), reverse=True)
        return resultado

    def relatorio_concorrentes(self, dominios: list[str]) -> str:
        """Texto formatado para Dani Ferreira apresentar na reunião."""
        dados = self.comparar_concorrentes(dominios)
        linhas = ["🔍 Análise de Concorrentes — SEMrush\n"]
        for i, d in enumerate(dados):
            linhas.append(
                f"#{i+1} {d['dominio']}: "
                f"{d.get('trafego', 0):,} visitas/mês · "
                f"{d.get('keywords', 0):,} keywords"
            )
        return "\n".join(linhas)


# ══════════════════════════════════════════════════════════════
# GOOGLE ANALYTICS 4 — Tráfego e conversões
# ══════════════════════════════════════════════════════════════

class GoogleAnalyticsConnector:
    def __init__(self):
        self.client = None
        self.property_id = os.getenv("GA4_PROPERTY_ID")
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if self.property_id and creds_path:
            try:
                from google.analytics.data_v1beta import BetaAnalyticsDataClient
                self.client = BetaAnalyticsDataClient()
                logger.info("✅ Google Analytics 4 conectado.")
            except Exception as e:
                logger.warning(f"GA4 erro: {e}")
        else:
            logger.warning("GA4 não configurado — modo simulação.")

    def _simular(self, metrica: str) -> dict:
        return {
            "simulado": True,
            "sessoes": 4320, "usuarios": 3180, "novos_usuarios": 2100,
            "taxa_rejeicao": "38.2%", "duracao_media": "2m 45s",
            "conversoes": 87, "taxa_conversao": "2.01%",
            "top_paginas": ["/", "/produto", "/sobre", "/contato"],
        }

    def relatorio_basico(self, dias: int = 7) -> dict:
        if not self.client:
            return self._simular("basico")
        try:
            from google.analytics.data_v1beta.types import (
                DateRange, Dimension, Metric, RunReportRequest
            )
            req = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=f"{dias}daysAgo",
                    end_date="today",
                )],
                dimensions=[Dimension(name="date")],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                    Metric(name="newUsers"),
                    Metric(name="bounceRate"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="conversions"),
                ],
            )
            resp = self.client.run_report(req)
            total = {m.name: 0 for m in resp.metric_headers}
            for row in resp.rows:
                for i, val in enumerate(row.metric_values):
                    total[resp.metric_headers[i].name] += float(val.value)
            return {
                "periodo_dias": dias,
                "sessoes": int(total.get("sessions", 0)),
                "usuarios_ativos": int(total.get("activeUsers", 0)),
                "novos_usuarios": int(total.get("newUsers", 0)),
                "taxa_rejeicao": f"{total.get('bounceRate', 0):.1f}%",
                "duracao_media_seg": int(total.get("averageSessionDuration", 0)),
                "conversoes": int(total.get("conversions", 0)),
            }
        except Exception as e:
            logger.error(f"GA4 query erro: {e}")
            return self._simular("basico")

    def top_paginas(self, dias: int = 7, limite: int = 10) -> list[dict]:
        if not self.client:
            return [{"pagina": f"/pagina-{i}", "sessoes": 1000 - i*80} for i in range(limite)]
        try:
            from google.analytics.data_v1beta.types import (
                DateRange, Dimension, Metric, RunReportRequest
            )
            req = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date=f"{dias}daysAgo", end_date="today")],
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name="sessions"), Metric(name="conversions")],
                limit=limite,
                order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}],
            )
            resp = self.client.run_report(req)
            return [
                {
                    "pagina": row.dimension_values[0].value,
                    "sessoes": int(row.metric_values[0].value),
                    "conversoes": int(row.metric_values[1].value),
                }
                for row in resp.rows
            ]
        except Exception as e:
            logger.error(f"GA4 top páginas erro: {e}")
            return []

    def relatorio_resumido(self, dias: int = 7) -> str:
        """Texto formatado para Dani/Lucas lerem no relatório."""
        r = self.relatorio_basico(dias)
        return (
            f"📈 Google Analytics — últimos {dias} dias\n"
            f"• Sessões: {r.get('sessoes', 0):,}\n"
            f"• Usuários ativos: {r.get('usuarios_ativos', 0):,}\n"
            f"• Taxa de rejeição: {r.get('taxa_rejeicao', '—')}\n"
            f"• Conversões: {r.get('conversoes', 0):,}\n"
            f"{'⚠️ MODO SIMULAÇÃO' if r.get('simulado') else '✅ Dados reais'}"
        )


# Singletons
leonardo = LeonardoAIConnector()
semrush  = SEMrushConnector()
analytics = GoogleAnalyticsConnector()

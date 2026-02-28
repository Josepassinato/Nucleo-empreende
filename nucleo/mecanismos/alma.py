"""
Nucleo Empreende — Mecanismo de Alma v1.0
Estresse, Proatividade, Leaderboard e Reunião Semanal
"""

import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nucleo.alma")

# ---------------------------------------------------------------------------
# Estado global da Alma (persiste em arquivo JSON entre execuções)
# ---------------------------------------------------------------------------

ALMA_STATE_PATH = Path("nucleo/logs/alma_state.json")

AGENTES_DEFAULT = [
    "lucas_mendes", "mariana_oliveira", "pedro_lima", "carla_santos",
    "rafael_torres", "ana_costa", "ze_carvalho", "dani_ferreira", "beto_rocha"
]

CARGOS = {
    "lucas_mendes":    "CEO",
    "mariana_oliveira":"CMO",
    "pedro_lima":      "CFO",
    "carla_santos":    "COO",
    "rafael_torres":   "CPO",
    "ana_costa":       "CHRO",
    "ze_carvalho":     "Coach",
    "dani_ferreira":   "Analista de Dados",
    "beto_rocha":      "Otimizador",
}

NOMES = {k: k.replace("_", " ").title() for k in AGENTES_DEFAULT}
NOMES["ze_carvalho"] = "Zé Carvalho"

# Superior de cada agente (para escalar quando estresse > 70%)
SUPERIOR = {
    "mariana_oliveira": "lucas_mendes",
    "pedro_lima":       "lucas_mendes",
    "carla_santos":     "lucas_mendes",
    "rafael_torres":    "lucas_mendes",
    "ana_costa":        "lucas_mendes",
    "dani_ferreira":    "lucas_mendes",
    "beto_rocha":       "pedro_lima",
    "ze_carvalho":      "lucas_mendes",
    "lucas_mendes":     None,  # escala para o Dono
}

PESOS_LEADERBOARD = {"kpi": 0.4, "proatividade": 0.3, "pontualidade": 0.2, "cultura": 0.1}


# ---------------------------------------------------------------------------
# Classe AlmaEstado — estado emocional/operacional de um agente
# ---------------------------------------------------------------------------

class AlmaEstado:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.nome = NOMES.get(agent_id, agent_id)
        self.cargo = CARGOS.get(agent_id, "Agente")
        self.estresse: float = 0.0          # 0.0 – 1.0
        self.energia: float = 1.0           # 0.0 – 1.0
        self.confianca: float = 1.0         # bônus acumulado por boas sugestões
        self.tarefas_concluidas: int = 0
        self.tarefas_atrasadas: int = 0
        self.sugestoes_aceitas: int = 0
        self.scores: dict = {"kpi": 5.0, "proatividade": 5.0, "pontualidade": 5.0, "cultura": 5.0}
        self.historico_eventos: list = []

    # ---- Propriedade calculada ------------------------------------------------

    @property
    def score_total(self) -> float:
        s = sum(self.scores[k] * PESOS_LEADERBOARD[k] for k in PESOS_LEADERBOARD)
        return round(min(10.0, max(0.0, s * self.confianca)), 2)

    # ---- Mutadores -----------------------------------------------------------

    def receber_feedback_negativo(self, intensidade: float = 0.15):
        self.estresse = min(1.0, self.estresse + intensidade)
        self.scores["cultura"] = max(0, self.scores["cultura"] - 0.5)
        self._log_evento(f"Feedback negativo recebido. Estresse → {self.estresse:.0%}")

    def concluir_tarefa(self, no_prazo: bool = True):
        self.tarefas_concluidas += 1
        self.estresse = max(0.0, self.estresse - 0.1)
        self.energia = min(1.0, self.energia + 0.05)
        if no_prazo:
            self.scores["pontualidade"] = min(10, self.scores["pontualidade"] + 0.3)
            self.scores["kpi"] = min(10, self.scores["kpi"] + 0.2)
        else:
            self.tarefas_atrasadas += 1
            self.scores["pontualidade"] = max(0, self.scores["pontualidade"] - 0.5)
            self.estresse = min(1.0, self.estresse + 0.2)
        self._log_evento(f"Tarefa {'no prazo' if no_prazo else 'ATRASADA'} concluída.")

    def registrar_sugestao_aceita(self):
        self.sugestoes_aceitas += 1
        self.confianca = min(1.5, self.confianca + 0.05)
        self.scores["proatividade"] = min(10, self.scores["proatividade"] + 0.4)
        self._log_evento("Sugestão aceita! Bônus de confiança aplicado.")

    def aplicar_coaching(self):
        reducao = min(self.estresse, 0.25)
        self.estresse -= reducao
        self.energia = min(1.0, self.energia + 0.1)
        self._log_evento(f"Coaching com Zé Carvalho. Estresse ↓{reducao:.0%}, energia ↑")

    def modo_proativo(self) -> bool:
        """Retorna True ~20% das chamadas, indicando janela proativa."""
        ativo = random.random() < 0.20
        if ativo:
            self.scores["proatividade"] = min(10, self.scores["proatividade"] + 0.1)
            self._log_evento("Janela proativa: explorando soluções fora da caixa.")
        return ativo

    # ---- Alertas -------------------------------------------------------------

    def verificar_estresse(self) -> Optional[str]:
        if self.estresse >= 0.7:
            superior_id = SUPERIOR.get(self.agent_id)
            destino = NOMES.get(superior_id, "Dono") if superior_id else "Dono"
            msg = (
                f"⚠️  [{self.nome} / {self.cargo}] ALERTA DE ESTRESSE: {self.estresse:.0%}\n"
                f"   → Escalando para {destino} e solicitando suporte do Coach."
            )
            logger.warning(msg)
            return msg
        return None

    # ---- Serialização --------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "nome": self.nome,
            "cargo": self.cargo,
            "estresse": round(self.estresse, 3),
            "energia": round(self.energia, 3),
            "confianca": round(self.confianca, 3),
            "tarefas_concluidas": self.tarefas_concluidas,
            "tarefas_atrasadas": self.tarefas_atrasadas,
            "sugestoes_aceitas": self.sugestoes_aceitas,
            "scores": self.scores,
            "score_total": self.score_total,
            "historico_eventos": self.historico_eventos[-10:],  # últimos 10
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AlmaEstado":
        obj = cls(d["agent_id"])
        obj.estresse = d.get("estresse", 0.0)
        obj.energia = d.get("energia", 1.0)
        obj.confianca = d.get("confianca", 1.0)
        obj.tarefas_concluidas = d.get("tarefas_concluidas", 0)
        obj.tarefas_atrasadas = d.get("tarefas_atrasadas", 0)
        obj.sugestoes_aceitas = d.get("sugestoes_aceitas", 0)
        obj.scores = d.get("scores", obj.scores)
        obj.historico_eventos = d.get("historico_eventos", [])
        return obj

    def _log_evento(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.historico_eventos.append(f"[{ts}] {msg}")
        logger.debug(f"[{self.nome}] {msg}")


# ---------------------------------------------------------------------------
# Gerenciador global da Alma
# ---------------------------------------------------------------------------

class GerenciadorAlma:
    def __init__(self):
        self.agentes: dict[str, AlmaEstado] = {}
        self._carregar()

    def _carregar(self):
        if ALMA_STATE_PATH.exists():
            with open(ALMA_STATE_PATH, "r") as f:
                data = json.load(f)
            for agent_id, d in data.items():
                self.agentes[agent_id] = AlmaEstado.from_dict(d)
            logger.info(f"Alma carregada para {len(self.agentes)} agentes.")
        else:
            for agent_id in AGENTES_DEFAULT:
                self.agentes[agent_id] = AlmaEstado(agent_id)
            logger.info("Alma inicializada com valores padrão.")

    def salvar(self):
        ALMA_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ALMA_STATE_PATH, "w") as f:
            json.dump({k: v.to_dict() for k, v in self.agentes.items()}, f, ensure_ascii=False, indent=2)

    def get(self, agent_id: str) -> AlmaEstado:
        if agent_id not in self.agentes:
            self.agentes[agent_id] = AlmaEstado(agent_id)
        return self.agentes[agent_id]

    # ---- Leaderboard ---------------------------------------------------------

    def leaderboard(self) -> list[dict]:
        ranking = sorted(
            [a.to_dict() for a in self.agentes.values()],
            key=lambda x: x["score_total"],
            reverse=True,
        )
        for i, item in enumerate(ranking):
            item["posicao"] = i + 1
            if i < 3:
                item["status"] = "🏆 TOP 3 — bônus de crédito + folga"
            elif i >= len(ranking) - 3:
                item["status"] = "⚠️  BOTTOM 3 — coaching extra + plano de melhoria"
            else:
                item["status"] = "✅ Regular"
        return ranking

    def imprimir_leaderboard(self):
        print("\n" + "=" * 60)
        print("       🏅  LEADERBOARD — NÚCLEO VENTURES")
        print("=" * 60)
        for item in self.leaderboard():
            bar = "█" * int(item["score_total"]) + "░" * (10 - int(item["score_total"]))
            print(f"#{item['posicao']:>2}  {item['nome']:<22} [{bar}] {item['score_total']:.1f}")
            print(f"      Estresse: {item['estresse']:.0%}  |  {item['status']}")
        print("=" * 60)

    # ---- Verificar alertas de toda a equipe -----------------------------------

    def verificar_todos_alertas(self) -> list[str]:
        alertas = []
        for agente in self.agentes.values():
            alerta = agente.verificar_estresse()
            if alerta:
                alertas.append(alerta)
        return alertas

    # ---- Sessão de coaching coletiva (Zé Carvalho) ---------------------------

    def coaching_para_estressados(self):
        ze = self.get("ze_carvalho")
        for agente in self.agentes.values():
            if agente.estresse >= 0.6 and agente.agent_id != "ze_carvalho":
                agente.aplicar_coaching()
                ze.scores["kpi"] = min(10, ze.scores["kpi"] + 0.1)
                logger.info(f"[Zé Carvalho] Coaching aplicado a {agente.nome}.")


# Instância global reutilizável
alma = GerenciadorAlma()

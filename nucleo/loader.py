"""
Nucleo Empreende — Loader Dinâmico de Agentes e Tarefas
Carrega agents.yaml e tasks.yaml e cria objetos CrewAI dinamicamente.
"""

import yaml
import logging
from pathlib import Path
from crewai import Agent, Task
from crewai_tools import Tool
from nucleo.mecanismos.alma import alma, GerenciadorAlma

logger = logging.getLogger("nucleo.loader")


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def criar_agentes(
    agents_yaml_path: str,
    llm,
    tools_map: dict,
    gerenciador_alma: GerenciadorAlma,
) -> dict[str, Agent]:
    """
    Lê agents.yaml e cria um dict {agent_id: Agent CrewAI}.
    Injeta no backstory o estado emocional atual da Alma de cada agente.
    """
    data = load_yaml(agents_yaml_path)
    agentes: dict[str, Agent] = {}

    for agent_id, cfg in data.get("agents", {}).items():
        estado = gerenciador_alma.get(agent_id)

        # Enriquecer backstory com estado emocional atual
        alma_snippet = (
            f"\n\n[ESTADO INTERNO ATUAL]\n"
            f"- Estresse: {estado.estresse:.0%} {'(ALTO — peça ajuda se necessário)' if estado.estresse >= 0.7 else ''}\n"
            f"- Energia: {estado.energia:.0%}\n"
            f"- Confiança acumulada: {estado.confianca:.2f}\n"
            f"- Score no leaderboard: {estado.score_total}/10\n"
            f"- Proatividade ativa esta rodada: {'SIM — sugira uma solução inovadora!' if estado.modo_proativo() else 'NÃO'}\n"
        )

        backstory_final = cfg.get("backstory", "") + alma_snippet

        # Resolver ferramentas declaradas no YAML
        agent_tools = [
            tools_map[t] for t in cfg.get("tools", []) if t in tools_map
        ]

        agente = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=backstory_final,
            verbose=True,
            allow_delegation=cfg.get("allow_delegation", True),
            tools=agent_tools,
            llm=llm,
        )
        agentes[agent_id] = agente
        logger.info(f"Agente criado: {cfg['role']} (id={agent_id})")

    return agentes


def criar_tarefas(
    tasks_yaml_path: str,
    agentes: dict[str, Agent],
) -> list[Task]:
    """
    Lê tasks.yaml e cria lista de Tasks CrewAI na ordem declarada.
    Suporta campo opcional 'depends_on' (lista de task_ids anteriores).
    """
    data = load_yaml(tasks_yaml_path)
    tarefas: list[Task] = {}  # dict para lookup de dependências
    ordem: list[str] = []

    for task_id, cfg in data.get("tasks", {}).items():
        agent_id = cfg.get("agent")
        agente = agentes.get(agent_id)
        if not agente:
            logger.warning(f"Agente '{agent_id}' não encontrado para task '{task_id}'. Pulando.")
            continue

        context_tasks = []
        for dep_id in cfg.get("depends_on", []):
            if dep_id in tarefas:
                context_tasks.append(tarefas[dep_id])

        task = Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=agente,
            context=context_tasks if context_tasks else None,
        )
        tarefas[task_id] = task
        ordem.append(task_id)
        logger.info(f"Tarefa criada: '{task_id}' → agente: {agent_id}")

    return [tarefas[tid] for tid in ordem]

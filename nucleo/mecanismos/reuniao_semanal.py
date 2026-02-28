"""
Nucleo Empreende — Reunião Semanal Simulada
Lucas Mendes (CEO) lidera. Todos os diretores participam.
Gera ata em Markdown e salva em nucleo/docs/
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger("nucleo.reuniao")

ATA_DIR = Path("nucleo/docs")

PAUTA_BASE = """
Você está conduzindo a reunião semanal da diretoria da Nucleo Empreende.

PARTICIPANTES (você interpreta cada um em sequência):
- Lucas Mendes (CEO) — abre e fecha a reunião, define prioridades
- Mariana Oliveira (CMO) — update de marketing e campanhas
- Pedro Lima (CFO) — update financeiro, alertas de custo
- Carla Santos (COO) — update operacional, gargalos
- Rafael Torres (CPO) — update de produto, próximas features
- Ana Costa (CHRO) — update de time, contratações, cultura
- Dani Ferreira (Analista de Dados) — insights de dados, alertas de mercado
- Beto Rocha (Otimizador) — oportunidades de corte de custo
- Zé Carvalho (Coach) — bem-estar da equipe, ponto de atenção

CONTEXTO DO LEADERBOARD ATUAL:
{leaderboard_resumo}

ALERTAS DE ESTRESSE:
{alertas_estresse}

PAUTA DESTA SEMANA:
{pauta_customizada}

Escreva a ata completa da reunião em formato de chat simulado (como se fosse WhatsApp/Slack),
com cada participante falando na sua vez. Use os temperamentos de cada agente:
- Lucas: visionário, calmo, firme
- Mariana: criativa, ansiosa, perfeccionista  
- Pedro: pão-duro, prático, questionador
- Carla: organizada, cobra resultados
- Rafael: curioso, quer testar coisas
- Ana: empática, direta
- Zé: calmo, mentor, pai de santo
- Dani: paranoica, detalhista
- Beto: econômico, caça o grátis

A reunião deve ser realista, com divergências saudáveis, sugestões concretas e decisões tomadas.
Ao final, Lucas fecha com os 3 próximos passos da semana.

Formato de saída: Markdown com emojis, seções por participante.
"""


def gerar_reuniao_semanal(
    llm: ChatGoogleGenerativeAI,
    leaderboard: list[dict],
    alertas: list[str],
    pauta_extra: str = "Revisão geral de KPIs, oportunidades da semana e riscos a mitigar.",
) -> str:
    """Gera a ata da reunião semanal usando o LLM configurado."""

    # Formata resumo do leaderboard
    lb_resumo = "\n".join(
        f"#{item['posicao']} {item['nome']} ({item['cargo']}) — Score: {item['score_total']}/10 | Estresse: {item['estresse']:.0%} | {item['status']}"
        for item in leaderboard
    )

    alertas_str = "\n".join(alertas) if alertas else "Nenhum alerta crítico de estresse esta semana. ✅"

    prompt = PAUTA_BASE.format(
        leaderboard_resumo=lb_resumo,
        alertas_estresse=alertas_str,
        pauta_customizada=pauta_extra,
    )

    logger.info("Gerando reunião semanal com LLM...")
    response = llm.invoke(prompt)
    ata = response.content if hasattr(response, "content") else str(response)

    # Salva a ata
    ATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    ata_path = ATA_DIR / f"ata_reuniao_{ts}.md"
    header = f"# 📋 Ata de Reunião Semanal — {datetime.now().strftime('%d/%m/%Y')}\n\n"
    with open(ata_path, "w") as f:
        f.write(header + ata)

    logger.info(f"Ata salva em {ata_path}")
    return ata


def imprimir_ata(ata: str):
    print("\n" + "=" * 70)
    print("            📋  REUNIÃO SEMANAL — NÚCLEO VENTURES")
    print("=" * 70)
    print(ata)
    print("=" * 70)

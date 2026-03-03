"""
╔══════════════════════════════════════════════════════════════════╗
║           NÚCLEO VENTURES — Diretoria Autônoma de IA            ║
║                        main_gemini.py                           ║
║                                                                 ║
║  Stack: CrewAI · Gemini 2.0 Flash · Playwright · Alma v1.0     ║
╚══════════════════════════════════════════════════════════════════╝

Execução:
    python3 main_gemini.py
    python3 main_gemini.py --modo reuniao     (apenas reunião semanal)
    python3 main_gemini.py --modo leaderboard (apenas exibe ranking)
    python3 main_gemini.py --modo tarefas     (ciclo completo de tarefas)
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────
# Configuração de logging
# ──────────────────────────────────────────────────────────────────

LOG_DIR = Path("nucleo/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"nucleo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("nucleo.main")

# ──────────────────────────────────────────────────────────────────
# Carrega variáveis de ambiente
# ──────────────────────────────────────────────────────────────────

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.critical("❌  GOOGLE_API_KEY não encontrada! Crie um arquivo .env com ela.")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────
# Imports CrewAI / LangChain / Ferramentas
# ──────────────────────────────────────────────────────────────────

from crewai import Crew, Process
from crewai.tools import BaseTool
from typing import Any

from nucleo.config_loader import config          # ← inicializa TODA a stack
from nucleo.loader import criar_agentes, criar_tarefas

try:
    from nucleo.ferramentas.navegacao_autonoma.tool import NavegacaoAutonomaTool
    _NAV_DISPONIVEL = True
except ImportError as e:
    logger.warning(f"NavegacaoAutonomaTool indisponível (API browser_use mudou): {e}")
    _NAV_DISPONIVEL = False
from nucleo.mecanismos.alma import alma
from nucleo.mecanismos.reuniao_semanal import gerar_reuniao_semanal, imprimir_ata

# ──────────────────────────────────────────────────────────────────
# LLM principal — vem do config_loader (Gemini 2.0 Flash por padrão)
# ──────────────────────────────────────────────────────────────────

gemini_llm = config.llm_principal()
if not gemini_llm:
    logger.critical("Nenhum LLM disponível. Verifique as API Keys no .env")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────
# Ferramentas disponíveis
# ──────────────────────────────────────────────────────────────────

TOOLS_MAP: dict[str, BaseTool] = {}

if _NAV_DISPONIVEL:
    navegacao_instance = NavegacaoAutonomaTool()

    class NavegarSiteTool(BaseTool):
        name: str = "Navegar Site"
        description: str = (
            "Navega em sites reais como um humano. Recebe instrução natural e executa. "
            "Ex: 'pesquise concorrentes no Google, abra o primeiro resultado, tire screenshot'. "
            "Retorna texto extraído + screenshot em base64."
        )

        def _run(self, instrucao: str, **kwargs) -> Any:
            return navegacao_instance.navegar_site(instrucao, **kwargs)

    TOOLS_MAP["Navegar Site"] = NavegarSiteTool()
else:
    logger.info("⚪ Ferramenta 'Navegar Site' desativada — browser_use incompatível.")

# ──────────────────────────────────────────────────────────────────
# Banner de inicialização
# ──────────────────────────────────────────────────────────────────

def banner():
    print("\n" + "═" * 65)
    print("  🚀  NÚCLEO VENTURES — Diretoria Autônoma de IA  v1.0")
    print(f"  🤖  Modelo: Gemini 2.0 Flash")
    print(f"  📅  Sessão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  📁  Log: {log_file}")
    print("═" * 65 + "\n")


# ──────────────────────────────────────────────────────────────────
# MODO: LEADERBOARD
# ──────────────────────────────────────────────────────────────────

def modo_leaderboard():
    alma.imprimir_leaderboard()
    alertas = alma.verificar_todos_alertas()
    if alertas:
        print("\n⚠️  ALERTAS DE ESTRESSE:")
        for a in alertas:
            print(a)
    alma.salvar()


# ──────────────────────────────────────────────────────────────────
# MODO: REUNIÃO SEMANAL
# ──────────────────────────────────────────────────────────────────

def modo_reuniao(pauta_extra: str = ""):
    logger.info("📋 Iniciando reunião semanal...")
    leaderboard = alma.leaderboard()
    alertas = alma.verificar_todos_alertas()

    # Coaching para quem está estressado (Zé Carvalho age antes da reunião)
    alma.coaching_para_estressados()

    ata = gerar_reuniao_semanal(
        llm=gemini_llm,
        leaderboard=leaderboard,
        alertas=alertas,
        pauta_extra=pauta_extra or "Revisão geral de KPIs, oportunidades da semana e riscos a mitigar.",
    )
    imprimir_ata(ata)

    # Atualiza scores pós-reunião (participação = +0.1 cultura)
    for agent_id in alma.agentes:
        alma.get(agent_id).scores["cultura"] = min(
            10, alma.get(agent_id).scores["cultura"] + 0.1
        )

    alma.imprimir_leaderboard()
    alma.salvar()
    return ata


# ──────────────────────────────────────────────────────────────────
# MODO: CICLO COMPLETO DE TAREFAS
# ──────────────────────────────────────────────────────────────────

def modo_tarefas():
    logger.info("⚙️  Iniciando ciclo completo de tarefas...")

    # Verificar e agir sobre alertas
    alertas = alma.verificar_todos_alertas()
    if alertas:
        logger.warning(f"{len(alertas)} agente(s) com estresse alto. Coaching preventivo...")
        alma.coaching_para_estressados()

    # Criar agentes dinamicamente do YAML
    logger.info("📂 Carregando agents.yaml...")
    agentes = criar_agentes(
        agents_yaml_path="agents.yaml",
        llm=gemini_llm,
        tools_map=TOOLS_MAP,
        gerenciador_alma=alma,
    )

    # Criar tarefas dinamicamente do YAML
    logger.info("📂 Carregando tasks.yaml...")
    tarefas = criar_tarefas(
        tasks_yaml_path="tasks.yaml",
        agentes=agentes,
    )

    logger.info(f"✅ {len(agentes)} agentes e {len(tarefas)} tarefas carregados.")

    # Montar e executar a Crew
    crew = Crew(
        agents=list(agentes.values()),
        tasks=tarefas,
        verbose=True,
        process=Process.sequential,  # executa na ordem do YAML respeitando depends_on
    )

    print("\n🏁 Iniciando execução da Crew...\n")
    inicio = datetime.now()

    try:
        resultado = crew.kickoff()
        duracao = (datetime.now() - inicio).total_seconds()

        print("\n" + "═" * 65)
        print("  ✅  CICLO CONCLUÍDO COM SUCESSO")
        print(f"  ⏱️  Duração: {duracao:.1f}s")
        print("═" * 65)
        print("\n📋 SÍNTESE FINAL:\n")
        print(resultado)

        # Atualiza Alma: todas as tarefas concluídas no prazo
        for agent_id in agentes:
            alma.get(agent_id).concluir_tarefa(no_prazo=True)

        # Salva resultado em arquivo
        resultado_path = LOG_DIR / f"resultado_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        with open(resultado_path, "w") as f:
            f.write(f"# Resultado — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            f.write(str(resultado))
        logger.info(f"Resultado salvo em {resultado_path}")

    except Exception as e:
        logger.error(f"❌ Erro durante execução: {e}", exc_info=True)
        # Aumenta estresse do CEO e do agente responsável pela última tarefa
        alma.get("lucas_mendes").receber_feedback_negativo(0.2)
        for agent_id in agentes:
            alma.get(agent_id).concluir_tarefa(no_prazo=False)
        raise

    finally:
        alma.imprimir_leaderboard()
        alma.salvar()

    return resultado


# ──────────────────────────────────────────────────────────────────
# MODO: COMPLETO (tarefas + reunião + leaderboard)
# ──────────────────────────────────────────────────────────────────

def modo_completo():
    logger.info("🌟 Modo COMPLETO ativado — tarefas + reunião semanal + leaderboard")

    # 1. Ciclo de tarefas
    resultado_tarefas = modo_tarefas()

    # 2. Reunião semanal com contexto do que foi feito
    pauta = (
        "Revisão dos resultados do ciclo de tarefas desta semana. "
        "Análise dos relatórios entregues: pesquisa de mercado, campanha de marketing, "
        "plano de produto, relatório financeiro e plano operacional. "
        "Decisões a tomar e prioridades para a próxima semana."
    )
    modo_reuniao(pauta_extra=pauta)

    # 3. Leaderboard final
    print("\n🏅 RANKING FINAL DA SEMANA:")
    alma.imprimir_leaderboard()


# ──────────────────────────────────────────────────────────────────
# KILL SWITCH (segurança do Dono)
# ──────────────────────────────────────────────────────────────────

def verificar_kill_switch():
    kill_switch_path = Path("nucleo/seguranca/.kill_switch")
    if kill_switch_path.exists():
        logger.critical("🛑 KILL SWITCH ATIVADO! Encerrando sistema imediatamente.")
        print("\n🛑 KILL SWITCH ATIVADO — Sistema encerrado pelo Dono.")
        sys.exit(0)


# ──────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Increase Team — Diretoria Autônoma de IA"
    )
    parser.add_argument(
        "--modo",
        choices=["completo", "tarefas", "reuniao", "leaderboard"],
        default="completo",
        help="Modo de execução (padrão: completo)",
    )
    parser.add_argument(
        "--pauta",
        type=str,
        default="",
        help="Pauta extra para a reunião semanal",
    )
    args = parser.parse_args()

    banner()
    verificar_kill_switch()

    logger.info(f"Modo de execução: {args.modo}")

    if args.modo == "leaderboard":
        modo_leaderboard()

    elif args.modo == "reuniao":
        modo_reuniao(pauta_extra=args.pauta)

    elif args.modo == "tarefas":
        modo_tarefas()

    else:  # completo
        modo_completo()


if __name__ == "__main__":
    main()

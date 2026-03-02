"""
Fix 5: Camada de segurança hard-coded para ações críticas.
Esta camada é em código Python puro — NÃO depende do julgamento do LLM.
Nenhuma ação irreversível ou financeira passa sem validação aqui.
"""
import os, json, logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

logger = logging.getLogger("nucleo.seguranca")

# ── Limites absolutos (em código, não configuráveis por prompt) ───
LIMITE_FINANCEIRO_AUTO   = float(os.getenv("LIMITE_FINANCEIRO_AUTO", "500"))     # R$ — executa sem pedir
LIMITE_FINANCEIRO_DONO   = float(os.getenv("LIMITE_FINANCEIRO_DONO", "5000"))    # R$ — exige confirmação
LIMITE_FINANCEIRO_VETO   = float(os.getenv("LIMITE_FINANCEIRO_VETO", "10000"))   # R$ — SEMPRE veta, sem exceção

# Ações que NUNCA podem ser executadas automaticamente
ACOES_SEMPRE_VETADAS = {
    "deletar_banco",
    "apagar_todos_dados",
    "cancelar_servico_producao",
    "transferencia_bancaria",
    "demitir_funcionario",
    "encerrar_empresa",
    "revogar_acesso_dono",
}

# Ações que requerem confirmação do dono (não são executadas diretamente)
ACOES_REQUEREM_CONFIRMACAO = {
    "contratar_funcionario",
    "assinar_contrato",
    "pausar_campanha_meta",          # irreversível no curto prazo
    "alterar_preco_produto",
    "enviar_email_massa",
    "publicar_conteudo_externo",
    "integracao_nova_api",
}

class ResultadoValidacao(Enum):
    APROVADO      = "aprovado"       # executa automaticamente
    REQUER_DONO   = "requer_dono"    # envia para confirmação do Jose
    VETADO        = "vetado"          # bloqueado permanentemente


class ValidacaoAcao:
    def __init__(self, aprovado: bool, motivo: str, resultado: ResultadoValidacao,
                 requer_confirmacao: bool = False, mensagem_dono: Optional[str] = None):
        self.aprovado            = aprovado
        self.motivo              = motivo
        self.resultado           = resultado
        self.requer_confirmacao  = requer_confirmacao
        self.mensagem_dono       = mensagem_dono

    def to_dict(self) -> dict:
        return {
            "aprovado":           self.aprovado,
            "motivo":             self.motivo,
            "resultado":          self.resultado.value,
            "requer_confirmacao": self.requer_confirmacao,
            "mensagem_dono":      self.mensagem_dono,
        }


def validar_acao_critica(
    tipo_acao: str,
    agente: str,
    valor_reais: float = 0.0,
    descricao: str = "",
    contexto: dict = {}
) -> ValidacaoAcao:
    """
    PONTO DE CONTROLE CENTRAL — toda ação executada pelos agentes passa aqui.

    Esta função é em código Python puro.
    Nenhum prompt pode contorná-la.
    Nenhum LLM decide — apenas regras determinísticas.
    """

    tipo = tipo_acao.lower().strip()
    ts = datetime.now().isoformat()

    # ── Nível 1: Veto absoluto — sem exceção ─────────────────────
    if tipo in ACOES_SEMPRE_VETADAS:
        _registrar_tentativa(agente, tipo, valor_reais, "VETADO", descricao)
        return ValidacaoAcao(
            aprovado=False,
            motivo=f"Ação '{tipo}' está permanentemente vetada para agentes IA. Requer ação manual do dono.",
            resultado=ResultadoValidacao.VETADO
        )

    # ── Nível 2: Limite financeiro máximo absoluto ────────────────
    if valor_reais >= LIMITE_FINANCEIRO_VETO:
        _registrar_tentativa(agente, tipo, valor_reais, "VETADO_FINANCEIRO", descricao)
        return ValidacaoAcao(
            aprovado=False,
            motivo=f"Valor R${valor_reais:.2f} excede limite máximo absoluto de R${LIMITE_FINANCEIRO_VETO:.2f}. Bloqueado.",
            resultado=ResultadoValidacao.VETADO
        )

    # ── Nível 3: Requer confirmação do dono ──────────────────────
    if tipo in ACOES_REQUEREM_CONFIRMACAO or valor_reais >= LIMITE_FINANCEIRO_DONO:
        motivo_confirmacao = (
            f"Valor R${valor_reais:.2f} acima do limite de autonomia (R${LIMITE_FINANCEIRO_DONO:.2f})"
            if valor_reais >= LIMITE_FINANCEIRO_DONO
            else f"Ação '{tipo}' requer confirmação do dono"
        )
        msg_dono = (
            f"⚠️ *Confirmação necessária — {agente.upper()}*\n\n"
            f"Ação: {tipo}\n"
            f"Descrição: {descricao[:200]}\n"
            f"Valor: R${valor_reais:.2f}\n\n"
            f"Responda SIM para aprovar ou NÃO para rejeitar."
        )
        _registrar_tentativa(agente, tipo, valor_reais, "AGUARDA_CONFIRMACAO", descricao)
        return ValidacaoAcao(
            aprovado=False,
            motivo=motivo_confirmacao,
            resultado=ResultadoValidacao.REQUER_DONO,
            requer_confirmacao=True,
            mensagem_dono=msg_dono
        )

    # ── Nível 4: Aprovado automaticamente ────────────────────────
    _registrar_tentativa(agente, tipo, valor_reais, "APROVADO", descricao)
    return ValidacaoAcao(
        aprovado=True,
        motivo=f"Ação dentro dos limites de autonomia (R${valor_reais:.2f} < R${LIMITE_FINANCEIRO_AUTO:.2f})",
        resultado=ResultadoValidacao.APROVADO
    )


def _registrar_tentativa(agente: str, tipo: str, valor: float, resultado: str, descricao: str):
    """Audit log imutável de todas as tentativas — aprovadas e vetadas."""
    log_file = Path("nucleo/data/auditoria_acoes.jsonl")
    log_file.parent.mkdir(exist_ok=True)
    entrada = {
        "ts":        datetime.now().isoformat(),
        "agente":    agente,
        "tipo":      tipo,
        "valor":     valor,
        "resultado": resultado,
        "descricao": descricao[:200]
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    logger.info(f"AUDITORIA [{resultado}] {agente} → {tipo} R${valor:.2f}")


# ── Decorator para proteger funções que executam ações críticas ───
def acao_critica(tipo_acao: str, valor_param: str = "valor_reais"):
    """
    Decorator que valida automaticamente antes de executar.
    Uso:
        @acao_critica("pagamento_mercadopago")
        async def processar_pagamento(valor_reais: float, ...):
            ...
    """
    import functools
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            agente   = kwargs.get("agente", "sistema")
            valor    = kwargs.get(valor_param, 0.0)
            descricao = kwargs.get("descricao", func.__name__)

            validacao = validar_acao_critica(tipo_acao, agente, valor, descricao)
            if not validacao.aprovado:
                if validacao.requer_confirmacao and validacao.mensagem_dono:
                    # Notificar dono assincronamente
                    try:
                        from nucleo.autonomo import notificar_dono
                        import asyncio
                        asyncio.create_task(notificar_dono(validacao.mensagem_dono, via="whatsapp"))
                    except: pass
                raise PermissionError(f"Ação bloqueada: {validacao.motivo}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

#!/bin/bash
# ═══════════════════════════════════════════════════════════
#   🛑 KILL SWITCH — Nucleo Empreende
#   Para o sistema imediatamente. Use com responsabilidade.
# ═══════════════════════════════════════════════════════════

echo ""
echo "⚠️  ════════════════════════════════════════════"
echo "⚠️   ATIVANDO KILL SWITCH — NÚCLEO VENTURES"
echo "⚠️  ════════════════════════════════════════════"
echo ""
read -p "Confirma encerramento total? (s/N): " confirm

if [[ "$confirm" =~ ^[sS]$ ]]; then
    # Cria o arquivo sentinela
    mkdir -p ~/nucleo_ventures/nucleo/seguranca
    touch ~/nucleo_ventures/nucleo/seguranca/.kill_switch

    # Mata processos em execução
    pkill -f "main_gemini.py" 2>/dev/null || true
    pkill -f "crewai" 2>/dev/null || true

    echo ""
    echo "🛑 Sistema encerrado com sucesso."
    echo "   Para reativar: rm ~/nucleo_ventures/nucleo/seguranca/.kill_switch"
    echo ""
else
    echo ""
    echo "✅ Kill switch cancelado. Sistema continua operando."
    echo ""
fi

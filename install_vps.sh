#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#   NÚCLEO VENTURES — Script de Instalação VPS
#   Ubuntu 22.04 / Debian 12 | CrewAI + Gemini 2.0 Flash
# ═══════════════════════════════════════════════════════════════

set -e  # Para imediatamente em qualquer erro

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    NÚCLEO VENTURES — Instalação na VPS           ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Atualizar sistema ──────────────────────────────────────
echo "📦 [1/7] Atualizando pacotes do sistema..."
sudo apt update && sudo apt upgrade -y

# ── 2. Python e pip ──────────────────────────────────────────
echo "🐍 [2/7] Instalando Python 3.11 e pip..."
sudo apt install -y python3 python3-pip python3-venv python3-dev git curl

# ── 3. Dependências do Playwright ────────────────────────────
echo "🎭 [3/7] Instalando dependências do Playwright..."
sudo apt install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libxkbcommon0 libdrm-dev libgbm-dev libasound2 \
    libxcomposite1 libxdamage1 libxrandr2 libcups2 \
    libpango-1.0-0 libcairo2 libglib2.0-0

# ── 4. Ambiente virtual ──────────────────────────────────────
echo "📁 [4/7] Criando ambiente virtual Python..."
mkdir -p ~/nucleo_ventures
cd ~/nucleo_ventures

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# ── 5. Dependências Python ───────────────────────────────────
echo "📚 [5/7] Instalando dependências Python..."
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install \
        crewai \
        crewai-tools \
        langchain-google-genai \
        playwright \
        browser-use \
        python-dotenv \
        pyyaml
fi

# ── 6. Chromium para Playwright ──────────────────────────────
echo "🌐 [6/7] Instalando Chromium para Playwright..."
playwright install chromium --with-deps

# ── 7. Estrutura de diretórios ───────────────────────────────
echo "🗂️  [7/7] Criando estrutura de diretórios..."
mkdir -p nucleo/{logs,docs,agentes,config,mecanismos,seguranca,stack,ferramentas/navegacao_autonoma}

# ── Configuração do .env ─────────────────────────────────────
if [ ! -f ".env" ]; then
    echo ""
    echo "🔑 Configurando .env..."
    read -p "   Cole sua GOOGLE_API_KEY (Enter para pular): " api_key
    if [ -n "$api_key" ]; then
        echo "GOOGLE_API_KEY='$api_key'" > .env
        echo "   ✅ .env criado com sucesso!"
    else
        echo "GOOGLE_API_KEY='SUA_CHAVE_GEMINI_AQUI'" > .env
        echo "   ⚠️  Edite o arquivo .env antes de executar: nano ~/nucleo_ventures/.env"
    fi
fi

# ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅  INSTALAÇÃO CONCLUÍDA!                       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Próximos passos:"
echo "  1. Verifique a API Key:    nano ~/nucleo_ventures/.env"
echo "  2. Ative o ambiente:       source ~/nucleo_ventures/.venv/bin/activate"
echo "  3. Execute o sistema:"
echo "     cd ~/nucleo_ventures"
echo ""
echo "     # Modo completo (tarefas + reunião + leaderboard):"
echo "     python3 main_gemini.py"
echo ""
echo "     # Apenas reunião semanal:"
echo "     python3 main_gemini.py --modo reuniao"
echo ""
echo "     # Apenas leaderboard:"
echo "     python3 main_gemini.py --modo leaderboard"
echo ""
echo "     # Apenas ciclo de tarefas:"
echo "     python3 main_gemini.py --modo tarefas"
echo ""
echo "  📖 Documentação: ~/nucleo_ventures/nucleo/docs/"
echo ""

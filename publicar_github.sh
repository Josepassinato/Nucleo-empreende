#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
#   NUCLEO EMPREENDE — Publicar no GitHub
#   Uso: bash publicar_github.sh
# ══════════════════════════════════════════════════════════

set -e

AMBER='\033[38;5;214m'; GREEN='\033[38;5;82m'; RED='\033[38;5;196m'
CYAN='\033[38;5;51m'; GRAY='\033[38;5;244m'; BOLD='\033[1m'; R='\033[0m'

ok()   { echo -e "  ${GREEN}${BOLD}✓${R} $1"; }
err()  { echo -e "  ${RED}${BOLD}✗${R} $1"; exit 1; }
info() { echo -e "  ${GRAY}→${R} $1"; }
ask()  { echo -e "\n  ${AMBER}►${R} $1"; }

echo ""
echo -e "  ${AMBER}${BOLD}Nucleo Empreende — Publicar no GitHub${R}"
echo -e "  ${GRAY}══════════════════════════════════════${R}"
echo ""

# ── 1. Verificar git ──────────────────────────────────────
command -v git &>/dev/null || err "git não encontrado. Instale: sudo apt install git"
ok "git disponível"

# ── 2. Verificar gh (GitHub CLI) ─────────────────────────
if ! command -v gh &>/dev/null; then
  info "Instalando GitHub CLI..."
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update -qq && sudo apt install gh -y -qq
fi
ok "GitHub CLI disponível"

# ── 3. Login no GitHub ────────────────────────────────────
if ! gh auth status &>/dev/null; then
  echo ""
  echo -e "  ${CYAN}Fazendo login no GitHub...${R}"
  gh auth login
fi
ok "GitHub autenticado"

# ── 4. Coletar informações ────────────────────────────────
echo ""
ask "Nome do repositório no GitHub (ex: nucleo-empreende):"
read -r REPO_NAME
REPO_NAME="${REPO_NAME:-nucleo-empreende}"

ask "Repositório público ou privado? [publico/PRIVADO]:"
read -r VISIBILITY_INPUT
if [[ "${VISIBILITY_INPUT,,}" == "publico" ]]; then
  VISIBILITY="public"
else
  VISIBILITY="private"
fi

ask "Descrição do repositório:"
read -r REPO_DESC
REPO_DESC="${REPO_DESC:-Framework de Diretoria Autônoma de IA para Empresários}"

# ── 5. Garantir estrutura mínima ──────────────────────────
echo ""
info "Preparando estrutura do repositório..."

# .gitignore
cat > .gitignore << 'GITIGNORE'
# Sensível — NUNCA commitar
.env
*.env.local
nucleo/logs/licencas.jsonl

# Python
__pycache__/
*.py[cod]
*.pyo
venv/
.venv/
*.egg-info/
dist/
build/

# Playwright / Chromium
.playwright/

# Áudios gerados
nucleo/logs/audios/

# IDEs
.vscode/
.idea/
*.swp

# macOS
.DS_Store

# Logs (manter estrutura, ignorar conteúdo)
nucleo/logs/*.jsonl
!nucleo/logs/.gitkeep
GITIGNORE
ok ".gitignore criado"

# Manter pasta de logs no repo
mkdir -p nucleo/logs
touch nucleo/logs/.gitkeep

# ── 6. Inicializar git e commitar ─────────────────────────
info "Inicializando repositório..."
git init -b main &>/dev/null || git checkout -b main 2>/dev/null || true

git add -A
git commit -m "🚀 Nucleo Empreende v1.0.0 — release inicial

- 9 agentes com cargo, personalidade e memória
- 12 conectores de API (WhatsApp, Hotmart, Meta Ads, etc.)
- Setup Wizard interativo (CLI + Web)
- Instalador one-liner (curl | bash)
- FastAPI backend com WebSocket
- Dashboard de controle
- Documentação completa" &>/dev/null || true

ok "Commit criado"

# ── 7. Criar repositório no GitHub ───────────────────────
info "Criando repositório $REPO_NAME no GitHub..."

GH_USER=$(gh api user --jq .login)

# Tenta criar; se já existir, apenas faz push
if gh repo create "$REPO_NAME" \
    --"$VISIBILITY" \
    --description "$REPO_DESC" \
    --source=. \
    --remote=origin \
    --push 2>/dev/null; then
  ok "Repositório criado e publicado"
else
  info "Repositório já existe. Fazendo push..."
  git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git" 2>/dev/null || \
  git remote set-url origin "https://github.com/$GH_USER/$REPO_NAME.git"
  git push -u origin main --force
  ok "Push realizado"
fi

REPO_URL="https://github.com/$GH_USER/$REPO_NAME"

# ── 8. Configurar GitHub Pages (site de onboarding) ──────
info "Ativando GitHub Pages para o site de onboarding..."

# Mover site para /docs (convenção do GitHub Pages)
mkdir -p docs-site
cp -r nucleo_github/site/* docs-site/ 2>/dev/null || true
cp nucleo_github/site/onboarding.html docs-site/index.html 2>/dev/null || true

if [ -f "docs-site/index.html" ]; then
  git add docs-site/
  git commit -m "docs: adicionar site de onboarding para GitHub Pages" &>/dev/null || true
  git push origin main &>/dev/null || true

  # Ativar Pages via API
  gh api repos/$GH_USER/$REPO_NAME/pages \
    --method POST \
    --field source='{"branch":"main","path":"/docs-site"}' \
    &>/dev/null && ok "GitHub Pages ativado" || info "Ative manualmente: Settings → Pages → Branch: main → /docs-site"
fi

# ── 9. Adicionar topics/tags ──────────────────────────────
gh api repos/$GH_USER/$REPO_NAME/topics \
  --method PUT \
  --field names='["ai","agents","crewai","whatsapp","automation","python","fastapi","brazil"]' \
  &>/dev/null && ok "Topics adicionados" || true

# ── 10. Resultado final ───────────────────────────────────
echo ""
echo -e "  ${GREEN}${BOLD}════════════════════════════════════════${R}"
echo -e "  ${GREEN}${BOLD}  ✅  PUBLICADO NO GITHUB COM SUCESSO   ${R}"
echo -e "  ${GREEN}${BOLD}════════════════════════════════════════${R}"
echo ""
echo -e "  ${AMBER}Repositório:${R}  ${CYAN}$REPO_URL${R}"
echo -e "  ${AMBER}Visibilidade:${R} $VISIBILITY"
echo -e "  ${AMBER}README:${R}       $REPO_URL#readme"
echo -e "  ${AMBER}Docs:${R}         $REPO_URL/tree/main/nucleo_github/docs"
echo -e "  ${AMBER}Site onboard:${R} https://$GH_USER.github.io/$REPO_NAME"
echo ""
echo -e "  ${GRAY}GitHub Pages pode levar 1-2 minutos para ativar.${R}"
echo ""

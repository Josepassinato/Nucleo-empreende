#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#   NUCLEO EMPREENDE — Deploy Backend na VPS
#   Uso: bash deploy_vps.sh
# ══════════════════════════════════════════════════════════════
set -e

AMBER='\033[38;5;214m'; GREEN='\033[38;5;82m'; RED='\033[38;5;196m'
CYAN='\033[38;5;51m'; GRAY='\033[38;5;244m'; BOLD='\033[1m'; R='\033[0m'

ok()    { echo -e "  ${GREEN}${BOLD}✓${R}  $1"; }
err()   { echo -e "  ${RED}${BOLD}✗${R}  $1"; exit 1; }
info()  { echo -e "  ${GRAY}→${R}  $1"; }
title() { echo -e "\n  ${AMBER}${BOLD}$1${R}"; }
ask()   { echo -e "\n  ${AMBER}►${R} $1"; }

REPO="https://github.com/Josepassinato/Nucleo-empreende.git"
APP_DIR="$HOME/Nucleo-empreende"
SERVICE="nucleo-empreende"

clear
echo ""
echo -e "  ${AMBER}${BOLD}NUCLEO EMPREENDE — Deploy VPS${R}"
echo ""

# ── 1. SISTEMA
title "[1/7] Dependências do sistema"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv redis-server nginx certbot python3-certbot-nginx git curl
ok "Python, Redis, Nginx instalados"
systemctl enable redis-server --now && ok "Redis iniciado"

# ── 2. REPOSITÓRIO
title "[2/7] Clonar repositório"
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR" && git pull origin main
else
  git clone "$REPO" "$APP_DIR"
fi
ok "Repositório em $APP_DIR"
cd "$APP_DIR"

# ── 3. PYTHON
title "[3/7] Instalar dependências Python"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install "uvicorn[standard]" fastapi python-dotenv httpx twilio -q
ok "Dependências instaladas"

# ── 4. .ENV
title "[4/7] Configurar API Keys"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo -e "  ${CYAN}Configure as chaves (Enter para pular):${R}"
  echo ""
  ask "Nome da empresa:"; read -r V1
  ask "Seu nome (dono):"; read -r V2
  ask "Seu WhatsApp (+5511999999999):"; read -r V3
  ask "Google API Key:"; read -r V4
  ask "Groq API Key:"; read -r V5
  ask "Twilio Account SID:"; read -r V6
  ask "Twilio Auth Token:"; read -rs V7; echo ""
  ask "Twilio WhatsApp Number:"; read -r V8
  ask "Mercado Pago Access Token:"; read -rs V9; echo ""

  SECRET=$(openssl rand -hex 32)

  cat > .env << EOF
EMPRESA_NOME='${V1:-Minha Empresa}'
DONO_NOME='${V2:-Dono}'
DONO_WHATSAPP_NUMBER='${V3}'
NUCLEO_FASE='1'
NUCLEO_ENV='production'
SECRET_KEY='${SECRET}'
LIMITE_APROVACAO_REAIS='10000'
GOOGLE_API_KEY='${V4}'
GROQ_API_KEY='${V5}'
TWILIO_ACCOUNT_SID='${V6}'
TWILIO_AUTH_TOKEN='${V7}'
TWILIO_WHATSAPP_NUMBER='${V8}'
MERCADOPAGO_ACCESS_TOKEN='${V9}'
REDIS_URL='redis://localhost:6379'
META_ACCESS_TOKEN=''
PINECONE_API_KEY=''
SUPABASE_URL=''
SUPABASE_SERVICE_ROLE_KEY=''
HOTMART_CLIENT_ID=''
HOTMART_WEBHOOK_TOKEN=''
CLICKSIGN_ACCESS_TOKEN=''
ELEVENLABS_API_KEY=''
TELEGRAM_BOT_TOKEN=''
EOF
  chmod 600 .env
  ok ".env criado"
else
  ok ".env já existe — mantido"
fi

# ── 5. SYSTEMD
title "[5/7] Criar serviço systemd"
cat > /etc/systemd/system/${SERVICE}.service << EOF
[Unit]
Description=Nucleo Empreende Backend
After=network.target redis.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/uvicorn nucleo.api:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable ${SERVICE}
ok "Serviço systemd criado"

# ── 6. NGINX
title "[6/7] Configurar Nginx"
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
ask "Domínio (Enter para usar IP $IP):"; read -r DOMINIO
DOMINIO="${DOMINIO:-$IP}"

cat > /etc/nginx/sites-available/nucleo-empreende << EOF
server {
    listen 80;
    server_name ${DOMINIO};

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 60s;
    }
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }
}
EOF

ln -sf /etc/nginx/sites-available/nucleo-empreende /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
ok "Nginx configurado para $DOMINIO"

# HTTPS
if [[ "$DOMINIO" != "$IP" ]] && [[ "$DOMINIO" == *"."* ]]; then
  ask "Email para SSL (Let's Encrypt):"; read -r SSL_EMAIL
  if [ -n "$SSL_EMAIL" ]; then
    certbot --nginx -d "$DOMINIO" --email "$SSL_EMAIL" --agree-tos --non-interactive && ok "HTTPS ativado" || info "Certbot falhou — OK por enquanto"
  fi
fi

# ── 7. INICIAR
title "[7/7] Iniciar sistema"
systemctl start ${SERVICE}
sleep 4

if curl -s http://localhost:8000 | grep -qi "nucleo\|online" 2>/dev/null; then
  ok "Backend respondendo"
else
  info "Backend iniciando... aguarde alguns segundos"
fi

echo ""
echo -e "  ${GREEN}${BOLD}✅  DEPLOY CONCLUÍDO!${R}"
echo ""
echo -e "  ${AMBER}API:${R}              http://${DOMINIO}/api/v1/status"
echo -e "  ${AMBER}Dashboard API:${R}    http://${DOMINIO}/api/v1/dashboard"
echo ""
echo -e "  ${AMBER}Webhook WhatsApp → cole no Twilio:${R}"
echo -e "  ${CYAN}  http://${DOMINIO}/webhook/whatsapp${R}"
echo ""
echo -e "  ${AMBER}Webhook Hotmart → cole no painel:${R}"
echo -e "  ${CYAN}  http://${DOMINIO}/webhook/hotmart${R}"
echo ""
echo -e "  ${AMBER}Conectar Vercel ao backend:${R}"
echo -e "  ${GRAY}  Vercel → Settings → Environment Variables:${R}"
echo -e "  ${CYAN}  NEXT_PUBLIC_API_URL = http://${DOMINIO}${R}"
echo ""
echo -e "  ${GRAY}Logs:  journalctl -u ${SERVICE} -f${R}"
echo -e "  ${GRAY}Restart: systemctl restart ${SERVICE}${R}"
echo ""

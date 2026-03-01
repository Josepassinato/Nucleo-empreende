#!/usr/bin/env bash
# Fix Nginx — detecta IP automaticamente, sem input interativo
set -e

GREEN='\033[38;5;82m'; AMBER='\033[38;5;214m'; CYAN='\033[38;5;51m'; GRAY='\033[38;5;244m'; BOLD='\033[1m'; R='\033[0m'
ok()   { echo -e "  ${GREEN}${BOLD}✓${R}  $1"; }
info() { echo -e "  ${GRAY}→${R}  $1"; }

echo ""
echo -e "  ${AMBER}${BOLD}Nucleo Empreende — Fix Nginx${R}"
echo ""

# Detectar IP público real
IP=$(curl -s https://api.ipify.org 2>/dev/null \
  || curl -s https://ifconfig.me 2>/dev/null \
  || curl -s https://icanhazip.com 2>/dev/null \
  || hostname -I | awk '{print $1}')

echo -e "  IP público detectado: ${CYAN}$IP${R}"

# Verificar se foi passado domínio como argumento
DOMINIO="${1:-$IP}"
echo -e "  Usando: ${CYAN}$DOMINIO${R}"
echo ""

# Criar config Nginx com IP/domínio real
CONFIG_FILE="/etc/nginx/sites-available/nucleo-empreende"

cat > "$CONFIG_FILE" << NGINX
server {
    listen 80;
    server_name $DOMINIO;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
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
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
NGINX

ln -sf "$CONFIG_FILE" /etc/nginx/sites-enabled/nucleo-empreende
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
ok "Nginx configurado para: $DOMINIO"

# Reiniciar backend
systemctl restart nucleo-empreende 2>/dev/null || true
sleep 3

# Testar
HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null || echo "000")
if [ "$HTTP" = "200" ] || [ "$HTTP" = "404" ]; then
  ok "Backend respondendo (HTTP $HTTP)"
else
  info "Backend ainda iniciando... teste: curl http://localhost:8000"
fi

echo ""
echo -e "  ${GREEN}${BOLD}✅  NGINX CORRIGIDO!${R}"
echo ""
echo -e "  ${AMBER}Testar API:${R}"
echo -e "  ${CYAN}  curl http://$DOMINIO/api/v1/status${R}"
echo ""
echo -e "  ${AMBER}Webhook WhatsApp → cole no Twilio:${R}"
echo -e "  ${CYAN}  http://$DOMINIO/webhook/whatsapp${R}"
echo ""
echo -e "  ${AMBER}Webhook Hotmart → cole no painel:${R}"
echo -e "  ${CYAN}  http://$DOMINIO/webhook/hotmart${R}"
echo ""
echo -e "  ${AMBER}Vercel → Settings → Environment Variables:${R}"
echo -e "  ${CYAN}  NEXT_PUBLIC_API_URL = http://$DOMINIO${R}"
echo ""
echo -e "  ${GRAY}Logs: journalctl -u nucleo-empreende -f${R}"
echo ""

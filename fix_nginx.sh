#!/usr/bin/env bash
# Corrige o Nginx com o IP real da VPS
set -e

GREEN='\033[38;5;82m'; AMBER='\033[38;5;214m'; CYAN='\033[38;5;51m'; GRAY='\033[38;5;244m'; BOLD='\033[1m'; R='\033[0m'
ok()   { echo -e "  ${GREEN}${BOLD}✓${R}  $1"; }
info() { echo -e "  ${GRAY}→${R}  $1"; }

# Detectar IP público real
IP=$(curl -s https://api.ipify.org 2>/dev/null || curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo -e "  ${AMBER}${BOLD}Corrigindo configuração do Nginx${R}"
echo ""
echo -e "  IP detectado: ${CYAN}$IP${R}"
echo ""
echo -e "  ${AMBER}►${R} Tem domínio configurado? (ex: api.nucleoempreende.com.br)"
echo -e "  ${GRAY}  Enter para usar o IP: $IP${R}"
read -r DOMINIO
DOMINIO="${DOMINIO:-$IP}"

# Reescrever config do Nginx com IP/domínio correto
cat > /etc/nginx/sites-available/nucleo-empreende << NGINX
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

nginx -t && systemctl reload nginx
ok "Nginx corrigido para: $DOMINIO"

# Reiniciar backend
systemctl restart nucleo-empreende
sleep 3

# Testar
if curl -s http://localhost:8000 | grep -qi "nucleo\|online\|sistema" 2>/dev/null; then
  ok "Backend respondendo na porta 8000"
else
  info "Backend iniciando... teste em 10s: curl http://localhost:8000"
fi

echo ""
echo -e "  ${GREEN}${BOLD}✅  SISTEMA CORRIGIDO!${R}"
echo ""
echo -e "  ${AMBER}Teste agora:${R}"
echo -e "  ${CYAN}  curl http://$DOMINIO/api/v1/status${R}"
echo ""
echo -e "  ${AMBER}Webhook WhatsApp → cole no Twilio:${R}"
echo -e "  ${CYAN}  http://$DOMINIO/webhook/whatsapp${R}"
echo ""
echo -e "  ${AMBER}Webhook Hotmart → cole no painel:${R}"
echo -e "  ${CYAN}  http://$DOMINIO/webhook/hotmart${R}"
echo ""
echo -e "  ${AMBER}Logs em tempo real:${R}"
echo -e "  ${CYAN}  journalctl -u nucleo-empreende -f${R}"
echo ""

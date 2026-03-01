#!/usr/bin/env bash
# Corrige conflito de porta — muda para 8080
set -e

GREEN='\033[38;5;82m'; AMBER='\033[38;5;214m'; CYAN='\033[38;5;51m'; BOLD='\033[1m'; R='\033[0m'
ok() { echo -e "  ${GREEN}${BOLD}✓${R}  $1"; }

IP=$(curl -s https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')
PORTA="${1:-8080}"

echo ""
echo -e "  ${AMBER}${BOLD}Nucleo Empreende — Fix Porta${R}"
echo -e "  IP: ${CYAN}$IP${R} | Porta: ${CYAN}$PORTA${R}"
echo ""

# Verificar o que está na porta 80
echo -e "  Processos na porta 80:"
ss -tlnp | grep ':80 ' || echo "  (nenhum)"
echo ""

# Reconfigurar Nginx na porta escolhida
cat > /etc/nginx/sites-available/nucleo-empreende << NGINX
server {
    listen $PORTA;
    server_name $IP;

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

ln -sf /etc/nginx/sites-available/nucleo-empreende /etc/nginx/sites-enabled/nucleo-empreende
nginx -t && systemctl reload nginx
ok "Nginx na porta $PORTA"

# Garantir firewall aberto
ufw allow $PORTA/tcp 2>/dev/null && ok "Firewall liberado na porta $PORTA" || true

# Testar direto no backend
sleep 2
HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
ok "Backend porta 8000 respondendo (HTTP $HTTP)"

# Testar via Nginx
HTTP2=$(curl -s -o /dev/null -w "%{http_code}" http://$IP:$PORTA/ 2>/dev/null || echo "000")
ok "Nginx porta $PORTA respondendo (HTTP $HTTP2)"

echo ""
echo -e "  ${GREEN}${BOLD}✅  PRONTO!${R}"
echo ""
echo -e "  ${AMBER}Testar API (rode este comando):${R}"
echo -e "  ${CYAN}curl http://$IP:$PORTA/api/v1/status${R}"
echo ""
echo -e "  ${AMBER}Webhook WhatsApp → Twilio:${R}"
echo -e "  ${CYAN}http://$IP:$PORTA/webhook/whatsapp${R}"
echo ""
echo -e "  ${AMBER}Webhook Hotmart:${R}"
echo -e "  ${CYAN}http://$IP:$PORTA/webhook/hotmart${R}"
echo ""
echo -e "  ${AMBER}Vercel → Environment Variables:${R}"
echo -e "  ${CYAN}NEXT_PUBLIC_API_URL = http://$IP:$PORTA${R}"
echo ""

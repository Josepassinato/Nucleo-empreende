#!/bin/bash
# Libera acesso externo ao backend para Remote Control
IP=$(curl -s api.ipify.org 2>/dev/null || echo "76.13.109.151")

cat > /etc/nginx/sites-available/nucleo-empreende << NGINX
server {
    listen 8080;
    server_name $IP _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX

nginx -t && systemctl reload nginx && echo "✅ Nginx liberado"

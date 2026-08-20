#!/usr/bin/env bash
# Ensure nginx HTTPS vhost proxies /api/ to backend (required for login/register from browser).
set -euo pipefail

CONF="/etc/nginx/sites-enabled/indiagovjob"
if [[ ! -f "$CONF" ]] && [[ -f /etc/nginx/sites-enabled/default ]]; then
  CONF="/etc/nginx/sites-enabled/default"
fi

if [[ ! -f "$CONF" ]]; then
  echo "No nginx site config found. Copy deploy/nginx-indiagovjob-ssl.conf manually."
  exit 1
fi

if grep -q 'location /api/' "$CONF"; then
  echo "OK: nginx already has location /api/"
else
  echo "WARN: $CONF is missing 'location /api/' — browser login/register may fail."
  echo "Add the /api/ block from deploy/nginx-indiagovjob-ssl.conf inside your SSL server { } block."
  echo "Then: sudo nginx -t && sudo systemctl reload nginx"
  exit 1
fi

sudo nginx -t
sudo systemctl reload nginx
echo "Nginx reloaded."

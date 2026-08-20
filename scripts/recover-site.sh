#!/usr/bin/env bash
# Quick recovery when site shows 502/504 — run on VM.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Container status"
docker compose ps

echo ""
echo "==> Stop stuck one-off CLI containers"
docker ps -a --filter "name=jobalert-backend-run" -q | xargs -r docker rm -f

echo ""
echo "==> Restart stack"
docker compose up -d --force-recreate

echo ""
echo "==> Wait for backend (up to 2 min)"
for i in $(seq 1 24); do
  if curl -sf --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "Backend: OK"
    curl -s http://127.0.0.1:8000/health
    echo ""
    break
  fi
  sleep 5
done

echo ""
echo "==> Frontend check"
if curl -sf --max-time 10 -o /dev/null -w "Frontend HTTP %{http_code}\n" http://127.0.0.1:3000/; then
  true
else
  echo "Frontend not responding — logs:"
  docker compose logs frontend --tail=25
fi

echo ""
echo "==> Public health (via nginx)"
curl -sf --max-time 10 -o /dev/null -w "Site HTTPS %{http_code}\n" https://indiagovjob.online/ || echo "HTTPS check failed — reload nginx: sudo systemctl reload nginx"

docker compose ps

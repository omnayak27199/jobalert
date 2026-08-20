#!/usr/bin/env bash
# One-shot production deploy — run on VM after git clone or when broken.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Pull latest"
git pull origin main

echo "==> Fix .env"
bash "$ROOT/scripts/fix-env.sh"

echo "==> Rebuild backend (exclude .env from image)"
docker compose build --no-cache backend

echo "==> Start stack"
docker compose up -d --force-recreate

echo "==> Wait for health"
for i in $(seq 1 24); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "Backend healthy"
    curl -s http://127.0.0.1:8000/health
    echo ""
    docker compose ps
    exit 0
  fi
  sleep 5
done

echo "Backend not healthy — logs:"
docker compose logs backend --tail=40
exit 1

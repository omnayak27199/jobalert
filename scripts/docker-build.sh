#!/usr/bin/env bash
# Build Docker services with retries — frontend npm often flakes on small GCP VMs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FRESH=0
SERVICES=()

for arg in "$@"; do
  case "$arg" in
    --fresh | --no-cache)
      FRESH=1
      ;;
    *)
      SERVICES+=("$arg")
      ;;
  esac
done

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  SERVICES=(backend frontend)
fi

build_service() {
  local svc="$1"
  local max_attempts=5
  local attempt=1
  local -a flags=()

  if [[ "$FRESH" -eq 1 ]]; then
    flags=(--no-cache)
  fi

  while [[ "$attempt" -le "$max_attempts" ]]; do
    echo "==> docker compose build ${flags[*]:-} $svc (attempt $attempt/$max_attempts)"
    if docker compose build "${flags[@]}" "$svc"; then
      echo "==> $svc build OK"
      return 0
    fi

    if [[ "$svc" != "frontend" ]] || [[ "$attempt" -eq "$max_attempts" ]]; then
      echo "==> $svc build FAILED"
      return 1
    fi

    echo "Frontend npm install failed (network ECONNRESET is common on e2-micro). Retrying in 30s..."
    sleep 30
    attempt=$((attempt + 1))
  done
}

for svc in "${SERVICES[@]}"; do
  build_service "$svc"
done

echo "==> All requested images built."

#!/usr/bin/env bash
# Fix common backend/.env issues before docker compose up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
EXAMPLE="$ROOT/backend/.env.example"
DOCKER_ENV="$ROOT/backend/.env.docker"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$DOCKER_ENV" ]]; then
    cp "$DOCKER_ENV" "$ENV_FILE"
  elif [[ -f "$EXAMPLE" ]]; then
    cp "$EXAMPLE" "$ENV_FILE"
  fi
  echo "Created $ENV_FILE from template."
fi

if [[ -f "$ENV_FILE" ]]; then
  # Remove bad typo line entirely if present.
  if grep -q 'UBLIC_SITE_URL' "$ENV_FILE" 2>/dev/null; then
    sed -i '/^[[:space:]]*UBLIC_SITE_URL=/d' "$ENV_FILE"
    echo "Removed UBLIC_SITE_URL line from backend/.env"
  fi
  # Fix UBLIC_SITE_URL typo (missing P) if rename form exists.
  if grep -q '^UBLIC_SITE_URL=' "$ENV_FILE" 2>/dev/null; then
    sed -i 's/^UBLIC_SITE_URL=/PUBLIC_SITE_URL=/' "$ENV_FILE"
    sed -i 's/^[[:space:]]*UBLIC_SITE_URL=/PUBLIC_SITE_URL=/' "$ENV_FILE"
    echo "Fixed UBLIC_SITE_URL → PUBLIC_SITE_URL in backend/.env"
  fi
  # Ensure PUBLIC_SITE_URL exists for production.
  if ! grep -q '^PUBLIC_SITE_URL=' "$ENV_FILE" 2>/dev/null; then
    echo 'PUBLIC_SITE_URL=https://indiagovjob.online' >> "$ENV_FILE"
    echo "Added PUBLIC_SITE_URL to backend/.env"
  fi
  # Ensure admin email is configured for panel access.
  if ! grep -q '^ADMIN_EMAILS=' "$ENV_FILE" 2>/dev/null; then
    echo 'ADMIN_EMAILS=omnayak27199@gmail.com' >> "$ENV_FILE"
    echo "Added ADMIN_EMAILS to backend/.env"
  fi
fi

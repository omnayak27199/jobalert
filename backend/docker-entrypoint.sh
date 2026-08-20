#!/bin/sh
set -e

# Auto-fix common .env typo (UBLIC_SITE_URL missing leading P).
if [ -n "${UBLIC_SITE_URL:-}" ] && [ -z "${PUBLIC_SITE_URL:-}" ]; then
  export PUBLIC_SITE_URL="$UBLIC_SITE_URL"
fi
unset UBLIC_SITE_URL

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

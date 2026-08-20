#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting IndiaJob..."

# Backend
cd "$ROOT/backend"
mkdir -p data
if ! pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
  echo "Starting backend on http://0.0.0.0:8000"
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/jobalert-backend.log 2>&1 &
  sleep 3
else
  echo "Backend already running"
fi

# Frontend
cd "$ROOT/frontend"
if ! pgrep -f "next dev" > /dev/null 2>&1; then
  echo "Starting frontend on http://0.0.0.0:3000"
  nohup npm run dev -- -H 0.0.0.0 -p 3000 > /tmp/jobalert-frontend.log 2>&1 &
  sleep 5
else
  echo "Frontend already running - restarting with correct host..."
  pkill -f "next dev" || true
  sleep 2
  nohup npm run dev -- -H 0.0.0.0 -p 3000 > /tmp/jobalert-frontend.log 2>&1 &
  sleep 5
fi

echo ""
echo "============================================"
echo "  IndiaJob is running!"
echo "  Open in browser: http://localhost:3000"
echo ""
echo "  In Cursor: Open the 'Ports' tab and"
echo "  click the globe icon next to port 3000"
echo "============================================"
echo ""

curl -s -o /dev/null -w "Frontend: HTTP %{http_code}\n" http://localhost:3000 || echo "Frontend: starting..."
curl -s -o /dev/null -w "Backend:  HTTP %{http_code}\n" http://localhost:8000/health || echo "Backend: starting..."

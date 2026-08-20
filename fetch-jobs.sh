#!/usr/bin/env bash
# Manual fetch from all government portals
cd "$(dirname "$0")/backend"
python3 -m app.cli fetch "$@"

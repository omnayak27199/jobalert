#!/usr/bin/env bash
# Upload a PDF recruitment notification
# Usage: ./upload-pdf.sh /path/to/notification.pdf [--state "Uttar Pradesh"] [--org UPPSC]
cd "$(dirname "$0")/backend"
python3 -m app.cli upload "$@"

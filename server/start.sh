#!/bin/bash
# Amaravati Digital Twin — Server Start Script
# Kreayotoo Solutions (P) Ltd

cd "$(dirname "$0")"
echo "=================================================="
echo "  Amaravati Digital Twin — Backend Server"
echo "  Kreayotoo Solutions (P) Ltd"
echo "=================================================="

# Check if data is prepared
if [ ! -f "static/data/manifest.json" ]; then
  echo "Data not prepared. Running prepare_data.py first..."
  python3 prepare_data.py
fi

echo ""
echo "Starting server on http://0.0.0.0:8000"
echo "Monitor dashboard: http://localhost:8000"
echo "API docs:          http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info

#!/bin/bash
# run_web.sh
# Spins up the FastAPI backend ASGI server for the Insights Explorer

# Exit immediately if a command exits with a non-zero status
set -e

# Core directories definition
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "================================================================="
echo "🧠 Insights Explorer API Server Launcher"
echo "================================================================="

# 1. Activate Python virtual environment
if [ -d ".venv" ]; then
    echo "✔️ Activating local virtual environment (.venv)..."
    source .venv/bin/activate
else
    echo "❌ Error: Virtual environment (.venv) not found. Run standard python setup."
    exit 1
fi

# 2. Start Uvicorn ASGI Web Server
echo "🚀 Starting Uvicorn API Server on http://localhost:8000..."
echo "📁 API Swagger Docs are available at http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server."
echo "-----------------------------------------------------------------"

# Run uvicorn pointing to backend.app
PYTHONPATH=. uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload


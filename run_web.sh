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

# 2. Start Concurrent Servers
echo "🚀 Starting concurrent developer services..."

# Clean up trap to terminate all child processes on exit (Ctrl+C)
trap 'echo "🛑 Stopping services..."; kill $(jobs -p) 2>/dev/null' EXIT

# Start FastAPI Backend in background
echo "⚡ Starting FastAPI backend on http://127.0.0.1:8000..."
PYTHONPATH=. uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload &

# Start Vite React Frontend
echo "💻 Starting Vite React frontend..."
cd "$PROJECT_DIR"/frontend
/opt/homebrew/bin/npm run dev &

# Wait for all background jobs to finish
wait


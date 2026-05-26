#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get the absolute path of the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Print visual header
echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;36m       WhatsApp Ingestion & Scraping Pipeline Launcher     \033[0m"
echo -e "\033[1;36m============================================================\033[0m"

# 1. Detect and activate virtual environment
if [ ! -d ".venv" ]; then
    echo -e "\033[1;33m[!] Virtual environment (.venv) not found. Setting it up...\033[0m"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "\033[1;32m[+] Environment initialized successfully.\033[0m"
else
    source .venv/bin/activate
fi

# 2. Configure python path and execute the ingestion pipeline
echo -e "\033[1;32m[+] Executing the pipeline orchestrator...\033[0m"
PYTHONPATH=. python main.py run "$@"

echo -e "\033[1;36m============================================================\033[0m"

#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Get the absolute path of the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

if [ -z "$1" ]; then
    echo -e "\033[1;31m[!] Error: Please provide a search query.\033[0m"
    echo -e "Usage: ./search.sh \"<query_text>\" [--limit <n>] [--has-links <0|1>]"
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "\033[1;31m[!] Error: Virtual environment (.venv) not found. Please run ./run.sh first.\033[0m"
    exit 1
fi

# Execute the search query
PYTHONPATH=. python main.py search "$@"

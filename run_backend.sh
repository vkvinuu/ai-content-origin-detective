#!/usr/bin/env bash
# ==============================================================================
# Start AI Content-Origin Detective Backend (Linux / WSL)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# Detect Linux virtual environment
if [ -d ".venv_linux" ] && [ -f ".venv_linux/bin/activate" ]; then
    source ".venv_linux/bin/activate"
elif [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
else
    echo "❌ Linux virtual environment not found. Please run ./setup_linux.sh first."
    exit 1
fi

echo "=========================================================="
echo "🚀 Starting AI Content-Origin Detective Backend (FastAPI)"
echo "   URL: http://0.0.0.0:8000"
echo "   Docs: http://localhost:8000/docs"
echo "=========================================================="

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

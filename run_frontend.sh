#!/usr/bin/env bash
# ==============================================================================
# Start AI Content-Origin Detective Frontend (Linux / WSL)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/frontend"

echo "=========================================================="
echo "💻 Starting AI Content-Origin Detective Frontend (Next.js)"
echo "   Dashboard: http://localhost:3000"
echo "=========================================================="

npm run dev

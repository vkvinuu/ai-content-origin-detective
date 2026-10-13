#!/usr/bin/env bash
# ==============================================================================
# AI Content-Origin Detective - Linux & WSL Environment Setup Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo " Setting up AI Content-Origin Detective for Linux / WSL"
echo "=========================================================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    echo "   Please run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

# Check for Node.js & npm
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed."
    echo "   Please install Node.js (v18+) and npm."
    echo "   E.g., sudo apt install -y nodejs npm"
    exit 1
fi

echo "✅ System tools verified (python3, npm)."

# 1. Setup Backend Python Virtual Environment
echo ""
echo "📦 Setting up Python backend virtual environment..."
cd "$SCRIPT_DIR/backend"

# If in WSL or shared Windows filesystem, use .venv_linux to avoid collision with Windows .venv
VENV_DIR=".venv_linux"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at backend/$VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip and installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Ensure uploads and artifacts directories exist
mkdir -p uploads artifacts
echo "✅ Backend dependencies installed successfully."

# 2. Setup Frontend Next.js Dependencies
echo ""
echo "💻 Setting up Next.js frontend dependencies..."
cd "$SCRIPT_DIR/frontend"

npm install
echo "✅ Frontend packages installed successfully."

# 3. Mark scripts executable
chmod +x "$SCRIPT_DIR"/run_*.sh 2>/dev/null || true

echo ""
echo "=========================================================="
echo "🎉 Setup Complete! To start the project in WSL / Linux:"
echo ""
echo "  Option 1 (Run Both):    ./run_all.sh"
echo "  Option 2 (Terminal 1):  ./run_backend.sh"
echo "            (Terminal 2): ./run_frontend.sh"
echo ""
echo "  Web UI:      http://localhost:3000"
echo "  Backend API: http://localhost:8000/docs"
echo "=========================================================="

#!/usr/bin/env bash
# ==============================================================================
# Run Both Backend & Frontend in WSL / Linux
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "=========================================================="
echo " Starting AI Content-Origin Detective (Backend + Frontend)"
echo "=========================================================="

"$SCRIPT_DIR/run_backend.sh" &
BACKEND_PID=$!

sleep 2

"$SCRIPT_DIR/run_frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "🚀 Services are running!"
echo "   Frontend Web UI: http://localhost:3000"
echo "   Backend REST API: http://localhost:8000/docs"
echo "   (Press Ctrl+C to stop both)"
echo ""

wait

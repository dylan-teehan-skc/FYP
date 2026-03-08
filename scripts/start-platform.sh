#!/bin/bash
# Start the platform stack: dashboard (3000), collector (9000), and MCP servers (8001-8006).
# Run from anywhere — paths are relative to this script.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORTS="8001,8002,8003,8004,8005,8006,9000,3000"

# Kill anything already on our ports
stale=$(lsof -ti :$PORTS 2>/dev/null || true)
if [ -n "$stale" ]; then
    echo "Killing stale processes on ports $PORTS..."
    echo "$stale" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

cleanup() {
    echo ""
    echo "Shutting down all services..."
    kill 0 2>/dev/null
    wait 2>/dev/null
    echo "All services stopped."
}
trap cleanup EXIT INT TERM

# --- MCP servers (ports 8001-8006) ---
echo "Starting MCP servers (8001-8006)..."
cd "$ROOT/demo/fulfillment"
PYTHONPATH=. .venv/bin/python3 -m mcp_server.main &
PYTHONPATH=. .venv/bin/python3 -m payments_server.main &
PYTHONPATH=. .venv/bin/python3 -m notifications_server.main &
PYTHONPATH=. .venv/bin/python3 -m risk_server.main &
PYTHONPATH=. .venv/bin/python3 -m promotions_server.main &
PYTHONPATH=. .venv/bin/python3 -m inventory_server.main &

# --- Collector API (port 9000) ---
echo "Starting collector (9000)..."
cd "$ROOT/platform/collector"
.venv/bin/python3 -c "from collector.app import run; run()" &

# --- Dashboard (port 3000) ---
echo "Starting dashboard (3000)..."
cd "$ROOT/dashboard"
npm run dev &

echo ""
echo "=== Platform running ==="
echo "  Dashboard:   http://localhost:3000"
echo "  Collector:   http://localhost:9000"
echo "  MCP servers: http://localhost:8001-8006"
echo ""
echo "Press Ctrl+C to stop everything."
wait

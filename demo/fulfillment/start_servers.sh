#!/bin/bash
# Start all 6 MCP servers for the fulfillment demo.
# Run from the demo/fulfillment/ directory.

set -e

cd "$(dirname "$0")"

echo "Starting MCP servers..."
PYTHONPATH=. python -m mcp_server.main &
PYTHONPATH=. python -m payments_server.main &
PYTHONPATH=. python -m notifications_server.main &
PYTHONPATH=. python -m risk_server.main &
PYTHONPATH=. python -m promotions_server.main &
PYTHONPATH=. python -m inventory_server.main &

echo "All servers starting on ports 8001-8006"
echo "Press Ctrl+C to stop all servers"
wait

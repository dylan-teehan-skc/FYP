#!/bin/bash
# Run the demo scenarios then the analysis pipeline.
# Usage: bash scripts/run-demo.sh --rounds 3

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROUNDS=1

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rounds) ROUNDS="$2"; shift 2 ;;
        *) echo "Usage: $0 [--rounds N]"; exit 1 ;;
    esac
done

echo "=== Running demo ($ROUNDS round(s)) ==="
cd "$ROOT/demo/fulfillment"
PYTHONPATH=. .venv/bin/python3 runner/demo_runner.py --rounds "$ROUNDS"

echo ""
echo "=== Running analysis pipeline ==="
cd "$ROOT/platform/analysis"
.venv/bin/python3 -m analysis.pipeline

echo ""
echo "=== Done ==="

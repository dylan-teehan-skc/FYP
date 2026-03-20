#!/bin/bash
# Run demo scenarios with frequent analysis so guided mode activates quickly.
# Each round runs 1 scenario batch, then analysis, then repeats.
# Usage: bash scripts/run-demo.sh --rounds 8 --types fulfilment,exchange --batch 5

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROUNDS=1
TYPES=""
BATCH=5

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rounds) ROUNDS="$2"; shift 2 ;;
        -t|--types) TYPES="$2"; shift 2 ;;
        -b|--batch) BATCH="$2"; shift 2 ;;
        *) echo "Usage: $0 [--rounds N] [--types type1,type2] [--batch N]"; exit 1 ;;
    esac
done

TYPES_ARG=""
if [[ -n "$TYPES" ]]; then
    TYPES_ARG="--types $TYPES"
fi

TOTAL=0
for i in $(seq 1 "$ROUNDS"); do
    echo ""
    echo "=== Batch $i/$ROUNDS (scenarios per batch: $BATCH) ==="

    # Run a small batch of scenarios
    cd "$ROOT/demo/fulfillment"
    PYTHONPATH=. .venv/bin/python3 runner/demo_runner.py --rounds 1 $TYPES_ARG

    TOTAL=$((TOTAL + BATCH))

    # Run analysis after every batch so optimal paths update
    echo ""
    echo "=== Analysis pipeline (after batch $i, ~$TOTAL scenarios total) ==="
    cd "$ROOT/platform/analysis"
    .venv/bin/python3 -m analysis.pipeline
done

echo ""
echo "=== Done ($ROUNDS batches, ~$TOTAL scenarios) ==="

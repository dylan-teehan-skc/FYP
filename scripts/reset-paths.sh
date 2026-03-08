#!/bin/bash
# Clear only optimal_paths table (keeps traces/embeddings, forces re-analysis).

set -e

docker exec workflow-db psql -U collector workflow_optimizer \
  -c "TRUNCATE optimal_paths CASCADE;"

echo "Optimal paths cleared."

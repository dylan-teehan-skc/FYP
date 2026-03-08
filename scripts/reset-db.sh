#!/bin/bash
# Clear all data from the platform database (event_logs, workflow_embeddings, optimal_paths).

set -e

docker exec workflow-db psql -U collector workflow_optimizer \
  -c "TRUNCATE event_logs, workflow_embeddings, optimal_paths CASCADE;"

echo "Database cleared."

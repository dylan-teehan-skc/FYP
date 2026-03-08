#!/usr/bin/env bash
# Delete all guided workflow executions from the database.
set -euo pipefail

DB_URL="${DATABASE_URL:-postgresql://collector:collector_dev@localhost:5432/workflow_optimizer}"

echo "Finding guided workflows..."
COUNT=$(psql "$DB_URL" -tAc "
    SELECT COUNT(DISTINCT workflow_id)
    FROM event_logs
    WHERE activity = 'optimize:guided'
")

if [ "$COUNT" -eq 0 ]; then
    echo "No guided workflows found."
    exit 0
fi

echo "Found $COUNT guided workflow(s). Deleting..."

psql "$DB_URL" -c "
    DELETE FROM workflow_embeddings
    WHERE workflow_id IN (
        SELECT DISTINCT workflow_id
        FROM event_logs
        WHERE activity = 'optimize:guided'
    );

    DELETE FROM event_logs
    WHERE workflow_id IN (
        SELECT DISTINCT workflow_id
        FROM event_logs
        WHERE activity = 'optimize:guided'
    );
"

echo "Deleted $COUNT guided workflow(s) and their events."

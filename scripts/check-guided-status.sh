#!/bin/bash
# Check how close each workflow type is to guided mode activation.
# Usage: bash scripts/check-guided-status.sh

DB_CONTAINER="workflow-db"
DB_USER="collector"
DB_NAME="workflow_optimizer"
MIN_EXECUTIONS=30

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
-- Current optimal paths
SELECT '=== OPTIMAL PATHS ===' AS info;
SELECT task_cluster, execution_count,
       ROUND(success_rate::numeric, 2) AS success_rate,
       CASE WHEN execution_count >= $MIN_EXECUTIONS THEN 'GUIDED READY'
            ELSE 'NEED ' || ($MIN_EXECUTIONS - execution_count) || ' MORE'
       END AS status
FROM optimal_paths
ORDER BY task_cluster;

-- Workflow counts by type
SELECT '=== RUNS BY TYPE ===' AS info;
SELECT
    CASE
        WHEN we.task_description ILIKE '%exchange%' THEN 'exchange'
        WHEN we.task_description ILIKE '%return%' THEN 'return'
        WHEN we.task_description ILIKE '%fulfil%' OR we.task_description ILIKE '%fulfill%' THEN 'fulfilment'
        ELSE 'other'
    END AS workflow_type,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE e.activity = 'workflow:complete') AS successes,
    COUNT(*) FILTER (WHERE e.activity = 'workflow:fail') AS failures
FROM workflow_embeddings we
JOIN event_logs e ON e.workflow_id = we.workflow_id
    AND e.activity IN ('workflow:complete', 'workflow:fail')
GROUP BY 1
ORDER BY 1;

-- Mode breakdown
SELECT '=== MODE BREAKDOWN ===' AS info;
SELECT REPLACE(activity, 'optimize:', '') AS mode, COUNT(*) AS count
FROM event_logs
WHERE activity IN ('optimize:guided', 'optimize:exploration')
GROUP BY 1;
"

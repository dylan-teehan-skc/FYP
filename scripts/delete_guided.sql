-- Delete all guided workflow executions from the database.
-- A workflow is "guided" if it has an optimize:guided event.

BEGIN;

-- Delete events for guided workflows
DELETE FROM event_logs
WHERE workflow_id IN (
    SELECT DISTINCT workflow_id
    FROM event_logs
    WHERE activity = 'optimize:guided'
);

-- Delete embeddings for guided workflows
DELETE FROM workflow_embeddings
WHERE workflow_id IN (
    SELECT DISTINCT workflow_id
    FROM event_logs
    WHERE activity = 'optimize:guided'
);

COMMIT;

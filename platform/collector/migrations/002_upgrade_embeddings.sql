-- Upgrade embedding columns from 768 to 1536 dimensions.
-- text-embedding-3-small natively produces 1536-dim vectors; the original
-- 768-dim truncation lost semantic precision with no storage benefit at
-- our scale (hundreds of workflows, not millions).
--
-- Existing 768-dim embeddings are incompatible with 1536-dim columns,
-- so we clear them — the collector will regenerate on next workflow ingest.

ALTER TABLE workflow_embeddings ALTER COLUMN embedding TYPE VECTOR(1536);
ALTER TABLE optimal_paths ALTER COLUMN embedding TYPE VECTOR(1536);

-- Recreate HNSW indexes for new dimension
DROP INDEX IF EXISTS idx_workflow_embeddings_embedding;
CREATE INDEX idx_workflow_embeddings_embedding
    ON workflow_embeddings USING hnsw (embedding vector_cosine_ops);

DROP INDEX IF EXISTS idx_optimal_paths_embedding;
CREATE INDEX idx_optimal_paths_embedding
    ON optimal_paths USING hnsw (embedding vector_cosine_ops);

-- Clear old 768-dim embeddings (incompatible with new 1536-dim)
UPDATE workflow_embeddings SET embedding = NULL;
UPDATE optimal_paths SET embedding = NULL;

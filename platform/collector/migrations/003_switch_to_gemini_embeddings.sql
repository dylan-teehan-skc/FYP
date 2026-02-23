-- Switch embedding model from OpenAI text-embedding-3-small (1536-dim) to
-- Gemini gemini-embedding-001 (768-dim via dimensions=768) to avoid requiring
-- a separate OpenAI API key when the rest of the platform uses Gemini.
--
-- NOTE: This is a pragmatic choice for the demo. OpenAI's text-embedding-3-small
-- (1536-dim) is preferred for production — higher dimensionality captures more
-- semantic nuance. If an OpenAI key becomes available, revert to 1536-dim by
-- changing the embedding_model config and running a reverse migration.
--
-- Existing embeddings are incompatible with the new dimension, so we clear them.

ALTER TABLE workflow_embeddings ALTER COLUMN embedding TYPE VECTOR(768);
ALTER TABLE optimal_paths ALTER COLUMN embedding TYPE VECTOR(768);

-- Recreate HNSW indexes for new dimension
DROP INDEX IF EXISTS idx_workflow_embeddings_embedding;
CREATE INDEX idx_workflow_embeddings_embedding
    ON workflow_embeddings USING hnsw (embedding vector_cosine_ops);

DROP INDEX IF EXISTS idx_optimal_paths_embedding;
CREATE INDEX idx_optimal_paths_embedding
    ON optimal_paths USING hnsw (embedding vector_cosine_ops);

-- Clear old 1536-dim embeddings (incompatible with new 768-dim)
UPDATE workflow_embeddings SET embedding = NULL;
UPDATE optimal_paths SET embedding = NULL;

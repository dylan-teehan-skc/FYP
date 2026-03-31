ALTER TABLE optimal_paths
    ADD COLUMN IF NOT EXISTS failure_warnings JSONB NOT NULL DEFAULT '[]';

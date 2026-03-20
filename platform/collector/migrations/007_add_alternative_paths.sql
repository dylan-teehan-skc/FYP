ALTER TABLE optimal_paths
    ADD COLUMN IF NOT EXISTS alternative_paths JSONB NOT NULL DEFAULT '[]';

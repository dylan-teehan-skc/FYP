-- Add decision_tree column: auto-generated branching logic from subcluster analysis.
ALTER TABLE optimal_paths ADD COLUMN IF NOT EXISTS decision_tree JSONB DEFAULT NULL;

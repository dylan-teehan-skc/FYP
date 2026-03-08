-- Add guided vs exploration success rate tracking for automatic regression detection.
-- When guided mode performs worse than exploration, the collector falls back to exploration.

ALTER TABLE optimal_paths
    ADD COLUMN IF NOT EXISTS guided_success_rate    DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS exploration_success_rate DOUBLE PRECISION;

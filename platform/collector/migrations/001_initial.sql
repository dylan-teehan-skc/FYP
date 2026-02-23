-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Event logs table (stores every WorkflowEvent from the SDK)
CREATE TABLE IF NOT EXISTS event_logs (
    event_id            UUID PRIMARY KEY,
    workflow_id         UUID NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activity            VARCHAR(255) NOT NULL,

    -- Multi-agent tracking
    agent_name          VARCHAR(100) NOT NULL DEFAULT '',
    agent_role          VARCHAR(50) NOT NULL DEFAULT '',

    -- Tool call details
    tool_name           VARCHAR(100),
    tool_parameters     JSONB NOT NULL DEFAULT '{}',
    tool_response       JSONB NOT NULL DEFAULT '{}',

    -- LLM metrics
    llm_model               VARCHAR(50) NOT NULL DEFAULT '',
    llm_prompt_tokens       INTEGER NOT NULL DEFAULT 0,
    llm_completion_tokens   INTEGER NOT NULL DEFAULT 0,
    llm_reasoning           TEXT NOT NULL DEFAULT '',

    -- Performance metrics
    duration_ms         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cost_usd            DECIMAL(10, 6) NOT NULL DEFAULT 0.0,

    -- Outcome
    status              VARCHAR(20) NOT NULL DEFAULT 'success',
    error_message       TEXT,

    -- Workflow context
    step_number         INTEGER NOT NULL DEFAULT 0,
    parent_event_id     UUID REFERENCES event_logs(event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_logs_workflow_id ON event_logs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp ON event_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_logs_activity ON event_logs(activity);
CREATE INDEX IF NOT EXISTS idx_event_logs_agent_name ON event_logs(agent_name);

-- Workflow embeddings table (pgvector for semantic search)
CREATE TABLE IF NOT EXISTS workflow_embeddings (
    workflow_id         UUID PRIMARY KEY,
    task_description    TEXT NOT NULL,
    embedding           VECTOR(1536),
    model_version       VARCHAR(100) NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_embeddings_embedding
    ON workflow_embeddings USING hnsw (embedding vector_cosine_ops);

-- Optimal paths table (discovered best sequences)
CREATE TABLE IF NOT EXISTS optimal_paths (
    path_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_cluster        TEXT NOT NULL,
    tool_sequence       JSONB NOT NULL DEFAULT '[]',
    avg_duration_ms     DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    avg_steps           DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    success_rate        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    execution_count     INTEGER NOT NULL DEFAULT 0,
    embedding           VECTOR(1536),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_optimal_paths_embedding
    ON optimal_paths USING hnsw (embedding vector_cosine_ops);

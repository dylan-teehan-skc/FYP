# External Integrations

**Analysis Date:** 2026-03-13

## APIs & External Services

**LLM Providers (via LiteLLM):**
- Google Gemini - Embedding generation and reasoning
  - SDK/Client: LiteLLM (`import litellm`)
  - Auth: `GOOGLE_API_KEY` environment variable
  - Usage: `gemini/gemini-embedding-001` (embeddings), `gemini/gemini-2.5-flash-lite` (analysis reasoning)
  - Called from: `platform/collector/src/collector/embeddings.py`, `platform/analysis` pipeline

- Supports OpenAI, Anthropic (via LiteLLM abstraction) - Demos use LiteLLM for multi-provider support
  - SDK/Client: LiteLLM
  - Usage: Agent reasoning in `demo/agent-runtime`, `demo/fulfillment`, `demo/langchain`

**MCP (Model Context Protocol):**
- Internal tool server integration
  - SDK/Client: Custom HTTP client in `demo/agent-runtime/mcp/client.py` and `demo/langchain`
  - Protocol: HTTP/REST to MCP tool server
  - Usage: Agents retrieve tools from centralized MCP server
  - Server: `demo/mcp-tool-server` (FastAPI-based tool registry)

## Data Storage

**Databases:**
- PostgreSQL 16+ with pgvector extension
  - Connection: `DATABASE_URL` env var (default: `postgresql://collector:collector_dev@localhost:5432/workflow_optimizer`)
  - Client: asyncpg 0.29+ (async driver)
  - ORM: None - raw SQL queries with asyncpg
  - Pools: Configurable min/max (default 2/10) via `DATABASE_POOL_MIN`, `DATABASE_POOL_MAX`
  - Location: `platform/collector/src/collector/database.py`, `platform/analysis/src/analysis/database.py`

**Vector Storage:**
- pgvector extension (in PostgreSQL)
  - Tables: `workflow_embeddings` (768-dim vectors), `optimal_paths` (embeddings for path similarity)
  - Indexes: HNSW (Hierarchical Navigable Small World) for cosine similarity
  - Usage: Semantic clustering of workflows, optimal path discovery
  - Model: Gemini 768-dimensional embeddings

**File Storage:**
- Local filesystem only
  - SQLite used in fulfillment demo for demo data (`demo/fulfillment`)
  - No cloud storage integration

**Caching:**
- None (architecture relies on PostgreSQL for all persistence)

## Authentication & Identity

**Auth Provider:**
- Custom implementation (none for service-to-service)
  - Agent demos use `GOOGLE_API_KEY` for Gemini access
  - Dashboard has no auth layer (local dev only)
  - Services communicate via HTTP without authentication

**CORS:**
- Collector service configured for `http://localhost:3000` (dashboard)
  - Location: `platform/collector/src/collector/app.py`
  - Methods: All allowed
  - Headers: All allowed

## Monitoring & Observability

**Error Tracking:**
- None (not integrated)

**Logging:**
- structlog for structured logging across all services
  - Location: `platform/collector/src/collector/logger.py`, `platform/analysis/src/analysis/logger.py`
  - Output: STDOUT with structured fields
  - Level configurable via `LOG_LEVEL` env var
  - Services: collector, analysis, agent-runtime, demos

**Metrics:**
- LLM token tracking (LiteLLM integration)
  - Captured: Prompt tokens, completion tokens per LLM call
  - Storage: event_logs table (columns: llm_prompt_tokens, llm_completion_tokens)
  - Usage: Cost calculation, performance analysis

## CI/CD & Deployment

**Hosting:**
- Not configured (local development only)
- Docker support available via docker-compose.yml (PostgreSQL only)

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, etc.)

**Deployment:**
- Manual - services run via `uvicorn` for backend, `next start` for dashboard
- Start script: `scripts/start-platform.sh` (orchestrates startup)

## Environment Configuration

**Required env vars (Collector):**
- `DATABASE_URL` - PostgreSQL connection
- `EMBEDDING_MODEL` - Gemini embedding model
- `LOG_LEVEL` - Logging verbosity
- `SIMILARITY_THRESHOLD` - Workflow clustering sensitivity
- `MIN_EXECUTIONS` - Min workflow runs before optimization

**Required env vars (Analysis):**
- `DATABASE_URL` - PostgreSQL connection
- `EMBEDDING_MODEL` - Gemini embedding model
- `LLM_MODEL` - Gemini reasoning model
- `LOG_LEVEL` - Logging verbosity
- Analysis tuning: `SIMILARITY_THRESHOLD`, `MIN_SUCCESS_RATE`, `BOTTLENECK_THRESHOLD_PCT`

**Required env vars (Demos):**
- `GOOGLE_API_KEY` - Gemini API access for agents and analysis

**Secrets Location:**
- `.env` files (git-ignored, not committed)
- Environment variables passed at runtime
- `demo/langchain` sets `GOOGLE_API_KEY` in test setup

## Webhooks & Callbacks

**Incoming:**
- POST `/events` - Single workflow event submission (SDK)
- POST `/events/batch` - Batch event submission (SDK)
- POST `/optimize/path` - Semantic path lookup (SDK)
- POST `/run-analysis` - Trigger analysis pipeline
- WebSocket `/ws` - Real-time event streaming

**Outgoing:**
- None (platform is read/write only, no external push)

**SDK Tracing Callbacks:**
- Agents report workflow steps to collector via `workflow-optimizer-sdk`
- `demo/langchain` integrates callback handler for LangChain tracing
- Location: `demo/langchain/callback.py` (custom LangChain callback)

## SDK Communication

**Workflow Optimizer SDK:**
- Location: `sdk/src/workflow_optimizer/`
- Clients: aiohttp-based HTTP transport
- Protocol: JSON over HTTP
- Endpoints:
  - `POST /events` - Individual event
  - `POST /events/batch` - Batch of events
  - `GET /optimize/path` - Retrieve optimal path
- Batching: Configurable batch size (default 50) and flush interval (default 5s)
- Retry: Configurable max retries (default 3) with exponential backoff

## Data Flow Integration Points

1. **Agent → SDK → Collector**
   - Agents call `WorkflowOptimizer.trace()` context manager
   - SDK buffers events and flushes to collector via HTTP batching
   - Collector stores in PostgreSQL event_logs

2. **Collector → Analysis**
   - Collector triggers analysis via subprocess or direct import
   - Analysis reads event_logs, computes workflows, discovers paths
   - Writes optimal_paths back to PostgreSQL

3. **Collector/Analysis → LLM**
   - Embedding generation: Collector calls `litellm.aembedding()`
   - Analysis reasoning: Calls `litellm.completion()` for insights
   - All via LiteLLM abstraction (configurable provider)

4. **Dashboard → Collector**
   - Fetches workflow analytics via `/analytics` endpoints
   - Real-time updates via WebSocket `/ws`
   - CORS enabled for localhost:3000

---

*Integration audit: 2026-03-13*

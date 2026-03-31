# Concerns & Integrations

**Updated:** 2026-03-31

## Known Limitations

**PM4Py is CPU-bound** — process discovery and fitness computation block the async loop. Large traces (1000+ events) cause stalls. Could move to `asyncio.to_thread()` but hasn't been a problem at current scale.

**No data retention** — event_logs table grows forever. No cleanup, no partitioning. Fine for a demo/FYP but would need time-based partitioning for production.

**Bare exception catches** — a few `except Exception` blocks in websocket broadcast, embedding generation, and graph building. They log and continue, which is fine for resilience but makes debugging harder.

## External Dependencies

**Gemini API** — embedding generation (`gemini-embedding-001`) and LLM reasoning (`gemini-2.5-flash-lite`) go through LiteLLM. If Gemini is down, new workflows can't cluster and analysis can't name clusters. System degrades to exploration-only mode. Embedding model is configurable via env var.

**PostgreSQL + pgvector** — all persistence. Connection pool defaults: min=2, max=10. HNSW index on embedding columns for cosine similarity. Migrations in `platform/collector/migrations/` (001-006).

**PM4Py** — Inductive Miner for process model discovery. Pinned in pyproject.toml. Falls back gracefully if discovery fails on edge cases.

## Integration Points

1. **Agent → SDK → Collector** — SDK buffers events, flushes via HTTP batch to `/events/batch`. Collector stores in `event_logs`, broadcasts via WebSocket.
2. **SDK → Collector → Agent** — agent requests optimal path via `/optimize/path`. Collector does pgvector cosine search, returns guided mode (with tool sequence, confidence, decision tree, failure warnings) or exploration mode.
3. **Collector → Analysis** — triggered via `/actions/run-analysis` or from demo_runner after each round. Analysis reads event_logs, writes optimal_paths back.
4. **Dashboard → Collector** — REST endpoints for analytics + WebSocket `/ws` for live trace updates.

## Environment Variables

```
DATABASE_URL          # PostgreSQL connection (default: localhost:5432/workflow_optimizer)
EMBEDDING_MODEL       # LiteLLM model string (default: gemini/gemini-embedding-001)
LLM_MODEL             # For analysis reasoning (default: gemini/gemini-2.5-flash-lite)
GOOGLE_API_KEY        # Gemini API access
SIMILARITY_THRESHOLD  # Clustering sensitivity
MIN_EXECUTIONS        # Min runs before serving guided mode
LOG_LEVEL             # structlog level
```

## What Could Break

**Event schema changes** — `EventIn` has ~34 fields. Any change needs migration across SDK and collector. No schema versioning yet.

**Embedding dimension change** — currently 768-dim from Gemini. Switching models means re-embedding everything. pgvector HNSW index is dimension-specific.

**Database type coercion** — UUIDs and vectors are coerced to strings for asyncpg parameter passing. Works but fragile if upstream types change.

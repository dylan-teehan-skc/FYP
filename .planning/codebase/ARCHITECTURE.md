# Architecture

**Analysis Date:** 2026-03-13

## Pattern Overview

**Overall:** Three-tier decoupled microservices architecture with async event streaming.

**Key Characteristics:**
- Event-driven: SDK emits trace events to collector; no feedback loop until analysis completes
- Semantic clustering: embeddings-based task similarity using pgvector
- Multi-stage pipeline: trace reconstruction → process discovery → pattern detection → Pareto optimization
- Framework-agnostic SDK: zero-change instrumentation via context managers and transparent proxies
- Real-time WebSocket streaming for live trace visualization

## Layers

**SDK Layer:**
- Purpose: Lightweight client library for agent frameworks to instrument workflows
- Location: `sdk/src/workflow_optimizer/`
- Contains: Client, trace contexts, event models, HTTP transport
- Depends on: aiohttp, Pydantic v2
- Used by: All demos and customer integrations

**Collector/Ingestion Layer:**
- Purpose: FastAPI service that receives events, stores in PostgreSQL, and serves queries
- Location: `platform/collector/src/collector/`
- Contains: HTTP routes (events, workflows, optimize, analytics, dashboard), database layer, WebSocket connection manager
- Depends on: FastAPI, asyncpg, pgvector, LiteLLM for embeddings
- Used by: Dashboard, analysis engine, SDK clients

**Analysis Engine:**
- Purpose: Offline batch processing that discovers optimal execution paths from trace data
- Location: `platform/analysis/src/analysis/`
- Contains: Trace reconstruction, process mining (PM4Py), clustering, graph building, pattern detection, Pareto optimization
- Depends on: PM4Py, networkx, pandas, scipy, asyncpg
- Used by: Collector (updates optimal_paths table), dashboard (visualization data)

**Demo/Consumer Layer:**
- Purpose: Example frameworks showing how to integrate the SDK
- Locations:
  - `demo/agent-runtime/` — custom async Python agent with reasoning engine
  - `demo/langchain/` — LangChain/LangGraph integration with callback handlers
  - `demo/fulfillment/` — multi-server fulfillment scenario
  - `demo/mcp-tool-server/` — FastAPI mock tools (13 customer support tools)
- Contains: Agent logic, tool clients, orchestrators, reasoning engines
- Depends on: SDK, LLM clients (LiteLLM, Gemini), MCP

**Dashboard/Visualization:**
- Purpose: React/Next.js frontend for exploring workflows, optimal paths, and analytics
- Location: `dashboard/src/`
- Contains: Pages (traces, clusters, graph, insights), components, API client library
- Depends on: Next.js, React, react-flow, recharts, Tailwind CSS
- Used by: End users for observability and optimization insights

## Data Flow

**Trace Capture & Storage:**

1. Agent framework (or SDK user) calls `optimizer.trace()` context manager
2. For each tool invocation, framework enters `trace.step()` context
3. On step exit, `StepContext` creates `WorkflowEvent` with timing, parameters, response
4. `HttpTransport` batches events (up to 50 or 5s flush interval) and POSTs to `/events/batch`
5. Collector's `/events/batch` endpoint inserts events into `event_logs` table
6. WebSocket broadcasts serialized events to dashboard subscribers

**Optimization Path Lookup:**

1. Agent calls `optimizer.get_optimal_path(task_description)` before execution
2. Collector's `/optimize/path` endpoint receives task description
3. `EmbeddingService` generates embedding for task (Gemini by default)
4. pgvector performs cosine similarity search on `optimal_paths` table
5. If similarity >= threshold (0.60) and execution count >= min_executions:
   - Return guided mode with tool_sequence, confidence, avg_duration_ms, success_rate
6. Else: Return exploration mode (agent runs freely)
7. Collector checks regression detection (guided vs exploration success rates)

**Analysis Pipeline (Batch):**

1. `analysis.pipeline.run_analysis_for_cluster()` selects task clusters with sufficient trace volume
2. For each cluster:
   - Reconstruct full traces from event_logs (chain events by workflow_id)
   - Discover process model via PM4Py Inductive Miner (successful traces only)
   - Compute quality metrics: fitness, precision via token-based replay
   - Build networkx DAG with tools as nodes, transitions as weighted edges
   - Detect patterns: error sequences, branching patterns, deviations from model
   - Find Pareto-optimal paths: multi-objective optimization on duration, cost, success rate
   - Select knee point (best cost-complexity tradeoff) as primary optimal path
3. Upsert results into `optimal_paths` table (embedding stored for semantic search)
4. Dashboard refreshes with new insights

## Key Abstractions

**TraceContext:**
- Purpose: Async context manager that wraps one complete workflow execution
- Examples: `sdk/src/workflow_optimizer/trace.py` (TraceContext class)
- Pattern: Creates workflow_id on enter, collects step events, flushes to transport on exit

**StepContext:**
- Purpose: Sync context manager for a single tool invocation
- Examples: `sdk/src/workflow_optimizer/trace.py` (StepContext class)
- Pattern: Records start time on enter, emits WorkflowEvent on exit with duration and result

**WorkflowEvent:**
- Purpose: Wire-compatible event model shared between SDK and Collector
- Examples: `sdk/src/workflow_optimizer/models.py`, `platform/collector/src/collector/models.py`
- Pattern: Pydantic BaseModel with status validation; dual-use for inbound (EventIn) and outbound (WorkflowEvent)

**Database:**
- Purpose: Connection pool wrapper with domain-specific query methods
- Examples: `platform/collector/src/collector/database.py`
- Pattern: Pool management + parameterized queries + batch insert optimization

**WorkflowOptimizer (Client):**
- Purpose: Public entry point; manages transport lifecycle and provides convenience methods
- Examples: `sdk/src/workflow_optimizer/client.py`
- Pattern: Lazy initialization (first use), cascading agent_name/agent_role defaults

## Entry Points

**SDK:**
- Location: `sdk/src/workflow_optimizer/__init__.py`
- Triggers: `from workflow_optimizer import WorkflowOptimizer`
- Responsibilities: Expose public API (WorkflowOptimizer, TraceContext, exceptions, models)

**Collector Service:**
- Location: `platform/collector/src/collector/app.py:run()`
- Triggers: `cd platform/collector && .venv/bin/collector` (entrypoint script)
- Responsibilities: FastAPI lifespan (DB connect/disconnect), route registration, middleware setup

**Analysis Pipeline:**
- Location: `platform/analysis/src/analysis/pipeline.py:run_cli()` (or imported for programmatic use)
- Triggers: `cd platform/analysis && .venv/bin/python -m analysis.pipeline`
- Responsibilities: Connect to DB, cluster workflows, run analysis for each cluster, upsert results

**Agent Runtime Demo:**
- Location: `demo/agent-runtime/main.py:main()` or `demo_runner.py`
- Triggers: `cd demo/agent-runtime && .venv/bin/python3 main.py` or `demo_runner.py --rounds N`
- Responsibilities: Load config, initialize reasoning engine + MCP client, create agent, execute task

**Dashboard:**
- Location: `dashboard/src/app/page.tsx`
- Triggers: `cd dashboard && npm run dev`
- Responsibilities: Next.js app router, fetch data from collector API, render visualizations

## Error Handling

**Strategy:** Layered fault tolerance with graceful degradation.

**Patterns:**

- **SDK Transport:** Exponential backoff retry (3 max, 1s delay) on HTTP failures; logs and continues execution (no exception bubbles to agent)
- **Collector Routes:** Input validation via Pydantic; 400 on invalid JSON, 500 on DB errors, logged to structlog
- **Analysis Pipeline:** Try/catch on PM4Py discovery, graph building, pattern detection; log warning and continue with partial results
- **Agent Loops:** Loop detection via action history (circular reasoning for 3+ steps in window of 5); raises LoopDetectedError
- **Database:** asyncpg connection pool auto-retry on pool exhaustion; deadlocks surfaced as exceptions to caller

## Cross-Cutting Concerns

**Logging:**
- Framework: structlog with JSON formatting
- Pattern: Structured logging with context keys (workflow_id, event_id, agent_name, etc.)
- Examples: `platform/collector/src/collector/logger.py` defines `get_logger()` and `init_logging()`
- Usage: All modules use `log = get_logger(__name__)` and call `log.info(msg, key=value)`

**Validation:**
- Framework: Pydantic v2 field validators on all inbound models
- Pattern: Custom validators on `WorkflowEvent.status`, `EventIn.status`
- Examples: `sdk/src/workflow_optimizer/models.py` (status must be in {success, failure, timeout, loop_detected})

**Authentication:**
- Approach: None in MVP. CORS allowed from localhost:3000 only.
- Future: JWT bearer token validation in collector routes

---

*Architecture analysis: 2026-03-13*

# Architecture

**Updated:** 2026-03-31

## What This Is

Three-tier decoupled platform: SDK captures traces, collector stores them, analysis discovers optimal paths, dashboard visualises everything. Agents never know they're being traced.

## The Layers

**SDK** (`sdk/src/workflow_optimizer/`) — lightweight client library. Context managers wrap workflow execution, events get batched (50 events or 5s flush) and POSTed to the collector. Uses aiohttp + Pydantic v2. The agent framework doesn't need to change anything — tracing is transparent via `optimizer.trace()` and `trace.step()`.

**Collector** (`platform/collector/`) — FastAPI service. Receives events, stores in PostgreSQL + pgvector, serves queries. 7 route modules: events, workflows, optimize, analytics, dashboard, actions, ws. WebSocket broadcasts for live trace view. This is the central hub — dashboard, analysis engine, and SDK all talk to it.

**Analysis Engine** (`platform/analysis/`) — offline batch processing. This is where the interesting stuff happens:
- Reconstruct traces from raw events
- Two-level clustering: L1 embeddings (HAC), L2 edit distance (NED HAC)
- PM4Py Inductive Miner for process model discovery
- NetworkX DAG with tools as nodes, transitions as weighted edges
- Pareto-optimal path selection (duration, cost, success rate) with knee point
- Auto-generated decision trees from subcluster divergence
- Failure warnings extracted by comparing successful vs failed traces
- LLM-generated cluster names and suggestions

**Demo** (`demo/`) — two demos showing SDK integration:
- `agent-runtime/` — custom async Python agent with reasoning engine, MCP client, orchestrator. 25 scenarios across customer support and order fulfillment. `demo_runner.py` runs N rounds with interleaved analysis.
- `mcp-tool-server/` — FastAPI server exposing 7 tool modules (customer, order, ticket, knowledge, shipping, warranty, schemas). Agents call these via MCP.

**Dashboard** (`dashboard/`) — Next.js 16 + React 19 + TailwindCSS 4. Pages: overview, traces, clusters, graph (react-flow/dagre), insights, compare, agents, settings. Fetches from collector API, live updates via WebSocket.

## Data Flow

1. Agent calls `optimizer.trace()` → SDK buffers events → HTTP batch to collector → PostgreSQL `event_logs`
2. Agent calls `optimizer.get_optimal_path(task)` → collector generates embedding → pgvector cosine search on `optimal_paths` → returns guided or exploration mode
3. Analysis runs (triggered after each round): cluster workflows → reconstruct traces → discover process model → build graph → find Pareto paths → upsert optimal paths → extract failure warnings
4. Dashboard polls collector endpoints + WebSocket for live updates

## Key Config

- Similarity threshold: 0.78 (for clustering), 0.60 (for path lookup)
- Min executions: 30 (before serving guided mode)
- Min success rate: 0.85 (edge threshold in execution graph)
- NED threshold: 0.55 (for subclustering)
- Embedding model: `gemini/gemini-embedding-001` (768-dim)
- LLM model: `gemini/gemini-2.5-flash-lite`

## Tech Stack

**Backend:** Python 3.11+, FastAPI, asyncpg, Pydantic v2, structlog, LiteLLM
**Analysis:** PM4Py, NetworkX, pandas, scipy
**Frontend:** Next.js 16, React 19, TailwindCSS 4, Radix UI, react-flow, recharts, dagre
**Database:** PostgreSQL 16 + pgvector (HNSW index for cosine similarity)
**Infra:** Docker Compose for Postgres, uvicorn for backend, npm for dashboard

## Directory Map

```
FYP/
  sdk/src/workflow_optimizer/     # Client library (context managers, transport, models)
  platform/collector/             # FastAPI event service (routes, database, embeddings, websocket)
  platform/collector/migrations/  # SQL migrations (001-006)
  platform/analysis/              # Analysis engine (pipeline, clustering, graph, optimizer, decision_tree)
  demo/agent-runtime/             # Custom agent (agent, reasoning, mcp, orchestrator, mode_selector)
  demo/mcp-tool-server/           # MCP tool server (7 tool modules)
  dashboard/src/                  # Next.js frontend (app router, components, lib, hooks)
  scripts/                        # Utility scripts (start-platform.sh, statistical_tests/)
```

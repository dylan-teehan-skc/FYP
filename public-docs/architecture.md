# System Architecture

**Self-Optimising Workflow Intelligence Platform**

## Overview

A decoupled observability and optimisation platform that sits alongside any existing AI agent system. Companies integrate via a lightweight Python SDK (as few as two lines of code) or a raw REST API. The platform captures execution traces, discovers optimal tool-call sequences via process mining and Pareto-optimal path selection, and feeds that knowledge back to agents at runtime.

The product is **not** an agent framework. It is a layer that works with any agent system: LangChain, CrewAI, custom implementations, or the included demo.

## Repository Structure

```
FYP/
├── sdk/                     The product. Self-contained Python package (pip installable).
│                            What companies integrate. Minimal deps (aiohttp + pydantic).
│
├── platform/                Backend services (deployed together).
│   ├── collector/           FastAPI service, receives events, stores in Postgres.
│   │   └── migrations/      SQL schema (001_initial.sql, 002_upgrade_embeddings.sql)
│   └── analysis/            Process mining, pattern detection, Pareto-optimal path discovery.
│
├── dashboard/               React/Next.js frontend (separate deploy).
│                            Visualisation, metrics, optimisation suggestions.
│
├── demo/                    Example consumer (proves the platform works).
│   ├── agent-runtime/       Async Python agent system (built).
│   ├── mcp-tool-server/     FastAPI mock tools, 8 customer support tools (built).
│   └── demo_runner.py       Runs the 5 NovaTech scenarios across multiple rounds.
│
├── public-docs/             Architecture documentation (committed to git).
└── docker-compose.yml       Orchestrates all services.
```

**Key separation:**

- `sdk/` — what companies install (self-contained, no platform dependency)
- `platform/` — what we deploy (collector + analysis share a database)
- `dashboard/` — the frontend (reads from collector API)
- `demo/` — an example consumer (only imports the SDK, never from `platform/`)

## Component Architecture

### 1. SDK (`sdk/`)

| | |
|---|---|
| **Role** | Thin client library installed by companies |
| **Inputs** | Agent tool calls during workflow execution |
| **Outputs** | Structured events streamed to the collector; optimal path guidance returned to the agent |
| **Tech** | Python, aiohttp, Pydantic v2 |
| **Deps** | Minimal (aiohttp + pydantic only) |
| **Self-contained** | pip installable, no dependency on `platform/` or `dashboard/` |

**Key APIs:**

```python
optimizer = WorkflowOptimizer(endpoint="http://localhost:9000")
guidance = await optimizer.get_optimal_path("Handle refund for ORD-789")
async with optimizer.trace("Handle refund") as trace:
    with trace.step("check_ticket", params={...}):
        result = await check_ticket(...)
```

### 2. Collector (`platform/collector/`)

| | |
|---|---|
| **Role** | Central service. Receives events, stores them, serves queries |
| **Inputs** | Events from SDK via REST API |
| **Outputs** | Stored events in PostgreSQL; embeddings in pgvector; optimal path responses to SDK queries |
| **Tech** | FastAPI, asyncpg, Pydantic v2, LiteLLM (embeddings) |
| **Config** | pydantic-settings (env vars): `DATABASE_URL`, `SIMILARITY_THRESHOLD`, `EMBEDDING_MODEL`, `HOST`, `PORT`, `LOG_LEVEL` |

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/events` | Receive a single workflow event |
| `POST` | `/events/batch` | Receive multiple events |
| `POST` | `/workflows/complete` | Mark workflow complete, trigger embedding |
| `GET` | `/workflows/{id}/trace` | Get full trace for a workflow |
| `POST` | `/optimize/path` | Semantic search for optimal path |
| `GET` | `/analytics/summary` | Aggregate metrics across all workflows |

### 3. Analysis Engine (`platform/analysis/`)

| | |
|---|---|
| **Role** | Offline processing. Clusters workflows, builds process models, detects patterns, discovers Pareto-optimal paths |
| **Inputs** | Raw events from PostgreSQL |
| **Outputs** | Optimal path records written back to `optimal_paths` table |
| **Tech** | PM4Py (process mining), networkx (DAGs), asyncpg, LiteLLM, pandas |
| **Architecture** | Library (not service) — async functions callable from CLI or cron |

**Pipeline (8 steps):**

1. **Cluster Workflows (Two-Level)**
   - Level 1: Cosine similarity on task description embeddings (threshold >= 0.60)
   - Level 2: Levenshtein edit distance on tool sequences (threshold <= 2)
   - Each sub-cluster analysed independently

2. **Reconstruct Traces**
   - Fetch events by `workflow_id`, build typed `EventRecord` objects
   - Extract `tool_sequence`, compute duration/cost/success
   - Convert to PM4Py-compatible DataFrame

3. **Discover Process Model (PM4Py)**
   - Inductive Miner on successful traces only -> Petri net
   - Compute quality metrics: fitness + precision via token-based replay

4. **Build Execution Graph (networkx)**
   - Weighted DAG with `__START__`/`__END__` sentinels
   - Edge weights: `avg_duration_ms`, `avg_cost_usd`, `frequency`, `success_rate`

5. **Detect Patterns**
   - PM4Py conformance checking (missing/remaining tokens = deviations)
   - Redundant steps (tool called 2+ times in single trace)
   - Retry loops (same tool called after failure status)
   - Bottlenecks (tool avg duration > 40% of total workflow)

6. **Find Pareto-Optimal Paths**
   - Filter graph edges by `success_rate >= min_success_rate`
   - Enumerate all `__START__` -> `__END__` paths (feasible at <=8 tools)
   - Score each on 3 objectives: duration, cost, (1 - success_rate)
   - Non-dominated sorting -> Pareto front
   - Select knee point (lowest normalised objective sum)
   - Fallback: most-frequent path if no paths survive filtering

7. **Generate Suggestions**
   - Map each pattern to actionable recommendation with estimated savings
   - Compare traces against optimal path -> reorder/skip suggestions

8. **Upsert Optimal Path**
   - `DELETE` + `INSERT` in transaction -> `optimal_paths` table
   - Collector serves these to SDK via semantic search

### 4. Dashboard (`dashboard/`)

| | |
|---|---|
| **Role** | Web frontend for visualisation and insights |
| **Inputs** | Data from collector REST API |
| **Outputs** | Interactive visualisations |
| **Tech** | Next.js, React, react-flow (graphs), recharts (charts), Tailwind CSS |

**Views:**

- **Workflow Traces** — Step-by-step timeline with latency/cost per step
- **Execution Graph** — Interactive node-edge graph of tool-call patterns
- **Optimisation Panel** — Top cost leaks, slowest steps, suggested reordering
- **Metrics Dashboard** — Avg duration, cost, success rate over time
- **Compare View** — Exploration vs guided performance side-by-side

### 5. Demo Agent-Runtime (`demo/agent-runtime/`)

| | |
|---|---|
| **Role** | Example consumer. Proves the platform works |
| **Tech** | Python 3.11+, asyncio, aiohttp, LiteLLM, Pydantic v2, structlog |

**Components:**

| Component | Description |
|-----------|-------------|
| Agent | Autonomous agent with LLM-based reasoning |
| Orchestrator | Coordinates agents, delegates tasks, tracks state |
| MCPClient | Async HTTP client for MCP tool server |
| ReasoningEngine | LLM integration via LiteLLM (`acompletion`) |
| ModeSelector | Decides exploration vs guided based on SDK response |

### 6. Demo MCP-Tool-Server (`demo/mcp-tool-server/`)

| | |
|---|---|
| **Role** | Mock customer support tools for the demo scenario |
| **Tech** | FastAPI, Pydantic |

**Tools:** `check_ticket_status`, `get_order_details`, `check_refund_eligibility`, `process_refund`, `send_customer_message`, `close_ticket`, `get_customer_history`, `search_knowledge_base`

## Data Flow

```
┌──────────────────────────────────────────────────┐
│  ANY AGENT SYSTEM  (or demo/agent-runtime)       │
│                                                  │
│  from workflow_optimizer import WorkflowOptimizer │
│  optimizer = WorkflowOptimizer(endpoint=...)     │
│                                                  │
│  1. optimizer.get_optimal_path(task)  ──────┐    │
│  2. Agent executes workflow                 │    │
│  3. SDK auto-captures each tool call  ──┐   │    │
└─────────────────────────────────────────┼───┼────┘
     events stream in real-time           │   │
                                          │   │ optimal path response
                                          v   v
┌──────────────────────────────────────────────────┐
│  COLLECTOR (platform/collector/, port 9000)      │
│                                                  │
│  Validates events (Pydantic)                     │
│  Stores in PostgreSQL                            │
│  Generates 1536-dim embeddings on workflow       │
│    complete (text-embedding-3-small via LiteLLM) │
│  Serves optimal path queries via semantic search │
│  Configurable threshold (default 0.60)           │
└──────────────────┬───────────────────────────────┘
                   │
                   v
┌──────────────────────────────────────────────────┐
│  POSTGRESQL + PGVECTOR (port 5432)               │
│                                                  │
│  event_logs           Raw structured events      │
│  workflow_embeddings  VECTOR(1536) embeddings     │
│  optimal_paths        VECTOR(1536) + JSONB paths  │
│                       HNSW indexes (cosine ops)  │
└──────────────────┬───────────────────────────────┘
                   │
                   v
┌──────────────────────────────────────────────────┐
│  ANALYSIS ENGINE (platform/analysis/)            │
│                                                  │
│  Two-Level Clustering ──> Trace Reconstruction   │
│    ──> PM4Py Process Discovery + Conformance     │
│    ──> Pattern Detection (4 detectors)           │
│    ──> Pareto-Optimal Path Selection             │
│    ──> Suggestion Generation                     │
│    ──> Upsert optimal_paths for collector        │
└──────────────────┬───────────────────────────────┘
                   │
                   v
┌──────────────────────────────────────────────────┐
│  DASHBOARD (dashboard/, port 3000)               │
│                                                  │
│  Trace Viewer | Execution Graph | Metrics        │
│  Optimisation Suggestions | Compare View         │
└──────────────────────────────────────────────────┘
```

## Self-Optimising Feedback Loop

The core mechanism operates across two modes:

### Exploration Mode (insufficient data)

- **Trigger:** No similar past workflows found, or confidence below threshold
- **Behaviour:** Agent runs freely. SDK captures every tool call. No guidance provided. Path diversity emerges naturally
- **Goal:** Accumulate diverse execution traces

### Guided Mode (sufficient data, high confidence)

- **Trigger:** Similar workflows found with similarity >= 0.60, at least 10 prior executions, success rate >= 85%
- **Behaviour:** SDK queries collector at workflow start. Collector performs semantic search over past embeddings. Optimal tool-call sequence returned to agent. Sequence injected into agent prompt context
- **Goal:** Execute faster using learned knowledge

> **Note on threshold:** 0.60 is calibrated for text-embedding-3-small. Score distributions are model-dependent — ada-002 produces ~0.85 for similar texts, text-embedding-3-small produces ~0.43. Research (ACM Web Conference 2024, Preprints.org 2024) informed this calibration.

The transition is automatic. As data accumulates, the system shifts from exploration to guided mode without manual intervention.

**Loop:**

1. Agent starts task
2. SDK queries for optimal path
3. Exploration (no data) OR Guided (path returned)
4. Agent executes workflow, SDK captures every step
5. Collector stores events, generates embedding on complete
6. Analysis engine clusters, discovers Pareto-optimal paths
7. Next similar task benefits from accumulated knowledge
8. System improves with every run

## Database Schema

### `event_logs`

| Column | Type | Notes |
|--------|------|-------|
| `event_id` | UUID | Primary key |
| `workflow_id` | UUID | Groups events into one workflow run |
| `timestamp` | TIMESTAMPTZ | |
| `activity` | VARCHAR | e.g. `tool_call:check_ticket_status` |
| `agent_name` | VARCHAR | |
| `agent_role` | VARCHAR | |
| `tool_name` | VARCHAR | Nullable |
| `tool_parameters` | JSONB | |
| `tool_response` | JSONB | |
| `llm_model` | VARCHAR | |
| `llm_prompt_tokens` | INTEGER | |
| `llm_completion_tokens` | INTEGER | |
| `llm_reasoning` | TEXT | |
| `duration_ms` | FLOAT | |
| `cost_usd` | DECIMAL | |
| `status` | VARCHAR | `success`, `failure`, `timeout`, `loop_detected` |
| `error_message` | TEXT | Nullable |
| `step_number` | INTEGER | |
| `parent_event_id` | UUID | Nullable, for nested actions |

### `workflow_embeddings`

| Column | Type | Notes |
|--------|------|-------|
| `workflow_id` | UUID | Foreign key to `event_logs` |
| `task_description` | TEXT | |
| `embedding` | VECTOR(1536) | pgvector, text-embedding-3-small native dims |
| `model_version` | VARCHAR | |
| `created_at` | TIMESTAMPTZ | |

### `optimal_paths`

| Column | Type | Notes |
|--------|------|-------|
| `path_id` | UUID | Primary key |
| `task_cluster` | TEXT | Semantic grouping label |
| `tool_sequence` | JSONB | Ordered list of tool names |
| `avg_duration_ms` | FLOAT | |
| `avg_steps` | FLOAT | |
| `success_rate` | FLOAT | |
| `execution_count` | INTEGER | |
| `embedding` | VECTOR(1536) | pgvector |
| `updated_at` | TIMESTAMPTZ | |

### Indexes

- HNSW on `workflow_embeddings.embedding` (`vector_cosine_ops`)
- HNSW on `optimal_paths.embedding` (`vector_cosine_ops`)
- B-tree on `event_logs`: `workflow_id`, `timestamp`, `activity`, `agent_name`

## Deployment

All services orchestrated via Docker Compose:

| Service | Tech | Port |
|---------|------|------|
| `demo/agent-runtime` | Python 3.11 | CLI (no port) |
| `demo/mcp-tool-server` | FastAPI | 8000 |
| `platform/collector` | FastAPI | 9000 |
| `postgres-pgvector` | PostgreSQL 16 + pgvector | 5432 |
| `dashboard` | Next.js | 3000 |

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, asyncio, asyncpg, Pydantic v2, LiteLLM |
| Database | PostgreSQL 16 + pgvector (VECTOR(1536), HNSW indexes) |
| Frontend | Next.js, React, react-flow (graphs), recharts (charts), Tailwind CSS |
| Analysis | PM4Py (process mining), networkx (DAGs), pgvector (semantic search), pandas (DataFrames), LiteLLM (embeddings) |
| Agent | LiteLLM (multi-provider LLM), MCP (tool communication), structlog |
| Testing | pytest, pytest-asyncio, pytest-cov, ruff |

## Research References

The analysis engine design is grounded in academic literature:

- **van der Aalst (2019)** "Limitations of the Directly-Follows Graph" — Why we use PM4Py Inductive Miner instead of raw DFGs
- **Berti et al. (2023)** "PM4Py: A Process Mining Library" — Library suitability for our use case
- **Song et al. (2009)** "Trace Clustering in Process Mining" — Two-level clustering (semantic + trace structure)
- **Yassa et al. (2023)** "Multi-Objective Optimization in Cloud" — Pareto front over weighted Dijkstra for multi-objective paths
- **ACM Web Conference (2024)** "Is Cosine-Similarity Really About Similarity?" — Score distributions are model-dependent (threshold calibration)

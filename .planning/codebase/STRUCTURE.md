# Codebase Structure

**Analysis Date:** 2026-03-13

## Directory Layout

```
FYP/
├── sdk/                                # Product SDK (pip-installable)
│   ├── src/workflow_optimizer/         # Public package
│   │   ├── __init__.py                 # Exports: WorkflowOptimizer, models, exceptions
│   │   ├── client.py                   # WorkflowOptimizer class (main entry point)
│   │   ├── trace.py                    # TraceContext, StepContext managers
│   │   ├── models.py                   # Pydantic: WorkflowEvent, OptimalPathResponse
│   │   ├── transport.py                # HttpTransport with batching and retry logic
│   │   └── exceptions.py               # Custom exceptions (TraceStateError, etc.)
│   ├── tests/                          # pytest test suite (57 tests)
│   └── pyproject.toml                  # Dependencies: aiohttp, pydantic
│
├── platform/                           # Backend services
│   │
│   ├── collector/                      # Event ingestion + query service
│   │   ├── src/collector/
│   │   │   ├── __init__.py
│   │   │   ├── app.py                  # FastAPI factory, lifespan, route registration
│   │   │   ├── config.py               # Settings: DB URL, embedding model, thresholds
│   │   │   ├── database.py             # asyncpg connection pool, domain queries
│   │   │   ├── embeddings.py           # EmbeddingService (Gemini/OpenAI)
│   │   │   ├── models.py               # Pydantic: EventIn, OptimalPathOut, etc.
│   │   │   ├── logger.py               # structlog initialization
│   │   │   ├── websocket.py            # ConnectionManager for live trace broadcast
│   │   │   └── routes/                 # HTTP route handlers
│   │   │       ├── events.py           # POST /events, /events/batch (trace ingestion)
│   │   │       ├── workflows.py        # GET /workflows, POST /workflows/complete
│   │   │       ├── optimize.py         # POST /optimize/path (semantic search)
│   │   │       ├── analytics.py        # GET /analytics/* (summaries, distributions)
│   │   │       ├── dashboard.py        # GET /task-clusters, /optimal-paths
│   │   │       ├── actions.py          # POST /actions/run-analysis
│   │   │       └── ws.py               # WebSocket endpoint /ws
│   │   ├── migrations/                 # SQL migration files (001-006)
│   │   ├── tests/                      # pytest (129 tests, 97% coverage)
│   │   └── pyproject.toml              # Dependencies: FastAPI, asyncpg, LiteLLM
│   │
│   └── analysis/                       # Trace analysis + optimal path discovery
│       ├── src/analysis/
│       │   ├── __init__.py
│       │   ├── pipeline.py             # Main entry point, orchestrates stages
│       │   ├── database.py             # asyncpg for trace queries
│       │   ├── traces.py               # reconstruct_trace: chain events by workflow_id
│       │   ├── graph.py                # discover_process_model (PM4Py), build_execution_graph (networkx)
│       │   ├── clustering.py           # Two-level clustering: embeddings + edit distance
│       │   ├── optimizer.py            # find_pareto_paths, select_knee_point (multi-objective)
│       │   ├── patterns.py             # detect_patterns: errors, loops, deviations
│       │   ├── failure_warnings.py     # extract_failure_warnings: failure sequences
│       │   ├── suggestions.py          # generate_suggestions for dashboard
│       │   ├── naming.py               # generate_cluster_name via LLM
│       │   ├── models.py               # Pydantic: WorkflowTrace, AnalysisResult, etc.
│       │   ├── config.py               # Settings
│       │   └── logger.py               # structlog
│       ├── prompts/                    # LLM prompt templates for naming, suggestions
│       ├── tests/                      # pytest (131 tests, 92% coverage)
│       └── pyproject.toml              # Dependencies: PM4Py, networkx, pandas
│
├── demo/                               # Consumer examples
│   │
│   ├── agent-runtime/                  # Custom async Python agent
│   │   ├── agent/
│   │   │   ├── agent.py                # Agent class: async reasoning loop with tool calls
│   │   │   └── __init__.py
│   │   ├── reasoning/
│   │   │   ├── engine.py               # ReasoningEngine: LLM-powered decision making
│   │   │   └── __init__.py
│   │   ├── mcp/
│   │   │   ├── client.py               # MCPClient: MCP tool client with tracing proxy
│   │   │   └── __init__.py
│   │   ├── orchestrator/
│   │   │   ├── orchestrator.py         # Orchestrator: agent registration + task execution
│   │   │   └── __init__.py
│   │   ├── mode_selector/
│   │   │   ├── selector.py             # Guidance injection: use optimal path if available
│   │   │   └── __init__.py
│   │   ├── prompts/
│   │   │   ├── templates.py            # Prompt templates for reasoning
│   │   │   └── __init__.py
│   │   ├── utils/
│   │   │   ├── config.py               # AppConfig: JSON-based configuration
│   │   │   ├── exceptions.py           # Custom exceptions
│   │   │   ├── logger.py               # structlog setup
│   │   │   ├── interfaces.py           # Protocol definitions
│   │   │   └── timer.py                # Timing utilities
│   │   ├── main.py                     # Entry point: load config, init agent, execute task
│   │   ├── demo_runner.py              # Scenario runner: 5 scenarios x N rounds
│   │   ├── config.json                 # Agent config: LLM model, MCP URL, agent role
│   │   ├── tests/                      # pytest (59 tests)
│   │   └── pyproject.toml
│   │
│   ├── langchain/                      # LangChain/LangGraph integration
│   │   ├── single_agent/
│   │   │   ├── main.py                 # LangChain tool-calling loop with callbacks
│   │   │   ├── agent.py
│   │   │   └── prompts.py
│   │   ├── multi_agent/
│   │   │   ├── main.py                 # LangGraph supervisor + specialist agents
│   │   │   ├── supervisor.py
│   │   │   ├── specialist_agents.py
│   │   │   └── prompts/
│   │   ├── tests/                      # pytest (35 tests)
│   │   └── pyproject.toml
│   │
│   └── mcp-tool-server/                # FastAPI mock tool server (13 tools)
│       ├── main.py                     # FastAPI app with 13 customer support endpoints
│       ├── schemas.py
│       ├── tests/                      # pytest (54 tests)
│       └── pyproject.toml (uv)
│
├── dashboard/                          # React/Next.js visualization frontend
│   ├── src/
│   │   ├── app/                        # Next.js App Router
│   │   │   ├── page.tsx                # Dashboard home
│   │   │   ├── traces/                 # Workflow trace views
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── clusters/               # Task cluster analysis
│   │   │   │   ├── page.tsx
│   │   │   │   ├── [id]/page.tsx
│   │   │   │   └── group/[name]/page.tsx
│   │   │   ├── graph/                  # Execution graph visualization
│   │   │   │   └── page.tsx
│   │   │   ├── insights/               # Pattern insights
│   │   │   │   └── page.tsx
│   │   │   ├── settings/
│   │   │   │   └── page.tsx
│   │   │   └── layout.tsx              # Root layout
│   │   │
│   │   ├── components/                 # Reusable React components
│   │   │   ├── layout/                 # Header, sidebar, nav
│   │   │   ├── dashboard/              # Dashboard cards, summary panels
│   │   │   ├── traces/                 # Trace timeline, step details
│   │   │   ├── clusters/               # Cluster list, cluster detail
│   │   │   ├── graph/                  # Graph visualization (react-flow)
│   │   │   ├── insights/               # Pattern cards, suggestions
│   │   │   ├── compare/                # Path comparison charts
│   │   │   ├── ui/                     # Primitives: buttons, dialogs, tables (shadcn/ui)
│   │   │   └── agents/                 # Agent view, statistics
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                  # Fetch wrapper and endpoint methods
│   │   │   ├── types.ts                # TypeScript interfaces for API responses
│   │   │   ├── utils.ts                # Utility functions
│   │   │   ├── format.ts               # Number/duration/cost formatting
│   │   │   ├── path-matching.ts        # Semantic path matching logic
│   │   │   └── format.test.ts
│   │   │
│   │   ├── hooks/                      # Custom React hooks
│   │   │   ├── useAnalytics.ts
│   │   │   └── useWebSocket.ts         # Live trace updates
│   │   │
│   │   └── test/
│   │       └── test files
│   │
│   ├── public/                         # Static assets
│   ├── next.config.js                  # Next.js config
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── package.json
│
├── scripts/                            # Utility scripts
│   ├── start-platform.sh               # Start collector + analysis services
│   └── statistical_tests/              # Statistical analysis (extract_and_test.py)
│
├── docs/                               # Documentation (auto-generated by this process)
├── private-docs/                       # Internal docs
├── public-docs/                        # Public architecture docs
│
├── docker-compose.yml                  # PostgreSQL 16 + pgvector
├── .env                                # Environment variables (GEMINI_API_KEY, etc.)
├── .env.example
├── README.md                           # Main project documentation
└── .claude/                            # Claude project instructions
```

## Directory Purposes

**`sdk/src/workflow_optimizer/`:**
- Purpose: Lightweight SDK client library for instrumentation
- Contains: Context managers, event models, HTTP transport
- Key files: `client.py` (WorkflowOptimizer), `trace.py` (TraceContext/StepContext), `models.py` (WorkflowEvent)

**`platform/collector/src/collector/`:**
- Purpose: Event ingestion service and query layer
- Contains: FastAPI app, database layer, embedding service, WebSocket manager
- Key files: `app.py` (factory), `database.py` (queries), `routes/optimize.py` (semantic search)

**`platform/analysis/src/analysis/`:**
- Purpose: Offline batch processing for pattern discovery
- Contains: PM4Py process mining, clustering, graph analysis, Pareto optimization
- Key files: `pipeline.py` (orchestrator), `graph.py` (process discovery), `optimizer.py` (path optimization)

**`demo/agent-runtime/`:**
- Purpose: Example custom agent framework showing SDK integration
- Contains: Agent, reasoning engine, MCP client, orchestrator
- Key files: `main.py` (entry point), `agent/agent.py`, `demo_runner.py` (scenario runner)

**`demo/langchain/`:**
- Purpose: LangChain/LangGraph integration examples
- Contains: Single-agent (tool-calling loop) and multi-agent (supervisor + specialists) demos
- Key files: `single_agent/main.py`, `multi_agent/main.py`

**`demo/mcp-tool-server/`:**
- Purpose: FastAPI mock tool server for demos
- Contains: 13 customer support tool endpoints
- Key files: `main.py`

**`dashboard/src/`:**
- Purpose: React/Next.js visualization frontend
- Contains: Pages, components, API client, utilities
- Key files: `app/page.tsx` (home), `lib/api.ts` (collector queries)

**`platform/collector/migrations/`:**
- Purpose: SQL migration files for PostgreSQL schema
- Contains: Table definitions, pgvector extension setup, indexes
- Key files: `001_create_tables.sql` through `006_add_failure_warnings.sql`

## Key File Locations

**Entry Points:**
- `sdk/src/workflow_optimizer/__init__.py` — SDK public API
- `platform/collector/src/collector/app.py:run()` — Collector service start
- `platform/analysis/src/analysis/pipeline.py` — Analysis pipeline orchestration
- `demo/agent-runtime/main.py` — Agent-runtime demo
- `demo/agent-runtime/demo_runner.py` — Multi-scenario runner
- `dashboard/src/app/page.tsx` — Dashboard home

**Configuration:**
- `demo/agent-runtime/config.json` — Agent configuration (LLM model, MCP URL, timeouts)
- `platform/collector/src/collector/config.py` — Collector settings (DB, embedding model, thresholds)
- `platform/analysis/src/analysis/config.py` — Analysis settings (clustering, optimization params)
- `.env` — Environment variables (GEMINI_API_KEY, EMBEDDING_MODEL)

**Core Logic:**
- `sdk/src/workflow_optimizer/client.py` — WorkflowOptimizer client class
- `sdk/src/workflow_optimizer/trace.py` — TraceContext and StepContext managers
- `platform/collector/src/collector/database.py` — Database queries and pool management
- `platform/analysis/src/analysis/graph.py` — Process discovery and execution graph building
- `demo/agent-runtime/agent/agent.py` — Autonomous reasoning agent

**Testing:**
- `sdk/tests/` — 57 tests for SDK
- `platform/collector/tests/` — 129 tests (97% coverage)
- `platform/analysis/tests/` — 131 tests (92% coverage)
- `demo/agent-runtime/tests/` — 59 tests
- `dashboard/src/test/` — Test utilities

## Naming Conventions

**Files:**
- `*.py` — Python modules
- `*.ts` / `*.tsx` — TypeScript / TypeScript React
- `*.sql` — Database migrations
- Lowercase with underscores: `workflow_optimizer`, `event_logs`, `optimal_paths`

**Directories:**
- Lowercase with hyphens for npm packages: `dashboard`
- Lowercase with hyphens for subcommands: `agent-runtime`, `mcp-tool-server`
- Lowercase with underscores for Python packages: `workflow_optimizer`, `collector`

**Python Modules:**
- Classes: `WorkflowOptimizer`, `TraceContext`, `Agent`, `MCPClient`
- Functions: `get_optimal_path()`, `trace_reconstruction()`, `find_pareto_paths()`
- Constants: `START_NODE`, `END_NODE`, `MAX_RETRIES`

**Database:**
- Tables: lowercase with underscores: `event_logs`, `optimal_paths`, `workflow_clusters`
- Columns: lowercase with underscores: `workflow_id`, `task_description`, `tool_sequence`
- Functions: `insert_event()`, `find_similar_paths()`, `fetch_workflows()`

## Where to Add New Code

**New Framework Integration:**
- Location: Create new demo package `demo/{framework-name}/`
- Pattern: Implement tracing bridge (~60 lines) that maps framework's tool-calling to `trace.step()`
- Examples: See `demo/agent-runtime/mcp/client.py` (transparent proxy), `demo/langchain/` (callback handler)

**New Feature (e.g., new analysis stage):**
- Implementation: Add module to `platform/analysis/src/analysis/{feature}.py`
- Integration: Call from `platform/analysis/src/analysis/pipeline.py` in appropriate stage
- Example: `failure_warnings.py` added after pattern detection stage

**New Collector Route (e.g., new analytics endpoint):**
- Implementation: Add handler to `platform/collector/src/collector/routes/{category}.py`
- Models: Define Pydantic response class in `platform/collector/src/collector/models.py`
- Registration: Add `app.include_router({route_module}.router)` in `platform/collector/src/collector/app.py`

**New Dashboard Page:**
- Location: `dashboard/src/app/{page-name}/page.tsx`
- Pattern: Create layout file at path, use `lib/api.ts` to fetch data, render components
- Components: Reusable components in `dashboard/src/components/{category}/`

**New SDK Feature:**
- Location: Add to appropriate module in `sdk/src/workflow_optimizer/`
- Exports: Update `sdk/src/workflow_optimizer/__init__.py` with new public API
- Tests: Add tests to `sdk/tests/`

**Utilities & Helpers:**
- Shared Python: `platform/collector/src/collector/utils/` or cross-import from other platform modules
- Shared TS: `dashboard/src/lib/`
- Demo-specific: Each demo has its own `utils/` directory

**Database Schema Changes:**
- Location: Create new migration file `platform/collector/migrations/{NNN}_{description}.sql`
- Pattern: Follow existing migrations (e.g., `001_create_tables.sql`)
- Run: Applied by collector on startup (if using migration runner)

## Special Directories

**`platform/collector/migrations/`:**
- Purpose: Version-controlled SQL migrations
- Generated: No (manually written)
- Committed: Yes
- Order: Numbered sequentially (001, 002, etc.)
- Run on: Collector startup (handles schema initialization)

**`demo/agent-runtime/logs/`:**
- Purpose: Local log files from demo runs
- Generated: Yes (by agent-runtime during execution)
- Committed: No (in `.gitignore`)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis outputs (generated by this process)
- Generated: Yes (auto-generated)
- Committed: Yes (checked in as reference)

**`platform/analysis/prompts/`:**
- Purpose: LLM prompt templates for naming clusters, generating suggestions
- Generated: No (manually written)
- Committed: Yes

---

*Structure analysis: 2026-03-13*

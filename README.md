<p align="center">
  <h1 align="center">Self-Optimising Workflow Intelligence Platform</h1>
  <p align="center">
    A decoupled observability and optimisation platform for AI agent workflows.<br/>
    Captures execution traces, discovers optimal paths, feeds knowledge back at runtime.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js"/>
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-362_passing-brightgreen?style=flat-square" alt="Tests"/>
  <img src="https://img.shields.io/badge/coverage-90%25+-brightgreen?style=flat-square" alt="Coverage"/>
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/LLM-Gemini_2.5_Flash-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>
</p>

---

> **Add 2 lines of code. Every workflow gets captured, analysed, and optimised automatically.**

## How It Works

```
   New Task ──► Optimal path in DB? ──Yes──► Guided Mode (inject hint) ──► Task Complete
                        │
                       No
                        │
                 Exploration Mode
                        │
              Agent executes freely
                        │
              SDK captures all events
                        │
              Analysis engine discovers
              optimal paths via PM4Py +
              Pareto front selection
                        │
                  Saves to DB ──► Next similar task gets guided mode
```

1. **Agent starts a task** — e.g. "Handle refund for order ORD-5001"
2. **SDK queries for guidance** — semantic search via pgvector cosine similarity
3. **Exploration mode** — no known path, agent runs freely, SDK captures every tool call
4. **Guided mode** — optimal path found, injected as a soft constraint into the LLM prompt
5. **Analysis engine** — clusters workflows, builds execution graphs, discovers Pareto-optimal paths
6. **Self-improving** — system gets better with every run, no manual tuning

## Repository Structure

```
sdk/                        Self-contained Python SDK (pip installable)
platform/
  collector/                FastAPI event receiver + pgvector semantic search
  analysis/                 Process mining, clustering, Pareto-optimal path discovery
dashboard/                  React/Next.js frontend for visualisation and metrics
demo/
  agent-runtime/            Custom async Python agent with MCP tool calling
  fulfillment/              Order fulfillment demo (6 microservices + MCP server)
  langchain/
    single_agent/           LangChain single-agent tool-calling loop
    multi_agent/            LangGraph supervisor + specialist graph
  mcp-tool-server/          FastAPI MCP tool server (13 customer support tools)
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker** — for PostgreSQL 16 + pgvector
- **Gemini API key** — used for LLM reasoning and embeddings
- **Node.js 18+** — for the dashboard

> If you have a local PostgreSQL on port 5432, stop it first: `brew services stop postgresql@17`

### 1. Environment variables

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: use OpenAI embeddings instead
# EMBEDDING_MODEL=text-embedding-3-small
# OPENAI_API_KEY=your-openai-key-here
```

### 2. Install dependencies

```bash
# SDK
cd sdk && pip install -e ".[dev]"

# Platform
cd platform/collector && pip install -e ".[dev]"
cd platform/analysis && pip install -e ".[dev]"

# Dashboard
cd dashboard && npm install

# Demo — Agent Runtime
cd demo/agent-runtime && pip install -e ../../sdk && pip install -e ".[dev]"

# Demo — MCP Tool Server
cd demo/mcp-tool-server && uv sync

# Demo — LangChain (optional)
cd demo/langchain && pip install -e ../../sdk && pip install -e ".[dev]"
```

### 3. Run the platform

```bash
# Start Postgres + pgvector
docker-compose up -d

# Start all services (collector, MCP servers, dashboard) in one command
bash scripts/start-platform.sh
```

Dashboard at [localhost:3000](http://localhost:3000), collector at [localhost:9000](http://localhost:9000).

### 4. Run demos

```bash
# Run 8 rounds of fulfillment scenarios with interleaved analysis
bash scripts/run-demo.sh --rounds 8

# Filter by workflow type
bash scripts/run-demo.sh --rounds 5 --types fulfilment,exchange
```

Each round runs a batch of scenarios followed by the analysis pipeline, so guided mode activates within the same session.

<details>
<summary><b>Manual approach</b> (run each service in a separate terminal)</summary>

```bash
# Terminal 1: Collector
cd platform/collector && .venv/bin/collector

# Terminal 2: MCP tool server
cd demo/mcp-tool-server && .venv/bin/python3 main.py

# Terminal 3: Dashboard
cd dashboard && npm run dev

# Terminal 4: Run agent-runtime demo
cd demo/agent-runtime && PYTHONPATH=. .venv/bin/python3 demo_runner.py --rounds 3

# Run analysis manually
cd platform/analysis && .venv/bin/python -m analysis.pipeline

# Run again — guided mode kicks in
cd demo/agent-runtime && PYTHONPATH=. .venv/bin/python3 demo_runner.py --rounds 3
```
</details>

### Utility scripts

| Script | Purpose |
|--------|---------|
| `scripts/start-platform.sh` | Start all services with one command (Ctrl+C to stop) |
| `scripts/run-demo.sh` | Run demo rounds with interleaved analysis |
| `scripts/reset-db.sh` | Reset the database to a clean state |
| `scripts/reset-paths.sh` | Clear discovered optimal paths (re-enter exploration mode) |

## Integration

The SDK is **framework-agnostic**. The entire public API is three things:

| API | Purpose |
|-----|---------|
| `WorkflowOptimizer` | Client — creates traces, queries for guidance |
| `TraceContext` | Wraps one workflow execution (async context manager) |
| `StepContext` | Wraps one tool call within a trace |

### Direct usage

```python
from workflow_optimizer import WorkflowOptimizer

optimizer = WorkflowOptimizer(endpoint="http://localhost:9000")

# Query for known optimal path
guidance = await optimizer.get_optimal_path("Handle refund for order ORD-789")
# Returns: {"mode": "guided", "path": ["check_ticket", ...], "confidence": 0.87}
# Or:      {"mode": "exploration"}  (not enough data yet)

# Capture execution trace
async with optimizer.trace("Handle refund for order ORD-789") as trace:
    with trace.step("check_ticket", params={"id": "T-123"}):
        result = await check_ticket("T-123")
    with trace.step("process_refund", params={"order": "ORD-789"}):
        result = await process_refund("ORD-789", 99.99)
```

### Framework bridges

Each framework needs a thin bridge (~60 lines) that maps its tool-calling mechanism to `trace.step()`:

<details>
<summary><b>Transparent proxy</b> (agent-runtime) — agent is completely unaware of tracing</summary>

```python
class TracingMCPClient:
    async def call_tool(self, tool_name, parameters):
        with self._trace.step(tool_name, params=parameters) as step:
            result = await self._inner.call_tool(tool_name, parameters)
            step.set_response(result)
            return result
```
</details>

<details>
<summary><b>Callback handler</b> (LangChain/LangGraph) — hooks into LangChain's callback system</summary>

```python
class WorkflowOptimizerCallbackHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        step = self._trace.step(serialized["name"], params=parsed_input)
        step.__enter__()

    def on_tool_end(self, output, *, run_id, **kwargs):
        step = self._active_steps.pop(run_id)
        step.set_response(parsed_output)
        step.__exit__(None, None, None)
```
</details>

The same pattern applies to any framework — CrewAI, AutoGen, OpenAI Agents SDK — find where tools are invoked and wrap with `trace.step()`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) asyncio, asyncpg, Pydantic v2, LiteLLM |
| **Database** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=flat-square&logo=postgresql&logoColor=white) pgvector (VECTOR(768), HNSW indexes) |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js_14-000000?style=flat-square&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black) ![Tailwind](https://img.shields.io/badge/Tailwind-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) ReactFlow, Recharts |
| **Analysis** | ![PM4Py](https://img.shields.io/badge/PM4Py-FF6F00?style=flat-square) networkx, pandas, pgvector |
| **Testing** | ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) pytest-asyncio, ruff |
| **CI/CD** | ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white) lint + test on every push |

## Research-Informed Design

The platform design is grounded in academic literature:

| Component | Approach | Why |
|-----------|----------|-----|
| Process Discovery | PM4Py Inductive Miner | DFGs allow spurious paths (van der Aalst 2019) |
| Trace Clustering | Two-level: cosine similarity + NED | Single-dimension clustering misses pattern differences (Song et al. 2009, Bose & van der Aalst 2009) |
| Path Optimisation | Pareto front enumeration | Weighted objectives can't find non-convex solutions (Deb et al. 2002) |
| Guided Mode | Soft constraint injection | Preserves agent autonomy (KnowAgent, Zhu et al. NAACL 2025) |
| Context Engineering | Comprehensive over concise | Terse summaries lose actionable detail (ACE, Zhang et al. ICLR 2026) |
| Minimum Observations | n=30 threshold | Bootstrap confidence + agent eval variance (Efron 1993, Bjarnason et al. 2026) |

## License

This project was developed as a Final Year Project at the University of Limerick.

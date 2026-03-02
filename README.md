# Self-Optimising Workflow Intelligence Platform

A decoupled observability and optimisation platform for AI agent workflows. Captures execution traces, discovers optimal tool-call sequences via process mining and Pareto-optimal path selection, and feeds that knowledge back to agents at runtime so they improve over time.

**Add 2 lines of code. Every workflow is captured, analysed, and optimised automatically.**

## How It Works

1. Agent starts a task (e.g. "Handle refund for order ORD-5001")
2. SDK asks: "Any known optimal path for this?" (semantic search via pgvector)
3. If yes, agent gets guidance (guided mode). If no, agent runs freely (exploration mode)
4. SDK auto-captures every tool call, latency, cost, success/failure
5. Events stream to the collector and are stored in PostgreSQL + pgvector
6. Analysis engine clusters workflows, builds execution graphs, and discovers Pareto-optimal paths
7. Next time a similar task comes in, guided mode kicks in
8. System improves with every run, no manual tuning needed

## Repository Structure

```
sdk/                     The product. Self-contained Python SDK (pip installable).
platform/                Backend services (deployed together).
  collector/             FastAPI event receiver + pgvector queries.
  analysis/              Process mining, pattern detection, Pareto-optimal path discovery.
dashboard/               React/Next.js frontend for visualisation and metrics.
demo/                    Example consumers (prove the platform works with different frameworks).
  agent-runtime/         Custom async Python agent system with LLM reasoning.
  langchain/             LangChain/LangGraph integration demos.
    single_agent/        Single-agent tool-calling loop via LangChain.
    multi_agent/         Multi-agent supervisor + specialist graph via LangGraph.
  mcp-tool-server/       FastAPI mock tools (13 customer support tools).
public-docs/             Architecture and design documentation.
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL 16 + pgvector)
- A Gemini API key (`GEMINI_API_KEY`) — used for both LLM reasoning and embeddings
- If you have a local PostgreSQL running on port 5432, stop it first — Docker needs that port:
  ```bash
  brew services stop postgresql@17   # or whichever version
  ```

### Environment variables

Create a `.env` file in the project root (or export these in your shell):

```bash
# Required — used by agent-runtime (LLM reasoning) and collector/analysis (embeddings)
GEMINI_API_KEY=your-gemini-api-key-here

# Optional — override the default embedding model
# EMBEDDING_MODEL=text-embedding-3-small   # requires OPENAI_API_KEY
# OPENAI_API_KEY=your-openai-key-here
```

### Install dependencies

Each component has its own virtual environment. Install once before running:

```bash
# SDK
cd sdk && pip install -e ".[dev]"

# Collector
cd platform/collector && pip install -e ".[dev]"

# MCP Tool Server (uses uv)
cd demo/mcp-tool-server && uv sync

# Agent Runtime (needs SDK installed first)
cd demo/agent-runtime && pip install -e ../../sdk && pip install -e ".[dev]"

# LangChain demo (needs SDK installed first)
cd demo/langchain && pip install -e ../../sdk && pip install -e ".[dev]"

# Analysis Engine
cd platform/analysis && pip install -e ".[dev]"

# Dashboard
cd dashboard && npm install
```

### Run the platform

Run each service in a separate terminal tab:

```bash
# Tab 1: Start Postgres + pgvector
docker-compose up -d

# Tab 2: Start the collector service (wait for Postgres to be ready)
cd platform/collector && .venv/bin/collector

# Tab 3: Start the MCP tool server
cd demo/mcp-tool-server && .venv/bin/python3 main.py

# Tab 4: Start the dashboard
cd dashboard && npm run dev

# Tab 5: Run the agent-runtime demo (5 scenarios x 3 rounds = 15 workflows)
cd demo/agent-runtime && PYTHONPATH=. .venv/bin/python3 demo_runner.py --rounds 3

# Or run the LangChain demos instead (7 scenarios x 2 rounds = 14 workflows each)
cd demo/langchain && PYTHONPATH=. .venv/bin/python3 -m single_agent.main --rounds 2
cd demo/langchain && PYTHONPATH=. .venv/bin/python3 -m multi_agent.main --rounds 2

# Run analysis to discover optimal paths
cd platform/analysis && .venv/bin/python -m analysis.pipeline

# Run the demos again — some scenarios now get guided mode
cd demo/agent-runtime && PYTHONPATH=. .venv/bin/python3 demo_runner.py --rounds 3
```

### Run tests

```bash
# All projects
cd demo/agent-runtime   && .venv/bin/python -m pytest tests/ -v   # 59 tests
cd demo/mcp-tool-server && .venv/bin/python -m pytest tests/ -v   # 54 tests
cd demo/langchain       && .venv/bin/python -m pytest tests/ -v   # 35 tests
cd sdk                  && .venv/bin/python -m pytest tests/ -v   # 57 tests
cd platform/collector   && .venv/bin/python -m pytest tests/ -v   # 129 tests, 97% coverage
cd platform/analysis    && .venv/bin/python -m pytest tests/ -v   # 131 tests, 92% coverage
```

## Integration

The SDK is framework-agnostic — it knows nothing about LangChain, LangGraph, or any specific agent framework. The entire public API is three things:

1. **WorkflowOptimizer** — the client (creates traces, queries for guidance)
2. **TraceContext** — wraps one workflow execution (async context manager)
3. **StepContext** — wraps one tool call within a trace

### Direct usage

```python
from workflow_optimizer import WorkflowOptimizer

optimizer = WorkflowOptimizer(endpoint="http://localhost:9000")

guidance = await optimizer.get_optimal_path("Handle refund for order ORD-789")
# Returns: {"mode": "guided", "path": ["check_ticket", ...], "confidence": 0.87}
# Or:      {"mode": "exploration"}  (not enough data yet)

async with optimizer.trace("Handle refund for order ORD-789") as trace:
    with trace.step("check_ticket", params={"id": "T-123"}):
        result = await check_ticket("T-123")
    with trace.step("process_refund", params={"order": "ORD-789"}):
        result = await process_refund("ORD-789", 99.99)
```

### Framework bridges

Each framework needs a thin bridge (~60 lines) that maps its tool-calling mechanism to `trace.step()`. Two patterns are included:

**Transparent proxy** (agent-runtime) — wraps the tool client so the agent is completely unaware of tracing:

```python
class TracingMCPClient:
    async def call_tool(self, tool_name, parameters):
        with self._trace.step(tool_name, params=parameters) as step:
            result = await self._inner.call_tool(tool_name, parameters)
            step.set_response(result)
            return result
```

**Callback handler** (LangChain/LangGraph) — hooks into LangChain's built-in callback system:

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

The same pattern applies to any framework — CrewAI, AutoGen, OpenAI Agents SDK — find where tools are invoked and wrap with `trace.step()`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, asyncio, asyncpg, Pydantic v2, LiteLLM |
| Database | PostgreSQL 16 + pgvector (VECTOR(768), HNSW indexes) |
| Frontend | Next.js, React, react-flow, recharts, Tailwind CSS |
| Analysis | PM4Py (process mining), networkx (DAGs), pgvector (semantic search), pandas |
| Testing | pytest, pytest-asyncio, pytest-cov, ruff |

## Research-Informed Design

The platform design is grounded in academic literature:

**Analysis engine:**
1. **PM4Py Inductive Miner** for process discovery + conformance checking — replaces raw Directly-Follows Graphs which allow spurious paths (van der Aalst 2019)
2. **Two-level clustering** — cosine similarity on task embeddings + Levenshtein edit distance on tool sequences (Song et al. 2009)
3. **Pareto front enumeration** for multi-objective path optimisation on duration, cost, and success rate — weighted Dijkstra can't find non-convex Pareto solutions (Yassa et al. 2023)

**SDK integration:**
4. **Transparent proxy pattern** for zero-refactoring instrumentation — TracingMCPClient wraps the real MCP client without the agent knowing (MCP Proxy Wrapper 2025; Sypherd et al. 2024)
5. **Soft constraint guidance** — optimal paths injected as context hints, not hard constraints, preserving agent autonomy (KnowAgent, Zhu et al. NAACL 2025)
6. **AgentBoard progress metrics** — incremental advancement tracking beyond binary success/failure (Ma et al. NeurIPS 2024)

## Demo Scenario

The demo simulates NovaTech Electronics, a company handling customer support tickets with an LLM-powered agent. Three demo runners exercise the same scenarios through different frameworks:

- **Agent Runtime** — custom async Python agent (5 scenarios per round)
- **LangChain Single-Agent** — LangChain tool-calling loop (7 scenarios per round)
- **LangChain Multi-Agent** — LangGraph supervisor + specialist graph (7 scenarios per round)

The core five ticket types exercise different tool combinations:

| Scenario | Ticket | Type | Expected Steps |
|----------|--------|------|---------------|
| Eligible refund | T-1001 | refund_request | 6 |
| Order status inquiry | T-1002 | order_inquiry | 4 |
| Denied refund | T-1003 | refund_request | 6 |
| VIP complaint | T-1004 | complaint | 6 |
| Product troubleshooting | T-1005 | product_support | 4 |

The LangChain demos add two additional error-handling scenarios (invalid ticket, system error) for 7 total per round.

## Limitations

**Embedding model**: The platform currently uses Gemini `gemini-embedding-001` (768-dim, via `dimensions=768`) for semantic search to keep the entire platform on a single API key. OpenAI's `text-embedding-3-small` (1536-dim) is the preferred model — it ranks higher on the MTEB benchmark, and the similarity threshold (0.60) was originally calibrated for its cosine similarity distribution. To switch, set `EMBEDDING_MODEL=text-embedding-3-small` and `OPENAI_API_KEY` in your environment, then run the database migration to upgrade to `VECTOR(1536)`.

## Documentation

- [Architecture](public-docs/architecture.md) - Component descriptions, data flow, database schema

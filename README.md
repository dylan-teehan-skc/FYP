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
demo/                    Example consumer (proves the platform works).
  agent-runtime/         Async Python agent system with LLM reasoning.
  mcp-tool-server/       FastAPI mock tools (8 customer support tools).
  demo_runner.py         Runs the 5 NovaTech demo scenarios.
public-docs/             Architecture and design documentation.
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL 16 + pgvector)
- If you have a local PostgreSQL running on port 5432, stop it first — Docker needs that port:
  ```bash
  brew services stop postgresql@17   # or whichever version
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

# Analysis Engine
cd platform/analysis && pip install -e ".[dev]"
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

# Tab 4: Run the demo (5 scenarios x 3 rounds = 15 workflows)
cd demo/agent-runtime && PYTHONPATH=. .venv/bin/python3 demo_runner.py --rounds 3

# 5. Run analysis to discover optimal paths
cd platform/analysis && .venv/bin/python -m analysis.pipeline

# 6. Run the demo again — some scenarios now get guided mode
cd demo/agent-runtime && PYTHONPATH=. .venv/bin/python3 demo_runner.py --rounds 3
```

### Run tests

```bash
# All projects
cd demo/agent-runtime   && .venv/bin/python -m pytest tests/ -v   # 59 tests
cd demo/mcp-tool-server && .venv/bin/python -m pytest tests/ -v   # 54 tests
cd sdk                  && .venv/bin/python -m pytest tests/ -v   # 57 tests
cd platform/collector   && .venv/bin/python -m pytest tests/ -v   # 49 tests, 97% coverage
cd platform/analysis    && .venv/bin/python -m pytest tests/ -v   # 131 tests, 92% coverage
```

## Integration

Companies integrate via the Python SDK:

```python
from workflow_optimizer import WorkflowOptimizer

optimizer = WorkflowOptimizer(endpoint="http://localhost:9000")

# Get optimal path guidance at workflow start
guidance = await optimizer.get_optimal_path("Handle refund for order ORD-789")
# Returns: {"mode": "guided", "path": ["check_ticket", ...], "confidence": 0.87}
# Or:      {"mode": "exploration"}  (not enough data yet)

# Auto-capture every step
async with optimizer.trace("Handle refund for order ORD-789") as trace:
    with trace.step("check_ticket", params={"id": "T-123"}):
        result = await check_ticket("T-123")
    with trace.step("process_refund", params={"order": "ORD-789"}):
        result = await process_refund("ORD-789", 99.99)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, asyncio, asyncpg, Pydantic v2, LiteLLM |
| Database | PostgreSQL 16 + pgvector (VECTOR(1536), HNSW indexes) |
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

The demo simulates NovaTech Electronics, a company handling customer support tickets with an LLM-powered agent. Five ticket types exercise different tool combinations:

| Scenario | Ticket | Type | Expected Steps |
|----------|--------|------|---------------|
| Eligible refund | T-1001 | refund_request | 6 |
| Order status inquiry | T-1002 | order_inquiry | 4 |
| Denied refund | T-1003 | refund_request | 6 |
| VIP complaint | T-1004 | complaint | 6 |
| Product troubleshooting | T-1005 | product_support | 4 |

## Documentation

- [Architecture](public-docs/architecture.md) - Component descriptions, data flow, database schema

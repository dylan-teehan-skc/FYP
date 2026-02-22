# Self-Optimising Workflow Intelligence Platform

A decoupled observability and optimisation platform for AI agent workflows. Captures execution traces, discovers optimal tool-call sequences, and feeds that knowledge back to agents at runtime so they improve over time.

**Add 2 lines of code. Every workflow is captured, analysed, and optimised automatically.**

## How It Works

1. Agent starts a task (e.g. "Handle refund for order ORD-5001")
2. SDK asks: "Any known optimal path for this?" (semantic search via pgvector)
3. If yes, agent gets guidance (guided mode). If no, agent runs freely (exploration mode)
4. SDK auto-captures every tool call, latency, cost, success/failure
5. Events stream to the collector and are stored in PostgreSQL + pgvector
6. Analysis engine builds execution graphs and finds optimal paths
7. Next time a similar task comes in, guided mode kicks in
8. System improves with every run, no manual tuning needed

## Repository Structure

```
sdk/                     The product. Self-contained Python SDK (pip installable).
platform/                Backend services (deployed together).
  collector/             FastAPI event receiver + pgvector queries.
  analysis/              Trace reconstruction, pattern detection, path optimisation.
dashboard/               React/Next.js frontend for visualisation and metrics.
demo/                    Example consumer (proves the platform works).
  agent-runtime/         Async Python agent system with LLM reasoning.
  mcp-tool-server/       FastAPI mock tools (8 customer support tools).
  demo_runner.py         Runs the 5 NovaTech demo scenarios.
docs/                    Spec, architecture, diary, demo scenario, useful links.
```

## Quick Start

### Run the demo

```bash
# 1. Start the MCP tool server
cd demo/mcp-tool-server && .venv/bin/python3 main.py

# 2. In another terminal, run the agent
cd demo/agent-runtime && .venv/bin/python3 main.py
```

### Run tests

```bash
cd demo/agent-runtime && .venv/bin/python3 -m pytest tests/ -v
```

## Integration

Companies integrate via the Python SDK:

```python
from workflow_sdk import WorkflowOptimizer

optimizer = WorkflowOptimizer(endpoint="http://localhost:9000")

async with optimizer.trace("Handle refund for order ORD-789") as trace:
    with trace.step("check_ticket"):
        result = await check_ticket("T-123")
```

Or via the REST API:

```
POST http://localhost:9000/events
{"workflow_id": "run-456", "tool": "check_ticket", "latency_ms": 230}
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, asyncio, aiohttp, Pydantic v2, LiteLLM |
| Database | PostgreSQL 16 + pgvector |
| Frontend | Next.js, React, react-flow, recharts, Tailwind CSS |
| Analysis | networkx, pgvector, LiteLLM |
| Testing | pytest, pytest-asyncio, aioresponses, ruff |

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

- [Architecture](docs/architecture.txt) - Component descriptions, data flow, database schema
- [Specification](docs/spec.md) - Full technical spec
- [Demo Scenario](docs/demo.txt) - NovaTech demo details
- [Design Diary](docs/diary-and-desing-choices.txt) - Decisions and rationale

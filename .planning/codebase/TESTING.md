# Testing

**Updated:** 2026-03-31

## Current State

| Module | Tests | Coverage |
|--------|-------|----------|
| platform/analysis | 231 | 94% |
| platform/collector | ~129 | ~97% |
| demo/agent-runtime | ~59 | — |
| demo/mcp-tool-server | ~54 | — |
| dashboard | vitest | — |

## How to Run

```bash
# Analysis
cd platform/analysis && .venv/bin/python3 -m pytest tests/ -v
cd platform/analysis && .venv/bin/python3 -m pytest tests/ --cov=src/analysis -q

# Agent runtime
cd demo/agent-runtime && .venv/bin/python3 -m pytest tests/ -v

# Dashboard
cd dashboard && npm run test
```

## Patterns

**Python tests** use `pytest` + `pytest-asyncio` (auto mode — no `@pytest.mark.asyncio` needed). Tests in `tests/` directory mirroring source. File naming: `test_*.py`. Class naming: `TestFeatureName`.

**Mocking:** `unittest.mock` — `AsyncMock` for async, `MagicMock` for sync. `aioresponses` for HTTP mocking. Each test module has a `conftest.py` with shared fixtures and helpers like `make_event()` and `MockDatabase`.

**What we mock:** external HTTP, database calls, LLM calls. **What we don't mock:** Pydantic models, pure functions, core business logic.

**Dashboard tests** use vitest + @testing-library/react. Co-located with source (`component.test.tsx` next to `component.tsx`).

## Coverage Philosophy

Target 90%+ on analysis and collector (the core platform). The analysis module was at 79% — bumped to 94% by adding tests for decision_tree (11% → 96%), database (centroid + mode success rates), and pipeline (failed traces case). Lowest file is `pipeline.py` at 63% — that's mostly the CLI orchestration and interleaved analysis loop which is hard to unit test.

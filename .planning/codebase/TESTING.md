# Testing Patterns

**Analysis Date:** 2026-03-13

## Test Framework

### Python Tests

**Runner:**
- `pytest` (version 7.4.0+)
- Config location: `[tool.pytest.ini_options]` in each project's `pyproject.toml`

**Async Support:**
- `pytest-asyncio` (version 0.23.0+)
- Asyncio mode: `auto` (async functions auto-detected, no decorator needed)

**Coverage:**
- `pytest-cov` (version 4.1.0+)

**Mocking:**
- `unittest.mock` (built-in): `AsyncMock`, `MagicMock`, `patch`
- `aioresponses` (version 0.7.6+) for mocking HTTP responses in async tests

**Run Commands:**
```bash
# All tests
pytest tests/ -v

# Watch mode (not standard pytest; use pytest-watch if needed)
pytest tests/ --tb=short

# Coverage
pytest tests/ --cov=. -q

# Specific file
pytest tests/test_demo_runner.py -v

# Specific test
pytest tests/test_demo_runner.py::TestScenarioDefinitions::test_fifteen_scenarios_defined
```

### TypeScript Tests

**Runner:**
- `vitest` (version 4.0.18+)
- Config location: `vitest.config.ts`

**Assertion Library:**
- `@testing-library/react` (for component testing)
- Built-in expect API (vitest)

**Configuration (vitest.config.ts):**
```typescript
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

**Run Commands:**
```bash
# All tests
npm run test

# Watch mode
npm run test:watch

# Specific file
vitest run src/lib/format.test.ts

# UI mode
vitest --ui
```

---

## Test File Organization

### Location Pattern

**Python:**
- Co-located: Tests in `tests/` directory at package root, mirroring source structure
- Pattern: `src/module.py` → `tests/test_module.py`
- Example: `platform/analysis/src/analysis/pipeline.py` → `platform/analysis/tests/test_pipeline.py`

**TypeScript:**
- Co-located alongside source: `src/components/compare/delta-card.tsx` → `src/components/compare/delta-card.test.tsx`
- Utilities: `src/lib/format.ts` → `src/lib/format.test.ts`

### Naming Convention

**Python:**
- Test files: `test_*.py`
- Test classes: `Test[FeatureName]` (PascalCase)
- Test methods: `test_[scenario]` (snake_case)

**TypeScript:**
- Test files: `*.test.ts` or `*.test.tsx`
- Test suites: `describe("[feature]", ...)`
- Test cases: `it("[scenario]", ...)`

---

## Test Structure

### Python Structure

**Overall Pattern:**

```python
"""Tests for [module name]."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from module_under_test import Function, Class


class TestClass:
    """Tests for a class or related set of functions."""

    @pytest.fixture
    def setup(self) -> tuple:
        """Setup fixture with dependencies."""
        # Return tuple of (dependency1, dependency2, thing_under_test)
        pass

    def test_basic_behavior(self, setup: tuple) -> None:
        """Test straightforward happy path."""
        # Arrange, Act, Assert

    @pytest.mark.asyncio
    async def test_async_behavior(self, setup: tuple) -> None:
        """Test async operation."""
        # Arrange, Act, Assert
```

**Example from `/Users/dylan/MyRepos/FYP/demo/agent-runtime/tests/test_demo_runner.py`:**

```python
class TestBuildGuidedContext:
    def test_exploration_returns_empty(self) -> None:
        response = OptimalPathResponse(mode="exploration")
        assert build_guided_context(response) == ""

    def test_guided_with_path(self) -> None:
        response = OptimalPathResponse(
            mode="guided",
            path=["check_ticket", "get_order", "process_refund"],
            confidence=0.87,
            success_rate=0.95,
        )
        result = build_guided_context(response)
        assert "OPTIMIZATION HINT" in result
        assert "1. check_ticket" in result
```

**Fixture Pattern:**

```python
@pytest.fixture
def sample_config() -> AppConfig:
    """Valid AppConfig for testing."""
    return AppConfig(
        llm=LLMConfig(model="gpt-4"),
        logging=LoggingConfig(level="DEBUG"),
        mcp=MCPConfig(server_url="http://localhost:8000"),
        agent=AgentConfig(loop_detection_threshold=4, loop_detection_window=6),
    )
```

### TypeScript Structure

**Pattern:**

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ComponentUnderTest } from "./component-under-test";

describe("ComponentUnderTest", () => {
  it("renders without crashing", () => {
    render(<ComponentUnderTest />);
    expect(screen.getByText("Expected text")).toBeInTheDocument();
  });

  it("handles user interaction", async () => {
    render(<ComponentUnderTest />);
    const button = screen.getByRole("button", { name: "Click me" });
    await userEvent.click(button);
    expect(screen.getByText("Updated")).toBeInTheDocument();
  });
});
```

**Example from `/Users/dylan/MyRepos/FYP/dashboard/src/lib/format.test.ts`:**

```typescript
describe("formatCost", () => {
  it("formats small costs with 4 decimal places", () => {
    expect(formatCost(0.0023)).toBe("$0.0023");
  });

  it("returns dash for null", () => {
    expect(formatCost(null)).toBe("-");
  });
});
```

---

## Mocking Patterns

### Python Mocking

**Framework:** `unittest.mock` (built-in)

**Basic Async Mock:**

```python
from unittest.mock import AsyncMock

inner = AsyncMock()
inner.reason = AsyncMock(return_value={
    "reasoning": "Check the ticket first",
    "action": "check_ticket",
    "parameters": {"ticket_id": "T-1001"},
})
result = await inner.reason("task", "ctx", "tools")
```

**Mock with Side Effects:**

```python
mock = AsyncMock(side_effect=[
    {"success": True, "result": {"status": "closed"}},
    {"success": True, "result": {"refund_status": "refunded"}},
])
first = await mock()
second = await mock()
```

**Mock Database Pattern (conftest.py):**

```python
class MockDatabase:
    """In-memory mock database for testing."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.insert_event = AsyncMock(side_effect=self._insert_event)
        self.get_workflow_trace = AsyncMock(return_value=[])

    async def _insert_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)
```

**Patching:**

```python
from unittest.mock import patch

def test_with_patch(self) -> None:
    with patch("sys.argv", ["demo_runner.py", "--rounds", "5"]):
        args = parse_args()
        assert args.rounds == 5
```

### What to Mock

- External HTTP calls
- Database calls (replace with mock database in conftest)
- File I/O
- System dependencies (e.g., environment variables)

### What NOT to Mock

- Pydantic models (use actual instances)
- Pure functions (test real behavior)
- Core business logic (test implementation, not stub it)

---

## Fixtures and Test Data

### Test Data Helpers

**Python Pattern from `/Users/dylan/MyRepos/FYP/platform/analysis/tests/conftest.py`:**

```python
def make_event(
    workflow_id: str = "wf-1",
    activity: str = "tool_call:check_ticket",
    tool_name: str | None = "check_ticket",
    step_number: int = 1,
    duration_ms: float = 200.0,
    cost_usd: float = 0.001,
    status: str = "success",
    **kwargs: Any,
) -> EventRecord:
    """Helper to create an EventRecord with sensible defaults."""
    return EventRecord(
        event_id=kwargs.get("event_id", f"evt-{step_number}"),
        workflow_id=workflow_id,
        timestamp=kwargs.get("timestamp", datetime(2025, 2, 23, 10, 0, step_number, tzinfo=UTC)),
        activity=activity,
        tool_name=tool_name,
        step_number=step_number,
        status=status,
    )
```

**Fixture Location:**
- Shared fixtures in `conftest.py` at package root
- Project-specific fixtures in test module's `conftest.py`
- Helper functions (like `make_event()`) in same `conftest.py`

### Fixture Composition

```python
@pytest.fixture
def sample_events() -> list[EventRecord]:
    """6 events for T-1001 eligible refund workflow."""
    return [
        make_event(tool_name="check_ticket", step_number=1, duration_ms=230.0),
        make_event(tool_name="get_order", step_number=2, duration_ms=140.0),
        # ... more events ...
    ]

@pytest.fixture
def sample_trace(sample_events: list[EventRecord]) -> WorkflowTrace:
    """Pre-built trace from sample_events."""
    return WorkflowTrace(
        workflow_id="wf-1",
        events=sample_events,
        tool_sequence=[...],
        success=True,
    )
```

---

## Coverage

### Coverage Tool

**Tool:** `pytest-cov`

**View Coverage:**
```bash
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html
```

**Requirements:** Not enforced by CI; coverage targets are aspirational (>80% for critical paths)

---

## Test Types

### Unit Tests

**Scope:** Single function or method in isolation

**Approach:**
- Mock all external dependencies
- Test happy path + error cases
- Fast execution (<100ms per test)

**Example from `/Users/dylan/MyRepos/FYP/demo/agent-runtime/tests/test_demo_runner.py`:**

```python
class TestBuildGuidedContext:
    def test_exploration_returns_empty(self) -> None:
        response = OptimalPathResponse(mode="exploration")
        assert build_guided_context(response) == ""

    def test_guided_with_path(self) -> None:
        # Test specific path building logic
        response = OptimalPathResponse(
            mode="guided",
            path=["check_ticket", "get_order", "process_refund"],
        )
        result = build_guided_context(response)
        assert "1. check_ticket" in result
```

### Integration Tests

**Scope:** Multiple components working together (e.g., API endpoint + database mock)

**Approach:**
- Mock external services, not internal dependencies
- Test full request/response cycle
- May be slower (100ms - 1s per test)

**Example from `/Users/dylan/MyRepos/FYP/platform/collector/tests/test_routes_optimize.py`:**

```python
class TestOptimizePath:
    async def test_guided_mode_high_similarity(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        mock_db.find_similar_paths = AsyncMock(return_value={
            "tool_sequence": ["check_ticket", "get_order", "process_refund"],
            "success_rate": 0.95,
        })
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund for ORD-789"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "guided"
```

### E2E Tests

**Status:** Not used in this codebase

---

## Common Patterns

### Async Testing

**Pattern with `@pytest.mark.asyncio`:**

```python
@pytest.mark.asyncio
async def test_async_operation(self, setup: tuple) -> None:
    """Test an async function."""
    inner, last, engine = setup
    result = await engine.reason("task", "ctx", "tools")
    assert result["action"] == "check_ticket"
    inner.reason.assert_called_once_with("task", "ctx", "tools", None)
```

**Async Client Testing (FastAPI):**

```python
@pytest.fixture
async def client(app):
    """Async test client for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# In test:
async def test_endpoint(self, client: AsyncClient) -> None:
    response = await client.post("/endpoint", json={...})
    assert response.status_code == 200
```

### Error Testing

**Pattern for Expected Exceptions:**

```python
def test_invalid_config(self) -> None:
    with pytest.raises(ValueError, match="invalid"):
        LLMConfig(model="")
```

**Pattern for Verification of Tool Error:**

```python
@pytest.mark.asyncio
async def test_call_tool_with_trace_records_error(self, setup: tuple) -> None:
    inner, _, client = setup
    inner.call_tool = AsyncMock(return_value={
        "success": False,
        "error": "tool not found",
    })

    mock_step = MagicMock()
    mock_step.__enter__ = MagicMock(return_value=mock_step)
    mock_step.__exit__ = MagicMock(return_value=False)

    mock_trace = MagicMock()
    mock_trace.step = MagicMock(return_value=mock_step)

    client.set_trace(mock_trace)
    result = await client.call_tool("unknown_tool", {})

    mock_step.set_error.assert_called_once_with("tool not found")
    assert result["success"] is False
```

### Parameterized Tests

**Pattern (pytest):**

```python
@pytest.mark.parametrize("input,expected", [
    ("a", 1),
    ("b", 2),
])
def test_mapping(self, input: str, expected: int) -> None:
    assert get_value(input) == expected
```

---

## Conftest Patterns

### Shared Fixtures (conftest.py)

**Location:** At package/project root in `tests/conftest.py`

**Pattern:**

```python
"""Shared fixtures for [project] tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

class MockDatabase:
    """In-memory mock database for testing."""
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.insert_event = AsyncMock(side_effect=self._insert_event)

@pytest.fixture
def mock_db() -> MockDatabase:
    return MockDatabase()

@pytest.fixture
def sample_config() -> AppConfig:
    """Valid config for tests."""
    return AppConfig(...)
```

### Autouse Fixtures

**Pattern for setup/teardown:**

```python
@pytest.fixture(autouse=True)
async def cleanup(self):
    """Cleanup after each test."""
    yield
    # Teardown code here
```

---

## Test Coverage Goals

**Target:** 80%+ for critical paths
- Business logic: high coverage (95%+)
- Configuration: medium coverage (70-80%)
- Integration points: medium coverage (70-80%)
- Error cases: explicit coverage required

**Not required:**
- 100% coverage (aim for meaningful coverage)
- Coverage of framework/library code

---

## Running Tests

### Local Execution

**Python:**
```bash
cd demo/agent-runtime
.venv/bin/python3 -m pytest tests/ -v
.venv/bin/python3 -m pytest tests/ --cov=. -q
```

**TypeScript:**
```bash
cd dashboard
npm run test              # Run all
npm run test:watch       # Watch mode
```

### Continuous Integration

**Status:** Tests are runnable locally; CI/CD integration depends on project setup

---

*Testing analysis: 2026-03-13*

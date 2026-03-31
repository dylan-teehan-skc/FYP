# Coding Conventions

**Analysis Date:** 2026-03-13

## Overview

This codebase uses **Python 3.11+** for backend/SDK code and **TypeScript/React** for frontend (dashboard). Code style is enforced via `ruff` (Python) and `prettier`/`vitest` (TypeScript).

## Python Conventions

### Naming Patterns

**Files:**
- Snake case: `database.py`, `failure_warnings.py`, `demo_runner.py`
- Module names should be clear and descriptive

**Functions:**
- Snake case: `reconstruct_trace()`, `extract_tool_sequence()`, `extract_failure_warnings()`
- Public functions have type hints on all parameters and return types (required)
- Private functions (prefix `_`) may have type hints but are less critical

**Variables:**
- Snake case: `workflow_id`, `tool_sequence`, `total_duration_ms`
- No single-letter names except in list comprehensions or short scopes

**Types/Classes:**
- PascalCase: `WorkflowTrace`, `OptimalPath`, `EventRecord`
- Pydantic models use PascalCase with suffix convention for I/O: `EventIn`, `EventOut`
- Custom exceptions use PascalCase ending in `Error` or `Exception`: `ConfigurationError`, `MCPToolError`

**Constants:**
- UPPER_SNAKE_CASE: `MAX_WARNINGS`, `TIME_KEY`, `API_BASE`

### Code Style

**Formatting:**
- Tool: `ruff` format
- Line length: 100 characters (set in all `pyproject.toml` files)
- Target version: Python 3.11+

**Linting Rules (ruff):**
- Rules enabled: E, F, I, N, W, UP (pycodestyle, Pyflakes, isort, pep8-naming, pycodestyle warnings, pyupgrade)
- Line-length = 100 in all projects
- Config location: `[tool.ruff]` and `[tool.ruff.lint]` in `pyproject.toml`
- Per-file ignores used sparingly (e.g., E402 in `platform/analysis/src/analysis/pipeline.py` for delayed imports)

**Type Checking:**
- Tool: `mypy` (strict mode)
- Enabled: `strict = true`, `warn_return_any = true`, `warn_unused_ignores = true`
- All public functions MUST have type hints
- Union types use `|` syntax: `str | None`, `list[str]`
- Import TYPE_CHECKING for forward references: `if TYPE_CHECKING: from module import Type`

### Import Organization

**Order:**
1. Future imports: `from __future__ import annotations` (always first when present)
2. Standard library: `import os`, `import sys`, `from typing import Any`
3. Third-party: `import pydantic`, `import structlog`
4. Local imports: `from analysis.models import WorkflowTrace`
5. Blank lines between groups

**Example from `/Users/dylan/MyRepos/FYP/platform/analysis/src/analysis/traces.py`:**
```python
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from analysis.logger import get_logger
from analysis.models import EventRecord, WorkflowTrace

if TYPE_CHECKING:
    from analysis.database import Database
```

**Path Aliases:**
- Relative imports within packages: `from analysis.models import X` (not `from ..models import X`)
- Packages are treated as top-level in Python path (via setuptools entry in `pyproject.toml`)

### Error Handling

**Pattern:**
- Raise custom exceptions defined in `utils/exceptions.py` or package-specific exceptions module
- Never use bare `Exception` catches
- Exceptions inherit from a base package exception class

**Example from `/Users/dylan/MyRepos/FYP/demo/agent-runtime/utils/exceptions.py`:**
```python
class AgentRuntimeError(Exception):
    """Base exception for all agent-runtime errors."""

class ConfigurationError(AgentRuntimeError):
    """Configuration loading or validation error."""

class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""
```

**Usage Pattern:**
- Raise specific exceptions: `raise ConfigurationError("invalid config")`
- Catch specific exceptions: `except ConfigurationError as e:`
- Log exceptions before re-raising (if needed)

### Logging

**Framework:** `structlog` (never use `print()`)

**Setup:**
- Call `init_logging(level="INFO")` at application startup (from logger module)
- Get logger instance: `log = get_logger("module.name")`
- Logger name follows module path: `"analysis.failure_warnings"`, `"collector.database"`

**Patterns:**
- Log at INFO level for business logic events
- Use structured key-value pairs: `log.info("event_name", key=value, count=42)`
- Log context when handling errors: `log.error("operation_failed", error=str(e), workflow_id=id)`

**Example from `/Users/dylan/MyRepos/FYP/platform/analysis/src/analysis/failure_warnings.py`:**
```python
log = get_logger("analysis.failure_warnings")

# ...in function...
if warnings:
    log.info(
        "failure_warnings_extracted",
        count=len(warnings[:MAX_WARNINGS]),
        total_failed=len(failed),
        total_successful=len(successful),
    )
```

### Comments

**When to Comment:**
- Non-obvious logic only
- File header: One-line docstring describing the module (required)
- Functions: Docstrings for public functions with non-obvious behavior
- No inline comments for obvious code

**Docstrings:**
- One-line summary at file top: `"""Extract failure warnings from traces to enrich hints."""`
- Function docstrings: Brief description + what it returns
- Use simple phrasing, no deep explanation of every line

**Example from `/Users/dylan/MyRepos/FYP/platform/analysis/src/analysis/traces.py`:**
```python
"""Trace reconstruction from event_logs."""

def extract_tool_sequence(events: list[EventRecord]) -> list[str]:
    """Extract the ordered list of tool names from events.

    Filters to events where tool_name is not None, ordered by step_number.
    """
```

### Function Design

**Size:** Aim for <50 lines per function; extract helpers for long logic

**Parameters:**
- Type hints required
- Use keyword arguments for clarity on callers' side
- Pydantic models for complex data structures: `EventIn`, `OptimalPathOut`

**Return Values:**
- Explicit type hints required
- Use `|` for unions: `dict | None`
- Use structured returns (Pydantic models or NamedTuples) for multiple values

**Example from `/Users/dylan/MyRepos/FYP/platform/analysis/src/analysis/failure_warnings.py`:**
```python
def extract_failure_warnings(
    traces: list[WorkflowTrace],
    optimal_path: OptimalPath,
) -> list[str]:
    """Compare successful and failed traces to surface failure patterns.

    Returns up to MAX_WARNINGS concise natural-language warnings.
    """
```

### Module Design

**Exports:**
- Public functions/classes exposed at module level
- Use `__all__` for clarity if re-exporting from submodules

**Barrel Files:**
- Used sparingly (e.g., `analysis/__init__.py` re-exports main API)

**Example from `/Users/dylan/MyRepos/FYP/platform/analysis/src/analysis/__init__.py`:**
```python
from analysis.models import AnalysisResult, OptimalPath, Suggestion
from analysis.pipeline import run_analysis

__all__ = ["AnalysisResult", "OptimalPath", "Suggestion", "run_analysis"]
```

---

## TypeScript/React Conventions

### Naming Patterns

**Files:**
- Kebab case for component files: `delta-card.tsx`, `cost-leak-list.tsx`
- Kebab case for utilities: `layout-utils.ts`
- `.test.tsx`/`.test.ts` suffix for tests

**Functions/Components:**
- PascalCase for React components: `DeltaCard`, `ExecutionDAG`
- camelCase for utility functions: `formatCost()`, `formatDelta()`
- camelCase for hooks: `useWebSocket()`

**Variables:**
- camelCase: `apiBase`, `workflowId`, `toolSequence`
- Destructured props: `{ before, after, unit }`

**Constants:**
- UPPER_SNAKE_CASE for true constants: `API_BASE = process.env.NEXT_PUBLIC_API_URL`

### Code Style

**Formatting:**
- Tool: Tailwind CSS (not explicit formatter defined; follows default Next.js)
- Type-safe: Full TypeScript, no `any` unless unavoidable

**Linting:**
- ESLint/Prettier not explicitly configured in this codebase
- Follow conventional React patterns: prop drilling, composition over inheritance

### Import Organization

**Order:**
1. React/Next imports: `import type { ... }`, `import { ... } from "react"`
2. Third-party UI: `import { ... } from "@/components/ui/button"`
3. Local components: `import { DeltaCard } from "./delta-card"`
4. Types: `import type { OptimalPathsResponse } from "@/lib/types"`
5. Blank lines between groups

**Example from `/Users/dylan/MyRepos/FYP/dashboard/src/lib/api.ts`:**
```typescript
import type {
  ActionResponse,
  AnalyticsSummary,
  // ... other types
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:9000";
```

**Path Aliases:**
- `@/` points to `src/` (configured in `vitest.config.ts`)
- Use for all absolute imports

### Error Handling

**Pattern:**
- Throw `Error` with descriptive message
- Return error states via union types or error properties

**Example from `/Users/dylan/MyRepos/FYP/dashboard/src/lib/api.ts`:**
```typescript
async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}
```

### Logging

**Pattern:**
- Use `console.log()`, `console.error()` for debugging (not a structured logger like backend)
- Prefer React DevTools for component inspection

### Comments

**When to Comment:**
- Complex UI logic only
- No file-level comments (self-documenting code preferred)
- Inline comments for non-obvious calculations

### Component Design

**Props:**
- Define interface for component props
- Use destructuring in function signature: `{ before, after, unit }`
- No spread operator for untyped props

**Children:**
- Use `React.ReactNode` type

**Hooks:**
- Follow React hooks rules (dependencies, no conditional calls)
- Custom hooks in `/src/hooks/` directory

**Example from `/Users/dylan/MyRepos/FYP/dashboard/src/components/compare/delta-card.tsx` (inferred):**
```typescript
interface DeltaCardProps {
  label: string;
  before: number;
  after: number;
  unit: string;
  lowerIsBetter: boolean;
}

export function DeltaCard({ label, before, after, unit, lowerIsBetter }: DeltaCardProps) {
  // component body
}
```

---

## Language-Specific Standards

### Python

**Async Code:**
- Use `async def` / `await` consistently
- Async functions for I/O: database calls, HTTP requests
- Sync for pure computation
- pytest-asyncio for testing (`asyncio_mode = "auto"`)

**Pydantic Models:**
- Use v2 field defaults: `field: str | None = None`
- Validators via `@field_validator` decorator
- Use `Field(default_factory=dict)` for mutable defaults

**Database Patterns:**
- Use asyncpg for PostgreSQL connections (type-safe via Pydantic models)
- Connection pooling managed at application startup

### TypeScript

**Generics:**
- Use for reusable API functions: `async function fetchApi<T>(path: string): Promise<T>`
- Prefer explicit type params over inference in public APIs

**Optional Properties:**
- Use `| undefined` not optional field syntax (slightly more explicit)
- Null vs undefined: null for API responses, undefined for missing props

---

## Cross-Language Patterns

**Naming Consistency:**
- Both use snake_case for identifiers that cross boundaries (API request bodies): `workflow_id`, `tool_name`
- Dashboard models align with backend Pydantic models

**Data Validation:**
- Python: Pydantic at API boundaries
- TypeScript: Type checking only (runtime validation via API responses)

---

*Convention analysis: 2026-03-13*

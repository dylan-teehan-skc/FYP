# Conventions

**Updated:** 2026-03-31

## Python

- Python 3.11+, type hints on all public functions
- `ruff` for linting and formatting (line-length=100, rules: E/F/I/N/W/UP)
- `mypy` strict mode
- `structlog` for logging — never `print()`. Pattern: `log = get_logger("module.name")`, then `log.info("event_name", key=value)`
- One-line docstring at file top describing the module. Function docstrings only when non-obvious.
- No inline comments unless the logic is genuinely unclear.
- Import order: `__future__` → stdlib → third-party → local, blank lines between groups. Absolute imports only (`from analysis.models import X`, not relative).
- Custom exceptions in dedicated `exceptions.py` per package. Never bare `except Exception`.
- Pydantic v2 for all data models. `Field(default_factory=dict)` for mutable defaults. Union syntax: `str | None`.
- Async for all I/O, sync for pure computation. `pytest-asyncio` with `asyncio_mode = "auto"`.

## TypeScript/React

- TypeScript throughout, no `any` unless unavoidable
- PascalCase components, camelCase functions, kebab-case files
- TailwindCSS for styling, shadcn/ui primitives
- `@/` alias points to `src/`
- API types mirror backend Pydantic models. Snake_case in API payloads (matching Python).

## Cross-Language

- `workflow_id`, `tool_name`, `tool_sequence` — snake_case everywhere, even in JSON payloads
- Pydantic validates at API boundaries (Python), TypeScript types check at compile time

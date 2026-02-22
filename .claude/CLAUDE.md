# Self-Optimising Workflow Intelligence Platform (FYP)

Decoupled observability and optimisation platform for AI agent workflows. Captures execution traces, discovers optimal paths, feeds knowledge back to agents at runtime.

## Repository Structure

```
FYP/
├── sdk/                 # Python SDK (pip installable, what companies integrate)
├── platform/            # Backend services (collector + analysis, deployed together)
│   ├── collector/       #   FastAPI event receiver + pgvector queries
│   └── analysis/        #   Trace reconstruction, pattern detection, path optimisation
├── dashboard/           # React/Next.js frontend (separate deploy)
├── demo/                # Example consumer (proves the platform works)
│   ├── agent-runtime/   #   Async Python agent system
│   ├── mcp-tool-server/ #   FastAPI mock tools (8 customer support tools)
│   └── demo_runner.py   #   Runs the 5 NovaTech scenarios
└── docs/                # Spec, architecture, diary, demo scenario, useful links
```

## Commands

```bash
# demo agent-runtime
cd demo/agent-runtime && .venv/bin/python3 -m pytest tests/ -v          # run tests
cd demo/agent-runtime && .venv/bin/python3 -m pytest tests/ --cov=. -q  # coverage
cd demo/agent-runtime && .venv/bin/python3 -m ruff check .              # lint
cd demo/agent-runtime && .venv/bin/python3 -m ruff format .             # format
cd demo/agent-runtime && .venv/bin/python3 main.py                      # run agent

# demo mcp-tool-server
cd demo/mcp-tool-server && .venv/bin/python3 main.py                    # run MCP server
```

## Code Style

- Python 3.11+, type hints on all public functions
- Short docstrings at file top only (one line describing the file)
- No comments unless logic is non-obvious
- Imports: stdlib, third-party, local, separated by blank lines
- Exceptions in `utils/exceptions.py`, not bare Exception catches
- structlog for logging, never print()

## Workflow Rules

IMPORTANT: After making code changes, ALWAYS:
1. Run tests: `.venv/bin/python3 -m pytest tests/ -v`
2. Run lint: `.venv/bin/python3 -m ruff check .`
3. Fix any failures before considering the task complete

IMPORTANT: When making design decisions or architectural changes:
- Update `docs/diary-and-desing-choices.txt` with the current date and rationale
- Update `docs/spec.md` if the change affects project structure, components, or dependencies

IMPORTANT: Use any relevant Claude skills when they would help with the current task.

## Gotchas

- PYTHONPATH must include agent-runtime root for imports to work
- MCP server must be running on :8000 before agent-runtime starts
- Prompts live in `prompts/reasoning.txt` as plain text with XML tags, not in Python
- No max_steps limit on agents, they run until completion or loop detection
- Log files write to `logs/` relative to working directory
- Virtual envs must be activated for dependencies
- sdk/ is self-contained: companies install it independently of the platform backend
- demo/ is a separate consumer: it only imports the SDK, never from platform/

# Technology Stack

**Analysis Date:** 2026-03-13

## Languages

**Primary:**
- Python 3.11+ - Core platform services (collector, analysis), agent demos, SDK
- TypeScript 5 - Frontend dashboard with React
- SQL - PostgreSQL schema and migrations

**Secondary:**
- JavaScript - Configuration and build tooling (Next.js, Tailwind)

## Runtime

**Environment:**
- Python 3.11+ (strict requirement across all services)
- Node.js 20+ (dashboard development)
- PostgreSQL 16 with pgvector extension (database layer)

**Package Managers:**
- uv (lockfiles: `uv.lock` in Python projects)
- npm (Node.js projects)

## Frameworks

**Backend/API:**
- FastAPI 0.104+ - Core collector service (`platform/collector`)
- uvicorn 0.24+ - ASGI server for FastAPI applications
- Pydantic 2.5+ - Data validation and serialization across all Python services
- Pydantic Settings - Configuration management with environment variable loading

**Frontend:**
- Next.js 16.1.6 - React framework with server components
- React 19.2.3 - UI library
- React DOM 19.2.3 - DOM rendering
- TailwindCSS 4 - Utility-first CSS framework
- Radix UI 1.4.3 - Unstyled accessible components

**Agent/LLM Integration:**
- LiteLLM 1.0+ - Unified LLM API abstraction (supports Gemini, OpenAI, Anthropic)
- LangChain 0.3+ - Agent framework for demo (`demo/langchain`)
- LangChain Google GenAI 2.0+ - Google AI integration plugin

**Data Processing & Analysis:**
- NetworkX 3.2+ - Graph algorithms for workflow path analysis
- pm4py 2.7+ - Process mining framework
- pandas 2.1+ - Data analysis and transformation
- scipy 1.11+ - Scientific computing

**Database/Storage:**
- asyncpg 0.29+ - Async PostgreSQL driver with connection pooling
- pgvector extension - Vector similarity search support

**SDK/Client Library:**
- aiohttp 3.9+ - Async HTTP client (SDK transport layer, agent demos)

**Testing:**
- pytest 7.4+ - Testing framework (all services)
- pytest-asyncio 0.23+ - Async test support
- pytest-cov 4.1+ - Code coverage reporting
- aioresponses 0.7.6+ - Mock async HTTP responses

**Code Quality:**
- ruff 0.1+ - Fast Python linter (replaces flake8, isort)
- mypy 1.7+ - Static type checker (strict mode enabled)

**Logging:**
- structlog 24.1+ - Structured logging (all services)

**Frontend Testing:**
- Vitest 4.0.18 - Fast unit test runner
- @testing-library/react 16.3+ - React component testing
- @testing-library/jest-dom 6.9+ - DOM matchers

**Visualization:**
- Recharts 3.7+ - React charting library
- @xyflow/react 12.10.1 - Graph/DAG visualization
- dagre 0.8.5 - Graph layout engine
- framer-motion 12.34+ - Animation library

**UI Components:**
- Lucide React 0.575+ - Icon library
- clsx 2.1+ - Conditional classname utility
- tailwind-merge 3.5+ - TailwindCSS class merging
- Class Variance Authority 0.7.1 - Component variant management
- TanStack React Table 8.21.3 - Headless table component

## Key Dependencies

**Critical:**
- asyncpg - Direct PostgreSQL connectivity with proper pool management
- FastAPI - REST API framework for collector service
- Pydantic - Type-safe configuration and data models (strict mode)
- LiteLLM - Abstraction over multiple LLM providers; enables Gemini embedding generation
- structlog - Centralized logging across distributed services

**Infrastructure:**
- uvicorn - ASGI server; required for production deployment
- networkx, pm4py, scipy - Core algorithms for workflow optimization analysis
- Next.js - Modern React framework for dashboard with server-side rendering

## Configuration

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql://collector:collector_dev@localhost:5432/workflow_optimizer`)
- `EMBEDDING_MODEL` - LiteLLM embedding model (default: `gemini/gemini-embedding-001`)
- `LLM_MODEL` - LiteLLM LLM model for analysis (default: `gemini/gemini-2.5-flash-lite`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `SIMILARITY_THRESHOLD` - Workflow clustering threshold (default: varies by service)
- `MIN_EXECUTIONS` - Minimum workflow executions before optimization (default: 5)
- `GOOGLE_API_KEY` - Required for Gemini API access (set in demos)

**Build Configuration:**
- `tsconfig.json` - TypeScript configuration (dashboard)
- `pyproject.toml` - Python project metadata and dependencies (all Python projects)
- `next.config.ts` - Next.js configuration (minimal, dashboard)
- `.prettierrc` / `prettier` - Code formatting (if configured)
- `vitest.config.ts` - Frontend test configuration
- `ruff.toml` / `[tool.ruff]` in pyproject.toml - Linter configuration

## Platform Requirements

**Development:**
- Python 3.11+ with venv or uv
- PostgreSQL 16+ with pgvector extension
- Node.js 20+ with npm
- GOOGLE_API_KEY for Gemini API testing
- Docker (optional, for containerized PostgreSQL via docker-compose.yml)

**Production:**
- Python 3.11+ runtime
- PostgreSQL 16+ cluster with pgvector
- Node.js 20+ for Next.js build/serve
- Uvicorn ASGI server
- Environment variables for all services properly set

**Infrastructure Notes:**
- docker-compose.yml provides pgvector/pgvector:pg16 container
- Migrations stored in `platform/collector/migrations/` (7 migration files)
- Collector service CORS configured for `http://localhost:3000` (dashboard)

---

*Stack analysis: 2026-03-13*

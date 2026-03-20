# Codebase Concerns

**Analysis Date:** 2026-03-13

## Tech Debt

**Mode Selector Not Implemented:**
- Issue: `ModeSelector.select_mode()` always returns exploration mode with stubbed helper methods
- Files: `demo/agent-runtime/mode_selector/selector.py` (lines 39-52)
- Impact: Guided execution optimization is not functional; the system cannot retrieve optimal paths from historical workflows
- Fix approach: Implement `_find_similar_workflows()` with semantic search using pgvector embeddings, implement `_get_optimal_path()` to query workflow_graphs table, and integrate with analytics database

**Bare Exception Handling:**
- Issue: Multiple catch-all `except Exception` blocks that swallow errors without context
- Files:
  - `platform/collector/src/collector/websocket.py` (line 48)
  - `platform/collector/src/collector/embeddings.py` (line 29)
  - `platform/analysis/src/analysis/graph.py` (lines 51, 82)
- Impact: Failures are logged but errors propagate silently; operators cannot diagnose why embeddings or process discovery failed
- Fix approach: Replace with specific exception types, add error context to logs (e.g., what input caused the failure), and consider retry logic for transient failures (especially for embedding generation)

**WebSocket Connection Manager Exception Handling:**
- Issue: `ConnectionManager.broadcast()` silently discards dead connections without logging which clients failed
- Files: `platform/collector/src/collector/websocket.py` (lines 46-54)
- Impact: Silent client disconnections may go unnoticed; operators cannot debug WebSocket delivery issues
- Fix approach: Log client disconnection events with connection metadata, track reconnection patterns, add per-client error tracking

**Assertions in Production Code:**
- Issue: Multiple runtime assertions using `assert self._pool is not None` instead of proper null checks
- Files: `platform/collector/src/collector/database.py` (lines 56, 61, 66, 71, 96)
- Impact: Assertions are disabled with `-O` flag; code will crash with AttributeError instead of providing context
- Fix approach: Replace assertions with proper runtime checks and raise `RuntimeError` or custom `DatabaseError` with context

**Database Connection Pool Initialization Risk:**
- Issue: Database pool is checked but never validated to be connected before use
- Files: `platform/collector/src/collector/database.py` (line 96)
- Impact: If pool becomes None or is closed, queries will fail with cryptic asyncpg errors instead of connection-specific errors
- Fix approach: Add health checks and raise `ConnectionError` explicitly if pool is unavailable; add connection state validation

**Embedding Generation Failure Degradation:**
- Issue: `EmbeddingService.generate()` returns None on any error; callers must handle None gracefully
- Files: `platform/collector/src/collector/embeddings.py` (lines 16-31)
- Impact: Workflow clustering depends on embeddings; missing embeddings silently degrade optimization quality with no warning
- Fix approach: Return error details alongside embedding, track degradation in metrics, alert on high failure rates

## Known Bugs

**Mode Selector Loop Detection Threshold Bug:**
- Symptoms: Agent may exit with premature loop detection due to tight threshold
- Files: `demo/agent-runtime/mode_selector/selector.py` (line 24-26)
- Trigger: Set `loop_detection_threshold=3, loop_detection_window=5` (defaults in selector) but agent also has `loop_threshold=3` causing double-counting
- Workaround: Keep thresholds synchronized; review `demo/agent-runtime/agent/agent.py` line 19-20
- Root cause: Configuration is scattered across two classes without centralized validation

**WebSocket Broadcast Missing Error Context:**
- Symptoms: Dead WebSocket connections detected but removed without logging why they failed
- Files: `platform/collector/src/collector/websocket.py` (line 48)
- Trigger: Network partition or client crash while broadcast is in progress
- Workaround: Clients must re-establish connection manually; no heartbeat mechanism exists
- Root cause: No exception type checking to distinguish network errors from protocol errors

## Security Considerations

**Database Query String Formatting:**
- Risk: While asyncpg uses parameterized queries, embedding vector is coerced to string
- Files: `platform/collector/src/collector/database.py` (line 178, 154)
- Current mitigation: Parametrized queries prevent SQL injection, but vector serialization is ad-hoc
- Recommendations:
  - Add schema validation for vector format before database insertion
  - Use pgvector type safely (ensure JSON serialization matches expected format)
  - Add query plan analysis for embedding queries to catch parameter binding issues

**LiteLLM Dependency for Embeddings:**
- Risk: Embedding service is optional but silently degrades if LiteLLM import fails
- Files: `platform/collector/src/collector/embeddings.py` (line 19)
- Current mitigation: Graceful None return, logging
- Recommendations:
  - Make embedding provider configurable at startup
  - Validate API keys before accepting embedding requests
  - Add circuit breaker to prevent hammering API on repeated failures
  - Track embedding service health in metrics

**API Rate Limiting Not Implemented:**
- Risk: Endpoints expose aggregation queries that could be expensive over large datasets
- Files: `platform/collector/src/collector/routes/dashboard.py`, `routes/optimize.py`
- Current mitigation: None detected
- Recommendations:
  - Add rate limiting per client/workflow_id
  - Implement query timeouts for dashboard aggregations
  - Cache large analytics queries with TTL

## Performance Bottlenecks

**Database Aggregation Query Complexity:**
- Problem: `get_mode_comparison()` query is complex with multiple JOINs and window functions
- Files: `platform/collector/src/collector/database.py` (lines 342-402)
- Cause: SQL computes all metrics for both exploration and guided modes in single query; over 50 lines of SQL
- Improvement path:
  - Add materialized view for pre-aggregated mode metrics
  - Index on (workflow_id, activity, status) for mode_map subquery
  - Consider separate simpler queries if analytics query SLA is not critical
  - Profile query plan on large event logs (>1M rows)

**WebSocket Broadcast Loop:**
- Problem: Each event is broadcast sequentially in `broadcast_batch()`
- Files: `platform/collector/src/collector/websocket.py` (lines 56-58)
- Cause: For N events and M connections, O(N*M) send operations
- Improvement path:
  - Batch WebSocket sends using asyncio.gather()
  - Only broadcast events matching subscriber filters at send time
  - Consider connection pooling per workflow_id for faster filtering

**Analysis Pipeline Synchronous PM4Py Calls:**
- Problem: Process discovery and fitness computation block async context
- Files: `platform/analysis/src/analysis/pipeline.py` (lines 32-95), `platform/analysis/src/analysis/graph.py` (lines 25-84)
- Cause: PM4Py is CPU-bound; large trace datasets (1000+ events) cause task stalls
- Improvement path:
  - Move PM4Py processing to separate executor pool with `asyncio.to_thread()`
  - Add sampling for large traces before discovery
  - Cache discovered process models per task_cluster
  - Implement timeout to skip discovery if >5 seconds

**Dashboard Query N+1 Pattern:**
- Problem: Mode comparison queries may recompute for each dashboard page load
- Files: `platform/collector/src/collector/routes/dashboard.py` (calls `get_mode_comparison()`)
- Cause: No caching strategy visible
- Improvement path:
  - Cache aggregations for 60 seconds with cache invalidation on event insert
  - Use Redis or in-memory cache with TTL
  - Add cache hit/miss metrics

## Fragile Areas

**Event Schema Evolution:**
- Files: `platform/collector/src/collector/models.py`, `sdk/src/workflow_optimizer/models.py`
- Why fragile: EventIn has 34 fields; any schema change requires migration across SDK and collector
- Safe modification:
  - Use version field in event schema to support multiple versions in parallel
  - Make new fields optional with defaults
  - Add schema validation tests to catch incompatibilities
- Test coverage: No explicit schema versioning tests found

**Composite MCP Client Primary Selection:**
- Files: `demo/fulfillment/runner/composite_client.py` (lines 23-27)
- Why fragile: Primary client selection uses first-connected heuristic; no explicit configuration
- Safe modification:
  - Add primary_name parameter to __init__
  - Validate primary exists before returning
  - Add logging for primary selection
- Test coverage: No tests for multi-client fallback scenarios

**Optimal Path Response Optional Fields:**
- Files: `platform/collector/src/collector/models.py` (lines 67-78), `sdk/src/workflow_optimizer/models.py` (lines 66-77)
- Why fragile: Multiple optional fields with different combinations; unclear which are always present
- Safe modification:
  - Document guarantee for each mode ("exploration" has no path, "guided" must have path+confidence)
  - Add validation in __init__ to enforce mode-specific requirements
  - Add test cases for each response type
- Test coverage: No response schema validation tests detected

**Database Type Coercion:**
- Files: `platform/collector/src/collector/database.py` (lines 124, 154, 178)
- Why fragile: UUID and embedding vectors coerced to strings for parameter passing
- Safe modification:
  - Use asyncpg's UUID type support directly
  - Verify pgvector type codec registration on connection
  - Add type validation in insert methods
- Test coverage: Type coercion not covered by unit tests

## Scaling Limits

**PostgreSQL Connection Pool Size:**
- Current capacity: min_size=2, max_size=10 per `platform/collector/src/collector/database.py` line 20
- Limit: With concurrent event batching (batch size could be large), pool exhaustion at 100+ concurrent writers
- Scaling path:
  - Profile actual concurrent load; increase to min_size=5, max_size=50 for production
  - Implement connection pool metrics (active/idle/waiting connections)
  - Add adaptive pool sizing based on queue depth
  - Use connection pooler proxy (pgbouncer) for multi-process deployments

**Embedding Vector Dimension:**
- Current capacity: 768 dimensions per `platform/collector/src/collector/embeddings.py` line 24
- Limit: pgvector similarity search becomes expensive >1000 dimensions; database size grows with each embedding
- Scaling path:
  - Monitor embedding generation latency as workflow count grows
  - Consider dimensionality reduction (PCA) to 384 dims
  - Implement embedding caching/deduplication by task hash
  - Use approximate search (IVFFlat index) for large embedding tables

**Process Model Discovery Memory:**
- Current capacity: Scales with trace count and workflow complexity
- Limit: PM4Py Inductive Miner can take minutes on 1000+ event traces
- Scaling path:
  - Add trace sampling (keep 100 representative traces per cluster)
  - Implement timeout with graceful degradation (return partial graph)
  - Consider lighter discovery algorithms (heuristic miner) for large traces
  - Move to separate analysis worker pool

**Event Log Table Size:**
- Current capacity: Unbounded event insertion with no cleanup
- Limit: Table will grow indefinitely; queries will slow as size grows
- Scaling path:
  - Implement time-based partitioning (monthly tables)
  - Archive old events to cold storage
  - Add retention policy (keep 90 days hot, 1 year warm)
  - Implement event sampling/summarization for old workflow logs

## Dependencies at Risk

**LiteLLM Embedding Model Dependency:**
- Risk: Hardcoded to `gemini/gemini-embedding-001`; if Gemini API changes or becomes unavailable, all workflow clustering stops
- Files: `platform/collector/src/collector/embeddings.py` (line 13)
- Impact: Guided optimization becomes unavailable; system degrades to exploration-only mode
- Migration plan:
  - Make embedding model configurable via environment variable
  - Support fallback models (e.g., "text-embedding-3-small" from OpenAI)
  - Add model health check on startup
  - Cache embeddings to reduce API dependency

**PM4Py Process Mining:**
- Risk: PM4Py is actively maintained but may have breaking changes; Inductive Miner can fail on edge cases
- Files: `platform/analysis/src/analysis/graph.py` (line 48)
- Impact: Analysis pipeline skips process discovery if PM4Py fails, lowering optimization quality
- Migration plan:
  - Pin PM4Py version in pyproject.toml with upper bound
  - Add test cases for known problematic trace patterns
  - Implement fallback to simpler heuristic miner if Inductive fails
  - Monitor discovery failure rate

**structlog Logging Framework:**
- Risk: Custom logging setup may not support all standard Python logging handlers; debugging is difficult
- Files: `demo/agent-runtime/utils/logger.py`, `platform/analysis/src/analysis/logger.py`
- Impact: Operators may miss critical logs if handler setup fails silently
- Migration plan:
  - Document exact logging output format and handlers
  - Add logging integration tests
  - Support standard JSON logging format for centralized log aggregation

## Missing Critical Features

**No Circuit Breaker for External APIs:**
- Problem: Embedding generation and LiteLLM calls have no retry or backoff strategy
- Blocks: If Gemini API is down, all new workflows fail to cluster
- Recommendation: Add circuit breaker pattern with exponential backoff and fallback to cached embeddings

**No Workflow Trace Cleanup/Pruning:**
- Problem: Event logs grow unbounded; no data retention policy
- Blocks: Long-term cost/performance degrades; analytics queries slow
- Recommendation: Implement time-based partitioning and archive strategy

**No Observability of Mode Selector:**
- Problem: Mode selector always returns exploration; no metrics on guided vs exploration performance
- Blocks: Cannot measure optimization effectiveness or debug why guided mode isn't used
- Recommendation: Log mode selection decision with task similarity score and path quality metrics

**No Health Checks for External Dependencies:**
- Problem: Embedding service, process mining, and database have no liveness probes
- Blocks: System may report healthy while dependent services are down
- Recommendation: Add /health endpoint that checks database, embedding service, and analysis pipeline

**No API Documentation:**
- Problem: Collector endpoints lack OpenAPI schema; integration surface is unclear
- Blocks: Dashboard and SDK development are error-prone
- Recommendation: Add FastAPI OpenAPI integration with Swagger UI

## Test Coverage Gaps

**Mode Selector Logic:**
- What's not tested: Threshold comparison, semantic search ranking, path selection criteria
- Files: `demo/agent-runtime/mode_selector/selector.py` (entire file is stubbed)
- Risk: When implementation is added, logic errors will not be caught by tests
- Priority: High — blocking feature for optimization

**Database Connection Pool Failure Modes:**
- What's not tested: Pool exhaustion, connection timeout, reconnection after network partition
- Files: `platform/collector/src/collector/database.py`
- Risk: Production will experience unhandled pool errors
- Priority: High — critical for reliability

**WebSocket Connection Lifecycle:**
- What's not tested: Client connect/disconnect races, broadcast while connecting, reconnection
- Files: `platform/collector/src/collector/websocket.py`
- Risk: WebSocket delivery may fail silently under concurrent load
- Priority: Medium — impacts real-time dashboard updates

**Embedding Generation Failure Handling:**
- What's not tested: API timeout, rate limiting, malformed response handling
- Files: `platform/collector/src/collector/embeddings.py`, integration with database
- Risk: Embedding failures cascade to clustering failures with no visibility
- Priority: Medium — impacts optimization quality

**Database Type Coercion:**
- What's not tested: UUID string parsing, vector format validation, edge cases in tuple unpacking
- Files: `platform/collector/src/collector/database.py` (lines 124, 154, 178)
- Risk: Type errors in production on unexpected data shapes
- Priority: Medium — affects data integrity

**Process Model Discovery Edge Cases:**
- What's not tested: Empty traces, single-event traces, circular process discovery
- Files: `platform/analysis/src/analysis/graph.py` (lines 25-53)
- Risk: Analysis pipeline fails silently on edge cases
- Priority: Low — graceful degradation is implemented

---

*Concerns audit: 2026-03-13*

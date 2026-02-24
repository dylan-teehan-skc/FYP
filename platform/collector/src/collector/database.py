"""Async PostgreSQL database layer using asyncpg."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from collector.logger import get_logger

log = get_logger("collector.database")


class Database:
    """Connection pool wrapper with domain-specific query methods."""

    def __init__(self, dsn: str, min_size: int = 2, max_size: int = 10) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create the connection pool."""
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            init=self._init_connection,
        )
        log.info("database_connected", dsn=self._dsn.split("@")[-1])

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            log.info("database_disconnected")

    @staticmethod
    async def _init_connection(conn: asyncpg.Connection) -> None:
        """Register custom type codecs (JSONB) on each new connection."""
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
            format="text",
        )

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a query and return the status string."""
        assert self._pool is not None
        return await self._pool.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Execute a query and return all rows."""
        assert self._pool is not None
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Execute a query and return a single row."""
        assert self._pool is not None
        return await self._pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Execute a query and return a single value."""
        assert self._pool is not None
        return await self._pool.fetchval(query, *args)

    # === Domain-specific methods ===

    async def insert_event(self, event: dict[str, Any]) -> None:
        """Insert a single event into event_logs."""
        await self.execute(
            """INSERT INTO event_logs (
                event_id, workflow_id, timestamp, activity,
                agent_name, agent_role, tool_name, tool_parameters, tool_response,
                llm_model, llm_prompt_tokens, llm_completion_tokens, llm_reasoning,
                duration_ms, cost_usd, status, error_message,
                step_number, parent_event_id
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9,
                $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
            )""",
            *_event_to_args(event),
        )

    async def insert_events_batch(self, events: list[dict[str, Any]]) -> None:
        """Bulk insert events using executemany for performance."""
        if not events:
            return
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO event_logs (
                    event_id, workflow_id, timestamp, activity,
                    agent_name, agent_role, tool_name, tool_parameters, tool_response,
                    llm_model, llm_prompt_tokens, llm_completion_tokens, llm_reasoning,
                    duration_ms, cost_usd, status, error_message,
                    step_number, parent_event_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9,
                    $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
                )""",
                [_event_to_args(e) for e in events],
            )

    async def get_workflow_trace(self, workflow_id: str) -> list[asyncpg.Record]:
        """Fetch all events for a workflow, ordered by step_number."""
        return await self.fetch(
            """SELECT
                event_id::text, workflow_id::text, timestamp, activity,
                agent_name, agent_role, tool_name, tool_parameters, tool_response,
                llm_model, llm_prompt_tokens, llm_completion_tokens, llm_reasoning,
                duration_ms, cost_usd, status, error_message,
                step_number, parent_event_id::text
            FROM event_logs
            WHERE workflow_id = $1
            ORDER BY step_number, timestamp""",
            UUID(workflow_id),
        )

    async def upsert_embedding(
        self,
        workflow_id: str,
        task_description: str,
        embedding: list[float],
        model_version: str,
    ) -> None:
        """Insert or update a workflow embedding."""
        await self.execute(
            """INSERT INTO workflow_embeddings
                (workflow_id, task_description, embedding, model_version)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (workflow_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                model_version = EXCLUDED.model_version,
                created_at = NOW()
            """,
            UUID(workflow_id),
            task_description,
            str(embedding),
            model_version,
        )

    async def find_similar_paths(
        self,
        embedding: list[float],
        min_executions: int = 30,
        min_success_rate: float = 0.85,
    ) -> asyncpg.Record | None:
        """Semantic search for optimal path using pgvector cosine similarity."""
        return await self.fetchrow(
            """SELECT
                tool_sequence, avg_duration_ms, avg_steps,
                success_rate, execution_count,
                1 - (embedding <=> $1::vector) AS similarity
            FROM optimal_paths
            WHERE execution_count >= $2
              AND success_rate >= $3
            ORDER BY embedding <=> $1::vector
            LIMIT 1
            """,
            str(embedding),
            min_executions,
            min_success_rate,
        )

    async def get_analytics_summary(self) -> dict[str, Any]:
        """Aggregate metrics across all workflows."""
        row = await self.fetchrow(
            """SELECT
                COUNT(DISTINCT workflow_id) AS total_workflows,
                COUNT(*) AS total_events,
                AVG(duration_ms)
                    FILTER (WHERE activity = 'workflow:complete') AS avg_duration_ms,
                AVG(step_number)
                    FILTER (WHERE activity = 'workflow:complete') AS avg_steps,
                AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE activity LIKE 'workflow:%%') AS success_rate
            FROM event_logs
            """
        )
        top_tools = await self.fetch(
            """SELECT tool_name, COUNT(*) AS call_count,
                AVG(duration_ms) AS avg_duration_ms
            FROM event_logs
            WHERE tool_name IS NOT NULL
            GROUP BY tool_name
            ORDER BY call_count DESC
            LIMIT 10
            """
        )
        return {
            "total_workflows": row["total_workflows"] if row else 0,
            "total_events": row["total_events"] if row else 0,
            "avg_duration_ms": (
                float(row["avg_duration_ms"]) if row and row["avg_duration_ms"] else None
            ),
            "avg_steps": float(row["avg_steps"]) if row and row["avg_steps"] else None,
            "success_rate": (
                float(row["success_rate"]) if row and row["success_rate"] else None
            ),
            "top_tools": [
                {
                    "tool_name": r["tool_name"],
                    "call_count": r["call_count"],
                    "avg_duration_ms": float(r["avg_duration_ms"]),
                }
                for r in top_tools
            ],
        }


    # === Dashboard query methods ===

    async def list_workflows(self, limit: int, offset: int) -> dict[str, Any]:
        """Paginated list of completed workflows with basic stats."""
        rows = await self.fetch(
            """SELECT
                el.workflow_id::text,
                we.task_description,
                el.status,
                el.duration_ms,
                el.step_number  AS steps,
                el.timestamp,
                EXISTS(
                    SELECT 1 FROM event_logs m
                    WHERE m.workflow_id = el.workflow_id
                      AND m.activity = 'optimize:guided'
                ) AS is_guided
            FROM event_logs el
            LEFT JOIN workflow_embeddings we ON we.workflow_id = el.workflow_id
            WHERE el.activity = 'workflow:complete'
            ORDER BY el.timestamp DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        total_row = await self.fetchrow(
            "SELECT COUNT(*) AS cnt FROM event_logs WHERE activity = 'workflow:complete'"
        )
        return {
            "workflows": [dict(r) for r in rows],
            "total": total_row["cnt"] if total_row else 0,
        }

    async def list_optimal_paths(self) -> list[asyncpg.Record]:
        """Fetch all rows from the optimal_paths table."""
        return await self.fetch(
            """SELECT
                task_cluster,
                tool_sequence,
                avg_duration_ms,
                avg_steps,
                success_rate,
                execution_count,
                updated_at
            FROM optimal_paths
            ORDER BY execution_count DESC
            """
        )

    async def get_mode_distribution(self) -> dict[str, int]:
        """Count guided vs exploration optimize events."""
        rows = await self.fetch(
            """SELECT activity, COUNT(*) AS cnt
            FROM event_logs
            WHERE activity IN ('optimize:guided', 'optimize:exploration')
            GROUP BY activity
            """
        )
        counts: dict[str, int] = {"optimize:guided": 0, "optimize:exploration": 0}
        for r in rows:
            counts[r["activity"]] = r["cnt"]
        return {
            "guided": counts["optimize:guided"],
            "exploration": counts["optimize:exploration"],
            "total": counts["optimize:guided"] + counts["optimize:exploration"],
        }

    async def get_mode_comparison(self) -> dict[str, Any]:
        """Aggregate duration, steps, and success rate split by mode."""
        row = await self.fetchrow(
            """WITH mode_map AS (
                SELECT
                    workflow_id,
                    MAX(CASE WHEN activity = 'optimize:guided' THEN 1 ELSE 0 END) AS is_guided
                FROM event_logs
                WHERE activity IN ('optimize:guided', 'optimize:exploration')
                GROUP BY workflow_id
            )
            SELECT
                AVG(el.duration_ms)  FILTER (WHERE mm.is_guided = 0) AS exp_avg_duration,
                AVG(el.step_number)  FILTER (WHERE mm.is_guided = 0) AS exp_avg_steps,
                AVG(CASE WHEN el.status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE mm.is_guided = 0) AS exp_success_rate,
                COUNT(*) FILTER (WHERE mm.is_guided = 0) AS exp_count,
                AVG(el.duration_ms)  FILTER (WHERE mm.is_guided = 1) AS gui_avg_duration,
                AVG(el.step_number)  FILTER (WHERE mm.is_guided = 1) AS gui_avg_steps,
                AVG(CASE WHEN el.status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE mm.is_guided = 1) AS gui_success_rate,
                COUNT(*) FILTER (WHERE mm.is_guided = 1) AS gui_count
            FROM event_logs el
            JOIN mode_map mm ON mm.workflow_id = el.workflow_id
            WHERE el.activity = 'workflow:complete'
            """
        )

        def _f(v: Any) -> float | None:
            return float(v) if v is not None else None

        if row is None:
            empty = {"avg_duration_ms": None, "avg_steps": None, "success_rate": None, "count": 0}
            return {"exploration": empty, "guided": empty}

        return {
            "exploration": {
                "avg_duration_ms": _f(row["exp_avg_duration"]),
                "avg_steps": _f(row["exp_avg_steps"]),
                "success_rate": _f(row["exp_success_rate"]),
                "count": row["exp_count"] or 0,
            },
            "guided": {
                "avg_duration_ms": _f(row["gui_avg_duration"]),
                "avg_steps": _f(row["gui_avg_steps"]),
                "success_rate": _f(row["gui_success_rate"]),
                "count": row["gui_count"] or 0,
            },
        }

    async def get_timeline(self) -> list[asyncpg.Record]:
        """Daily aggregate metrics grouped by UTC date."""
        return await self.fetch(
            """WITH mode_map AS (
                SELECT
                    workflow_id,
                    MAX(CASE WHEN activity = 'optimize:guided' THEN 1 ELSE 0 END) AS is_guided
                FROM event_logs
                WHERE activity IN ('optimize:guided', 'optimize:exploration')
                GROUP BY workflow_id
            )
            SELECT
                DATE_TRUNC('day', el.timestamp)::date AS date,
                COUNT(*) AS workflows,
                AVG(el.duration_ms) AS avg_duration_ms,
                AVG(CASE WHEN el.status = 'success' THEN 1.0 ELSE 0.0 END) AS success_rate,
                AVG(COALESCE(mm.is_guided, 0)::float) AS guided_pct
            FROM event_logs el
            LEFT JOIN mode_map mm ON mm.workflow_id = el.workflow_id
            WHERE el.activity = 'workflow:complete'
            GROUP BY DATE_TRUNC('day', el.timestamp)::date
            ORDER BY date
            """
        )

    async def get_execution_graph(self) -> dict[str, Any]:
        """Build tool-to-tool transition graph from event_logs."""
        tool_rows = await self.fetch(
            """SELECT
                tool_name,
                COUNT(*) AS call_count,
                AVG(duration_ms) AS avg_duration_ms
            FROM event_logs
            WHERE tool_name IS NOT NULL
              AND activity LIKE 'tool_call:%%'
            GROUP BY tool_name
            """
        )
        seq_rows = await self.fetch(
            """SELECT workflow_id, tool_name, step_number
            FROM event_logs
            WHERE tool_name IS NOT NULL
              AND activity LIKE 'tool_call:%%'
            ORDER BY workflow_id, step_number
            """
        )

        from collections import defaultdict

        edge_counts: dict[tuple[str, str], int] = defaultdict(int)
        prev_wf: str | None = None
        prev_tool: str | None = None
        for r in seq_rows:
            wf = str(r["workflow_id"])
            tool = r["tool_name"]
            if prev_wf == wf and prev_tool is not None:
                edge_counts[(prev_tool, tool)] += 1
            prev_wf = wf
            prev_tool = tool

        nodes = [
            {
                "id": r["tool_name"],
                "label": r["tool_name"],
                "avg_duration_ms": float(r["avg_duration_ms"]) if r["avg_duration_ms"] else None,
                "call_count": r["call_count"],
            }
            for r in tool_rows
        ]
        edges = [
            {"source": src, "target": tgt, "weight": w}
            for (src, tgt), w in edge_counts.items()
        ]
        return {"nodes": nodes, "edges": edges}

    async def get_bottlenecks(self) -> list[asyncpg.Record]:
        """Per-tool aggregate stats for bottleneck detection."""
        return await self.fetch(
            """SELECT
                tool_name,
                COUNT(*) AS call_count,
                AVG(duration_ms) AS avg_duration_ms,
                SUM(cost_usd) AS total_cost_usd,
                COUNT(*)::float / NULLIF(COUNT(DISTINCT workflow_id), 0) AS avg_calls_per_workflow
            FROM event_logs
            WHERE tool_name IS NOT NULL
              AND activity LIKE 'tool_call:%%'
            GROUP BY tool_name
            ORDER BY avg_duration_ms DESC NULLS LAST
            """
        )

    async def list_task_clusters(self) -> list[asyncpg.Record]:
        """Fetch all task clusters with summary stats and matching workflow count."""
        return await self.fetch(
            """SELECT
                op.path_id::text,
                op.task_cluster,
                op.tool_sequence,
                op.avg_duration_ms,
                op.avg_steps,
                op.success_rate,
                op.execution_count,
                op.updated_at,
                (
                    SELECT COUNT(*)
                    FROM workflow_embeddings we
                    WHERE op.embedding IS NOT NULL
                      AND we.embedding IS NOT NULL
                      AND 1 - (we.embedding <=> op.embedding) >= 0.60
                ) AS workflow_count
            FROM optimal_paths op
            ORDER BY op.execution_count DESC
            """
        )

    async def get_cluster_workflows(
        self,
        path_id: str,
        similarity_threshold: float = 0.60,
    ) -> dict[str, Any]:
        """Get optimal path and all matching workflows for a task cluster."""
        path_row = await self.fetchrow(
            """SELECT
                path_id::text, task_cluster, tool_sequence,
                avg_duration_ms, avg_steps, success_rate,
                execution_count, embedding, updated_at
            FROM optimal_paths
            WHERE path_id = $1
            """,
            UUID(path_id),
        )
        if path_row is None:
            return {"path": None, "workflows": [], "mode_stats": None}

        embedding = path_row["embedding"]
        if embedding is None:
            return {"path": dict(path_row), "workflows": [], "mode_stats": None}

        workflow_rows = await self.fetch(
            """WITH matched_workflows AS (
                SELECT
                    we.workflow_id,
                    we.task_description,
                    1 - (we.embedding <=> $1::vector) AS similarity
                FROM workflow_embeddings we
                WHERE we.embedding IS NOT NULL
                  AND 1 - (we.embedding <=> $1::vector) >= $2
            ),
            mode_map AS (
                SELECT
                    workflow_id,
                    MAX(CASE WHEN activity = 'optimize:guided' THEN 1 ELSE 0 END) AS is_guided
                FROM event_logs
                WHERE activity IN ('optimize:guided', 'optimize:exploration')
                GROUP BY workflow_id
            )
            SELECT
                mw.workflow_id::text,
                mw.task_description,
                mw.similarity,
                el.status,
                el.duration_ms,
                el.step_number AS steps,
                el.timestamp,
                COALESCE(mm.is_guided, 0) AS is_guided,
                cost_agg.total_cost_usd
            FROM matched_workflows mw
            JOIN event_logs el ON el.workflow_id = mw.workflow_id
                AND el.activity = 'workflow:complete'
            LEFT JOIN mode_map mm ON mm.workflow_id = mw.workflow_id
            LEFT JOIN LATERAL (
                SELECT SUM(cost_usd) AS total_cost_usd
                FROM event_logs
                WHERE workflow_id = mw.workflow_id
            ) cost_agg ON true
            ORDER BY el.timestamp DESC
            """,
            str(embedding),
            similarity_threshold,
        )

        mode_stats_row = await self.fetchrow(
            """WITH matched_workflows AS (
                SELECT we.workflow_id
                FROM workflow_embeddings we
                WHERE we.embedding IS NOT NULL
                  AND 1 - (we.embedding <=> $1::vector) >= $2
            ),
            mode_map AS (
                SELECT
                    workflow_id,
                    MAX(CASE WHEN activity = 'optimize:guided' THEN 1 ELSE 0 END) AS is_guided
                FROM event_logs
                WHERE activity IN ('optimize:guided', 'optimize:exploration')
                GROUP BY workflow_id
            )
            SELECT
                AVG(el.duration_ms)
                    FILTER (WHERE COALESCE(mm.is_guided, 0) = 0) AS exp_avg_duration,
                AVG(el.step_number)
                    FILTER (WHERE COALESCE(mm.is_guided, 0) = 0) AS exp_avg_steps,
                AVG(CASE WHEN el.status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE COALESCE(mm.is_guided, 0) = 0) AS exp_success_rate,
                COUNT(*) FILTER (WHERE COALESCE(mm.is_guided, 0) = 0) AS exp_count,
                AVG(el.duration_ms) FILTER (WHERE mm.is_guided = 1) AS gui_avg_duration,
                AVG(el.step_number) FILTER (WHERE mm.is_guided = 1) AS gui_avg_steps,
                AVG(CASE WHEN el.status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE mm.is_guided = 1) AS gui_success_rate,
                COUNT(*) FILTER (WHERE mm.is_guided = 1) AS gui_count
            FROM matched_workflows mw
            JOIN event_logs el ON el.workflow_id = mw.workflow_id
                AND el.activity = 'workflow:complete'
            LEFT JOIN mode_map mm ON mm.workflow_id = mw.workflow_id
            """,
            str(embedding),
            similarity_threshold,
        )

        return {
            "path": dict(path_row),
            "workflows": [dict(r) for r in workflow_rows],
            "mode_stats": dict(mode_stats_row) if mode_stats_row else None,
        }

    async def get_savings(self) -> dict[str, Any]:
        """Calculate cumulative time and cost savings (guided vs exploration)."""
        row = await self.fetchrow(
            """WITH mode_map AS (
                SELECT
                    workflow_id,
                    MAX(CASE WHEN activity = 'optimize:guided' THEN 1 ELSE 0 END) AS is_guided
                FROM event_logs
                WHERE activity IN ('optimize:guided', 'optimize:exploration')
                GROUP BY workflow_id
            ),
            cost_by_wf AS (
                SELECT
                    el.workflow_id,
                    mm.is_guided,
                    MAX(el.duration_ms)
                        FILTER (WHERE el.activity = 'workflow:complete') AS duration_ms,
                    MAX(el.step_number)
                        FILTER (WHERE el.activity = 'workflow:complete') AS steps,
                    MAX(el.status)
                        FILTER (WHERE el.activity = 'workflow:complete') AS status,
                    SUM(el.cost_usd) AS total_cost_usd
                FROM event_logs el
                JOIN mode_map mm ON mm.workflow_id = el.workflow_id
                GROUP BY el.workflow_id, mm.is_guided
            )
            SELECT
                AVG(duration_ms) FILTER (WHERE is_guided = 0) AS exp_avg_duration,
                AVG(steps)       FILTER (WHERE is_guided = 0) AS exp_avg_steps,
                AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE is_guided = 0) AS exp_success_rate,
                AVG(total_cost_usd) FILTER (WHERE is_guided = 0) AS exp_avg_cost,
                AVG(duration_ms) FILTER (WHERE is_guided = 1) AS gui_avg_duration,
                AVG(steps)       FILTER (WHERE is_guided = 1) AS gui_avg_steps,
                AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE is_guided = 1) AS gui_success_rate,
                AVG(total_cost_usd) FILTER (WHERE is_guided = 1) AS gui_avg_cost,
                COUNT(*) FILTER (WHERE is_guided = 1) AS guided_count
            FROM cost_by_wf
            """
        )

        def _f(v: Any) -> float:
            return float(v) if v is not None else 0.0

        if row is None:
            return {
                "time_saved_ms": 0.0,
                "cost_saved_usd": 0.0,
                "pct_duration_improvement": 0.0,
                "pct_steps_improvement": 0.0,
                "pct_success_improvement": 0.0,
            }

        exp_dur = _f(row["exp_avg_duration"])
        gui_dur = _f(row["gui_avg_duration"])
        exp_steps = _f(row["exp_avg_steps"])
        gui_steps = _f(row["gui_avg_steps"])
        exp_succ = _f(row["exp_success_rate"])
        gui_succ = _f(row["gui_success_rate"])
        exp_cost = _f(row["exp_avg_cost"])
        gui_cost = _f(row["gui_avg_cost"])
        guided_count = int(row["guided_count"] or 0)

        time_saved = (exp_dur - gui_dur) * guided_count
        cost_saved = (exp_cost - gui_cost) * guided_count

        def _pct(baseline: float, improved: float) -> float:
            if baseline == 0.0:
                return 0.0
            return round((baseline - improved) / baseline * 100, 2)

        return {
            "time_saved_ms": max(time_saved, 0.0),
            "cost_saved_usd": max(cost_saved, 0.0),
            "pct_duration_improvement": _pct(exp_dur, gui_dur),
            "pct_steps_improvement": _pct(exp_steps, gui_steps),
            "pct_success_improvement": _pct(1.0 - exp_succ, 1.0 - gui_succ),
        }


def _to_uuid(value: Any) -> UUID:
    """Convert a string or UUID to UUID (idempotent)."""
    return value if isinstance(value, UUID) else UUID(value)


def _event_to_args(event: dict[str, Any]) -> list[Any]:
    """Convert event dict to positional args for INSERT query."""
    return [
        _to_uuid(event["event_id"]),
        _to_uuid(event["workflow_id"]),
        event["timestamp"],
        event["activity"],
        event["agent_name"],
        event["agent_role"],
        event.get("tool_name"),
        event.get("tool_parameters", {}),
        event.get("tool_response", {}),
        event.get("llm_model", ""),
        event.get("llm_prompt_tokens", 0),
        event.get("llm_completion_tokens", 0),
        event.get("llm_reasoning", ""),
        event.get("duration_ms", 0.0),
        Decimal(str(event.get("cost_usd", 0.0))),
        event.get("status", "success"),
        event.get("error_message"),
        event.get("step_number", 0),
        _to_uuid(event["parent_event_id"]) if event.get("parent_event_id") else None,
    ]

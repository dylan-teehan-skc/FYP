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
            "SELECT * FROM event_logs WHERE workflow_id = $1 ORDER BY step_number, timestamp",
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

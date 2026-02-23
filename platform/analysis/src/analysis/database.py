"""Async PostgreSQL database layer for the analysis engine."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg

from analysis.logger import get_logger

log = get_logger("analysis.database")


class Database:
    """Connection pool wrapper with read/write query methods for analysis."""

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

    # --- Read methods ---

    async def fetch_all_workflow_ids(self) -> list[str]:
        """Return all distinct workflow_ids from event_logs."""
        assert self._pool is not None
        rows = await self._pool.fetch(
            "SELECT DISTINCT workflow_id FROM event_logs ORDER BY workflow_id"
        )
        return [str(r["workflow_id"]) for r in rows]

    async def fetch_workflow_events(self, workflow_id: str) -> list[asyncpg.Record]:
        """Fetch all events for a specific workflow, ordered by step_number."""
        assert self._pool is not None
        return await self._pool.fetch(
            "SELECT * FROM event_logs WHERE workflow_id = $1 ORDER BY step_number, timestamp",
            UUID(workflow_id),
        )

    async def fetch_all_embeddings(self) -> list[asyncpg.Record]:
        """Fetch all rows from workflow_embeddings (for clustering)."""
        assert self._pool is not None
        return await self._pool.fetch(
            "SELECT workflow_id, task_description, embedding FROM workflow_embeddings"
        )

    # --- Write methods ---

    async def upsert_optimal_path(self, path: dict[str, Any]) -> None:
        """Write an optimal path to the DB (DELETE + INSERT in transaction)."""
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM optimal_paths WHERE task_cluster = $1",
                    path["task_cluster"],
                )
                await conn.execute(
                    """INSERT INTO optimal_paths
                        (path_id, task_cluster, tool_sequence, avg_duration_ms,
                         avg_steps, success_rate, execution_count, embedding, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """,
                    UUID(path["path_id"]),
                    path["task_cluster"],
                    path["tool_sequence"],
                    path["avg_duration_ms"],
                    path["avg_steps"],
                    path["success_rate"],
                    path["execution_count"],
                    str(path["embedding"]) if path.get("embedding") else None,
                )
        log.info("optimal_path_upserted", task_cluster=path["task_cluster"])

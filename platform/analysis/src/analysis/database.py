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

    async def fetch_embedding_for_workflow(self, workflow_id: str) -> list[float] | None:
        """Fetch the embedding vector for a single workflow (for attaching to optimal paths)."""
        assert self._pool is not None
        row = await self._pool.fetchrow(
            "SELECT embedding FROM workflow_embeddings WHERE workflow_id = $1",
            UUID(workflow_id),
        )
        if not row or row["embedding"] is None:
            return None
        embedding = row["embedding"]
        if isinstance(embedding, str):
            return [float(x) for x in embedding.strip("[]").split(",")]
        return list(embedding)

    async def fetch_centroid_embedding(
        self, workflow_ids: list[str],
    ) -> list[float] | None:
        """Compute the centroid (mean) of embeddings for a set of workflows."""
        assert self._pool is not None
        if not workflow_ids:
            return None
        uuids = [UUID(wid) for wid in workflow_ids]
        rows = await self._pool.fetch(
            "SELECT embedding FROM workflow_embeddings WHERE workflow_id = ANY($1::uuid[])",
            uuids,
        )
        if not rows:
            return None

        vectors: list[list[float]] = []
        for row in rows:
            emb = row["embedding"]
            if emb is None:
                continue
            if isinstance(emb, str):
                vectors.append([float(x) for x in emb.strip("[]").split(",")])
            else:
                vectors.append(list(emb))

        if not vectors:
            return None

        dim = len(vectors[0])
        centroid = [
            sum(v[i] for v in vectors) / len(vectors)
            for i in range(dim)
        ]
        return centroid

    async def fetch_mode_success_rates(
        self, workflow_ids: list[str],
    ) -> dict[str, float | None]:
        """Compute guided and exploration success rates for a set of workflows.

        Returns {"guided": rate_or_None, "exploration": rate_or_None}.
        """
        assert self._pool is not None
        if not workflow_ids:
            return {"guided": None, "exploration": None}

        uuids = [UUID(wid) for wid in workflow_ids]
        rows = await self._pool.fetch(
            """
            WITH mode_map AS (
                SELECT DISTINCT workflow_id,
                    CASE WHEN activity = 'optimize:guided' THEN 1 ELSE 0 END AS is_guided
                FROM event_logs
                WHERE workflow_id = ANY($1::uuid[])
                  AND activity IN ('optimize:guided', 'optimize:exploration')
            ),
            outcomes AS (
                SELECT e.workflow_id,
                    COALESCE(mm.is_guided, 0) AS is_guided,
                    CASE WHEN e.activity = 'workflow:complete' THEN 1 ELSE 0 END AS succeeded
                FROM event_logs e
                LEFT JOIN mode_map mm ON mm.workflow_id = e.workflow_id
                WHERE e.workflow_id = ANY($1::uuid[])
                  AND e.activity IN ('workflow:complete', 'workflow:fail')
            )
            SELECT is_guided,
                AVG(succeeded) AS success_rate
            FROM outcomes
            GROUP BY is_guided
            """,
            uuids,
        )

        result: dict[str, float | None] = {"guided": None, "exploration": None}
        for row in rows:
            key = "guided" if row["is_guided"] == 1 else "exploration"
            result[key] = float(row["success_rate"])
        return result

    # --- Write methods ---

    async def clear_optimal_paths(self) -> None:
        """Delete all optimal paths (called at the start of each analysis run)."""
        assert self._pool is not None
        await self._pool.execute("DELETE FROM optimal_paths")
        log.info("optimal_paths_cleared")

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
                         avg_steps, success_rate, execution_count, embedding,
                         guided_success_rate, exploration_success_rate,
                         failure_warnings, alternative_paths, decision_tree,
                         updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
                    """,
                    UUID(path["path_id"]),
                    path["task_cluster"],
                    path["tool_sequence"],
                    path["avg_duration_ms"],
                    path["avg_steps"],
                    path["success_rate"],
                    path["execution_count"],
                    str(path["embedding"]) if path.get("embedding") else None,
                    path.get("guided_success_rate"),
                    path.get("exploration_success_rate"),
                    path.get("failure_warnings", []),
                    path.get("alternative_paths", []),
                    path.get("decision_tree"),
                )
        log.info("optimal_path_upserted", task_cluster=path["task_cluster"])

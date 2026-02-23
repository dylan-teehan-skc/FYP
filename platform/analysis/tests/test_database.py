"""Tests for analysis database layer."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from analysis.database import Database


class TestDatabaseLifecycle:
    def test_init_stores_config(self) -> None:
        db = Database(dsn="postgresql://test:test@localhost/test", min_size=3, max_size=15)
        assert db._dsn == "postgresql://test:test@localhost/test"
        assert db._min_size == 3
        assert db._max_size == 15
        assert db._pool is None

    def test_default_pool_sizes(self) -> None:
        db = Database(dsn="postgresql://test:test@localhost/test")
        assert db._min_size == 2
        assert db._max_size == 10

    @patch("analysis.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_connect_creates_pool(self, mock_create_pool: AsyncMock) -> None:
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool
        db = Database(dsn="postgresql://test:test@localhost/test")
        await db.connect()
        mock_create_pool.assert_called_once()
        assert db._pool is mock_pool

    @patch("analysis.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_disconnect_closes_pool(self, mock_create_pool: AsyncMock) -> None:
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        db = Database(dsn="postgresql://test:test@localhost/test")
        await db.connect()
        await db.disconnect()
        mock_pool.close.assert_called_once()
        assert db._pool is None

    async def test_disconnect_noop_without_pool(self) -> None:
        db = Database(dsn="postgresql://test:test@localhost/test")
        await db.disconnect()
        assert db._pool is None


class TestReadQueries:
    def _make_db(self) -> Database:
        db = Database(dsn="postgresql://test:test@localhost/test")
        db._pool = AsyncMock()
        return db

    async def test_fetch_all_workflow_ids(self) -> None:
        db = self._make_db()
        mock_uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
        db._pool.fetch = AsyncMock(return_value=[{"workflow_id": mock_uuid}])
        result = await db.fetch_all_workflow_ids()
        assert result == [str(mock_uuid)]

    async def test_fetch_workflow_events(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.fetch_workflow_events("550e8400-e29b-41d4-a716-446655440000")
        assert result == []
        db._pool.fetch.assert_called_once()

    async def test_fetch_all_embeddings(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.fetch_all_embeddings()
        assert result == []


class TestWriteQueries:
    def _make_db(self) -> Database:
        db = Database(dsn="postgresql://test:test@localhost/test")
        db._pool = AsyncMock()
        return db

    async def test_upsert_optimal_path(self) -> None:
        db = self._make_db()
        mock_conn = AsyncMock()

        @asynccontextmanager
        async def fake_acquire():
            yield mock_conn

        mock_conn.transaction = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(), __aexit__=AsyncMock()
        ))
        db._pool.acquire = fake_acquire

        path_data = {
            "path_id": "550e8400-e29b-41d4-a716-446655440000",
            "task_cluster": "test_cluster",
            "tool_sequence": ["a", "b"],
            "avg_duration_ms": 500.0,
            "avg_steps": 2.0,
            "success_rate": 0.95,
            "execution_count": 10,
            "embedding": [0.1] * 1536,
        }
        await db.upsert_optimal_path(path_data)
        assert mock_conn.execute.call_count == 2  # DELETE + INSERT

    async def test_upsert_optimal_path_no_embedding(self) -> None:
        db = self._make_db()
        mock_conn = AsyncMock()

        @asynccontextmanager
        async def fake_acquire():
            yield mock_conn

        mock_conn.transaction = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(), __aexit__=AsyncMock()
        ))
        db._pool.acquire = fake_acquire

        path_data = {
            "path_id": "550e8400-e29b-41d4-a716-446655440000",
            "task_cluster": "test_cluster",
            "tool_sequence": ["a"],
            "avg_duration_ms": 100.0,
            "avg_steps": 1.0,
            "success_rate": 1.0,
            "execution_count": 5,
            "embedding": None,
        }
        await db.upsert_optimal_path(path_data)
        assert mock_conn.execute.call_count == 2

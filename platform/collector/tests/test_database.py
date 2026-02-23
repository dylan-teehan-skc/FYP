"""Tests for database layer."""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from collector.database import Database, _event_to_args

SAMPLE_EVENT = {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "workflow_id": "660e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-02-23T10:00:00Z",
    "activity": "tool_call:check_ticket",
    "agent_name": "agent",
    "agent_role": "triage",
    "tool_name": "check_ticket",
    "tool_parameters": {"ticket_id": "T-1001"},
    "tool_response": {"status": "open"},
    "llm_model": "gpt-4",
    "llm_prompt_tokens": 100,
    "llm_completion_tokens": 50,
    "llm_reasoning": "reasoning",
    "duration_ms": 230.0,
    "cost_usd": 0.002,
    "status": "success",
    "error_message": None,
    "step_number": 1,
    "parent_event_id": None,
}


class TestEventToArgs:
    def test_converts_all_fields(self) -> None:
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-02-23T10:00:00Z",
            "activity": "tool_call:check_ticket",
            "agent_name": "agent",
            "agent_role": "triage",
            "tool_name": "check_ticket",
            "tool_parameters": {"ticket_id": "T-1001"},
            "tool_response": {"status": "open"},
            "llm_model": "gpt-4",
            "llm_prompt_tokens": 100,
            "llm_completion_tokens": 50,
            "llm_reasoning": "reasoning",
            "duration_ms": 230.0,
            "cost_usd": 0.002,
            "status": "success",
            "error_message": None,
            "step_number": 1,
            "parent_event_id": None,
        }
        args = _event_to_args(event)
        assert len(args) == 19
        assert isinstance(args[0], UUID)  # event_id
        assert isinstance(args[1], UUID)  # workflow_id
        assert args[3] == "tool_call:check_ticket"  # activity
        assert args[7] == {"ticket_id": "T-1001"}  # tool_parameters
        assert isinstance(args[14], Decimal)  # cost_usd
        assert args[18] is None  # parent_event_id

    def test_converts_parent_event_id(self) -> None:
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440001",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440001",
            "timestamp": "2025-02-23T10:00:00Z",
            "activity": "test",
            "agent_name": "",
            "agent_role": "",
            "parent_event_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        args = _event_to_args(event)
        assert isinstance(args[18], UUID)

    def test_defaults_for_missing_optional_fields(self) -> None:
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440002",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440002",
            "timestamp": "2025-02-23T10:00:00Z",
            "activity": "workflow:start",
            "agent_name": "",
            "agent_role": "",
        }
        args = _event_to_args(event)
        assert args[6] is None  # tool_name
        assert args[7] == {}  # tool_parameters
        assert args[9] == ""  # llm_model
        assert args[10] == 0  # llm_prompt_tokens
        assert args[13] == 0.0  # duration_ms
        assert args[14] == Decimal("0.0")  # cost_usd


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

    @patch("collector.database.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_connect_creates_pool(self, mock_create_pool: AsyncMock) -> None:
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool
        db = Database(dsn="postgresql://test:test@localhost/test")
        await db.connect()
        mock_create_pool.assert_called_once()
        assert db._pool is mock_pool

    @patch("collector.database.asyncpg.create_pool", new_callable=AsyncMock)
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
        await db.disconnect()  # should not raise
        assert db._pool is None


class TestDatabaseQueries:
    def _make_db(self) -> Database:
        db = Database(dsn="postgresql://test:test@localhost/test")
        db._pool = AsyncMock()
        return db

    async def test_execute(self) -> None:
        db = self._make_db()
        db._pool.execute = AsyncMock(return_value="INSERT 0 1")
        result = await db.execute("SELECT 1", 42)
        db._pool.execute.assert_called_once_with("SELECT 1", 42)
        assert result == "INSERT 0 1"

    async def test_fetch(self) -> None:
        db = self._make_db()
        rows = [{"id": 1}, {"id": 2}]
        db._pool.fetch = AsyncMock(return_value=rows)
        result = await db.fetch("SELECT * FROM t")
        assert result == rows

    async def test_fetchrow(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={"id": 1})
        result = await db.fetchrow("SELECT * FROM t LIMIT 1")
        assert result == {"id": 1}

    async def test_fetchval(self) -> None:
        db = self._make_db()
        db._pool.fetchval = AsyncMock(return_value=42)
        result = await db.fetchval("SELECT COUNT(*)")
        assert result == 42

    async def test_insert_event(self) -> None:
        db = self._make_db()
        db._pool.execute = AsyncMock(return_value="INSERT 0 1")
        await db.insert_event(SAMPLE_EVENT)
        db._pool.execute.assert_called_once()

    async def test_insert_events_batch(self) -> None:
        db = self._make_db()
        mock_conn = AsyncMock()

        @asynccontextmanager
        async def fake_acquire():
            yield mock_conn

        db._pool.acquire = fake_acquire
        await db.insert_events_batch([SAMPLE_EVENT, SAMPLE_EVENT])
        mock_conn.executemany.assert_called_once()

    async def test_insert_events_batch_empty(self) -> None:
        db = self._make_db()
        await db.insert_events_batch([])  # should return early

    async def test_get_workflow_trace(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.get_workflow_trace("660e8400-e29b-41d4-a716-446655440000")
        assert result == []

    async def test_upsert_embedding(self) -> None:
        db = self._make_db()
        db._pool.execute = AsyncMock(return_value="INSERT 0 1")
        await db.upsert_embedding(
            "660e8400-e29b-41d4-a716-446655440000",
            "Handle refund",
            [0.1] * 1536,
            "test-model",
        )
        db._pool.execute.assert_called_once()

    async def test_find_similar_paths(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.find_similar_paths([0.1] * 1536)
        assert result is None
        db._pool.fetchrow.assert_called_once()

    async def test_get_analytics_summary(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "total_workflows": 5,
            "total_events": 50,
            "avg_duration_ms": 1500.0,
            "avg_steps": 4.2,
            "success_rate": 0.9,
        })
        db._pool.fetch = AsyncMock(return_value=[
            {"tool_name": "check_ticket", "call_count": 10, "avg_duration_ms": 200.0},
        ])
        result = await db.get_analytics_summary()
        assert result["total_workflows"] == 5
        assert result["total_events"] == 50
        assert len(result["top_tools"]) == 1

    async def test_get_analytics_summary_empty(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.get_analytics_summary()
        assert result["total_workflows"] == 0
        assert result["top_tools"] == []

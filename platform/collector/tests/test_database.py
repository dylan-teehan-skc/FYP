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
            [0.1] * 768,
            "test-model",
        )
        db._pool.execute.assert_called_once()

    async def test_find_similar_paths(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.find_similar_paths([0.1] * 768)
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

    async def test_get_analytics_summary_null_aggregates(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "total_workflows": 2,
            "total_events": 10,
            "avg_duration_ms": None,
            "avg_steps": None,
            "success_rate": None,
        })
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.get_analytics_summary()
        assert result["total_workflows"] == 2
        assert result["avg_duration_ms"] is None
        assert result["avg_steps"] is None
        assert result["success_rate"] is None


class TestDashboardQueries:
    def _make_db(self) -> Database:
        db = Database(dsn="postgresql://test:test@localhost/test")
        db._pool = AsyncMock()
        return db

    async def test_list_workflows(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[
            {"workflow_id": "abc", "task_description": "test", "status": "success",
             "duration_ms": 1000.0, "steps": 4, "is_guided": True,
             "timestamp": "2025-02-23T10:00:00Z"},
        ])
        db._pool.fetchrow = AsyncMock(return_value={"cnt": 1})
        result = await db.list_workflows(limit=50, offset=0)
        assert result["total"] == 1
        assert len(result["workflows"]) == 1
        db._pool.fetch.assert_called_once()
        db._pool.fetchrow.assert_called_once()

    async def test_list_workflows_empty(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        db._pool.fetchrow = AsyncMock(return_value={"cnt": 0})
        result = await db.list_workflows(limit=50, offset=0)
        assert result["total"] == 0
        assert result["workflows"] == []

    async def test_list_workflows_null_total(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.list_workflows(limit=50, offset=0)
        assert result["total"] == 0

    async def test_list_optimal_paths(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[
            {"task_cluster": "refund", "tool_sequence": ["a", "b"],
             "avg_duration_ms": 1500.0, "avg_steps": 3.0, "success_rate": 0.95,
             "execution_count": 42, "updated_at": "2025-02-23"},
        ])
        result = await db.list_optimal_paths()
        assert len(result) == 1

    async def test_list_optimal_paths_empty(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.list_optimal_paths()
        assert result == []

    async def test_get_mode_distribution(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "guided": 20, "exploration": 30,
        })
        result = await db.get_mode_distribution()
        assert result["guided"] == 20
        assert result["exploration"] == 30
        assert result["total"] == 50

    async def test_get_mode_distribution_empty(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.get_mode_distribution()
        assert result == {"guided": 0, "exploration": 0, "total": 0}

    async def test_get_mode_distribution_null_counts(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "guided": None, "exploration": None,
        })
        result = await db.get_mode_distribution()
        assert result["guided"] == 0
        assert result["exploration"] == 0
        assert result["total"] == 0

    async def test_get_mode_comparison(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "exp_avg_duration": 3000.0, "exp_avg_steps": 6.0,
            "exp_success_rate": 0.8, "exp_count": 30, "exp_avg_cost": 0.05,
            "gui_avg_duration": 1800.0, "gui_avg_steps": 4.0,
            "gui_success_rate": 0.96, "gui_count": 20, "gui_avg_cost": 0.07,
        })
        result = await db.get_mode_comparison()
        assert result["exploration"]["avg_duration_ms"] == 3000.0
        assert result["guided"]["success_rate"] == 0.96
        assert result["guided"]["count"] == 20
        assert result["exploration"]["avg_cost_usd"] == 0.05

    async def test_get_mode_comparison_empty(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.get_mode_comparison()
        assert result["exploration"]["avg_duration_ms"] is None
        assert result["guided"]["count"] == 0

    async def test_get_mode_comparison_null_values(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "exp_avg_duration": None, "exp_avg_steps": None,
            "exp_success_rate": None, "exp_count": None, "exp_avg_cost": None,
            "gui_avg_duration": None, "gui_avg_steps": None,
            "gui_success_rate": None, "gui_count": None, "gui_avg_cost": None,
        })
        result = await db.get_mode_comparison()
        assert result["exploration"]["avg_duration_ms"] is None
        assert result["guided"]["count"] == 0

    async def test_get_timeline(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[
            {"date": "2025-02-20", "workflows": 5, "avg_duration_ms": 2000.0,
             "success_rate": 0.8, "guided_pct": 0.4},
        ])
        result = await db.get_timeline()
        assert len(result) == 1

    async def test_get_timeline_empty(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.get_timeline()
        assert result == []

    async def test_get_execution_graph(self) -> None:
        db = self._make_db()
        tool_rows = [
            {"tool_name": "check_ticket", "call_count": 10, "avg_duration_ms": 200.0},
            {"tool_name": "get_order", "call_count": 8, "avg_duration_ms": 180.0},
        ]
        seq_rows = [
            {"workflow_id": "wf-1", "tool_name": "check_ticket", "step_number": 1},
            {"workflow_id": "wf-1", "tool_name": "get_order", "step_number": 2},
            {"workflow_id": "wf-2", "tool_name": "check_ticket", "step_number": 1},
            {"workflow_id": "wf-2", "tool_name": "get_order", "step_number": 2},
        ]
        db._pool.fetch = AsyncMock(side_effect=[tool_rows, seq_rows])
        result = await db.get_execution_graph()
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["edges"][0]["source"] == "check_ticket"
        assert result["edges"][0]["target"] == "get_order"
        assert result["edges"][0]["weight"] == 2

    async def test_get_execution_graph_empty(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(side_effect=[[], []])
        result = await db.get_execution_graph()
        assert result == {"nodes": [], "edges": []}

    async def test_get_execution_graph_null_duration(self) -> None:
        db = self._make_db()
        tool_rows = [
            {"tool_name": "check_ticket", "call_count": 1, "avg_duration_ms": None},
        ]
        db._pool.fetch = AsyncMock(side_effect=[tool_rows, []])
        result = await db.get_execution_graph()
        assert result["nodes"][0]["avg_duration_ms"] is None

    async def test_get_execution_graph_multiple_workflows(self) -> None:
        db = self._make_db()
        tool_rows = [
            {"tool_name": "a", "call_count": 4, "avg_duration_ms": 100.0},
            {"tool_name": "b", "call_count": 4, "avg_duration_ms": 200.0},
        ]
        seq_rows = [
            {"workflow_id": "wf-1", "tool_name": "a", "step_number": 1},
            {"workflow_id": "wf-1", "tool_name": "b", "step_number": 2},
            {"workflow_id": "wf-2", "tool_name": "b", "step_number": 1},
            {"workflow_id": "wf-2", "tool_name": "a", "step_number": 2},
        ]
        db._pool.fetch = AsyncMock(side_effect=[tool_rows, seq_rows])
        result = await db.get_execution_graph()
        edges_by_dir = {(e["source"], e["target"]): e["weight"] for e in result["edges"]}
        assert edges_by_dir[("a", "b")] == 1
        assert edges_by_dir[("b", "a")] == 1

    async def test_get_cluster_execution_graph(self) -> None:
        db = self._make_db()
        tool_rows = [
            {"tool_name": "check_ticket", "call_count": 5, "avg_duration_ms": 200.0},
        ]
        db._pool.fetch = AsyncMock(side_effect=[tool_rows, []])
        result = await db.get_cluster_execution_graph(
            "550e8400-e29b-41d4-a716-446655440000", 0.85,
        )
        assert len(result["nodes"]) == 1
        assert result["edges"] == []

    async def test_get_bottlenecks(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[
            {"tool_name": "check_ticket", "call_count": 50, "avg_duration_ms": 350.0,
             "total_cost_usd": 0.05, "avg_calls_per_workflow": 1.25},
        ])
        result = await db.get_bottlenecks()
        assert len(result) == 1

    async def test_get_bottlenecks_empty(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[])
        result = await db.get_bottlenecks()
        assert result == []

    async def test_get_cluster_bottlenecks(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[
            {"tool_name": "a", "call_count": 10, "avg_duration_ms": 500.0,
             "total_cost_usd": 0.01, "avg_calls_per_workflow": 2.0},
        ])
        result = await db.get_cluster_bottlenecks(
            "550e8400-e29b-41d4-a716-446655440000", 0.85,
        )
        assert len(result) == 1

    async def test_list_task_clusters(self) -> None:
        db = self._make_db()
        db._pool.fetch = AsyncMock(return_value=[
            {"path_id": "p1", "task_cluster": "refund", "tool_sequence": ["a"],
             "avg_duration_ms": 1000.0, "avg_steps": 3.0, "success_rate": 0.9,
             "execution_count": 30, "updated_at": "2025-02-23", "workflow_count": 25},
        ])
        result = await db.list_task_clusters(0.85)
        assert len(result) == 1

    async def test_get_cluster_workflows_no_path(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.get_cluster_workflows(
            "550e8400-e29b-41d4-a716-446655440000", 0.85,
        )
        assert result["path"] is None
        assert result["workflows"] == []

    async def test_get_cluster_workflows_no_embedding(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "path_id": "p1", "task_cluster": "refund",
            "tool_sequence": ["a", "b"], "avg_duration_ms": 1000.0,
            "avg_steps": 3.0, "success_rate": 0.9,
            "execution_count": 30, "embedding": None, "updated_at": "2025-02-23",
        })
        result = await db.get_cluster_workflows(
            "550e8400-e29b-41d4-a716-446655440000", 0.85,
        )
        assert result["path"] is not None
        assert result["workflows"] == []
        assert result["mode_stats"] is None

    async def test_get_cluster_workflows_with_data(self) -> None:
        db = self._make_db()
        path_row = {
            "path_id": "p1", "task_cluster": "refund",
            "tool_sequence": ["check_ticket", "get_order"],
            "avg_duration_ms": 1000.0, "avg_steps": 3.0,
            "success_rate": 0.9, "execution_count": 30,
            "embedding": str([0.1] * 768), "updated_at": "2025-02-23",
        }
        workflow_rows = [
            {"workflow_id": "wf-1", "task_description": "test",
             "similarity": 0.95, "status": "success",
             "duration_ms": 1000.0, "steps": 3,
             "timestamp": "2025-02-23", "is_guided": 0, "total_cost_usd": 0.01},
        ]
        mode_stats_row = {
            "exp_avg_duration": 3000.0, "exp_avg_steps": 6.0,
            "exp_success_rate": 0.8, "exp_count": 10, "exp_avg_cost": 0.05,
            "gui_avg_duration": 1800.0, "gui_avg_steps": 4.0,
            "gui_success_rate": 0.96, "gui_count": 5, "gui_avg_cost": 0.07,
        }
        tool_seq_rows = [
            {"workflow_id": "wf-1", "tools": ["check_ticket", "get_order"]},
        ]
        db._pool.fetchrow = AsyncMock(side_effect=[path_row, mode_stats_row])
        db._pool.fetch = AsyncMock(side_effect=[workflow_rows, tool_seq_rows])
        result = await db.get_cluster_workflows(
            "550e8400-e29b-41d4-a716-446655440000", 0.85,
        )
        assert result["path"] is not None
        assert len(result["workflows"]) == 1
        assert result["mode_stats"] is not None
        assert result["avg_conformance"] == 1.0

    async def test_get_cluster_workflows_partial_conformance(self) -> None:
        db = self._make_db()
        path_row = {
            "path_id": "p1", "task_cluster": "refund",
            "tool_sequence": ["a", "b", "c"],
            "avg_duration_ms": 1000.0, "avg_steps": 3.0,
            "success_rate": 0.9, "execution_count": 30,
            "embedding": str([0.1] * 768), "updated_at": "2025-02-23",
        }
        tool_seq_rows = [
            {"workflow_id": "wf-1", "tools": ["a", "b", "d"]},
            {"workflow_id": "wf-2", "tools": ["a", "x", "c"]},
        ]
        db._pool.fetchrow = AsyncMock(side_effect=[path_row, None])
        db._pool.fetch = AsyncMock(side_effect=[[], tool_seq_rows])
        result = await db.get_cluster_workflows(
            "550e8400-e29b-41d4-a716-446655440000", 0.85,
        )
        assert result["avg_conformance"] is not None
        assert 0.0 < result["avg_conformance"] < 1.0

    async def test_get_savings(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "exp_avg_duration": 3000.0, "exp_avg_steps": 6.0,
            "exp_success_rate": 0.8, "exp_avg_cost": 0.05,
            "gui_avg_duration": 1800.0, "gui_avg_steps": 4.0,
            "gui_success_rate": 0.95, "gui_avg_cost": 0.07,
            "guided_count": 20,
        })
        result = await db.get_savings()
        assert result["time_saved_ms"] == (3000.0 - 1800.0) * 20
        assert result["pct_duration_improvement"] == 40.0
        assert result["pct_steps_improvement"] > 0

    async def test_get_savings_empty(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value=None)
        result = await db.get_savings()
        assert result["time_saved_ms"] == 0.0
        assert result["cost_saved_usd"] == 0.0
        assert result["pct_duration_improvement"] == 0.0

    async def test_get_savings_null_values(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "exp_avg_duration": None, "exp_avg_steps": None,
            "exp_success_rate": None, "exp_avg_cost": None,
            "gui_avg_duration": None, "gui_avg_steps": None,
            "gui_success_rate": None, "gui_avg_cost": None,
            "guided_count": None,
        })
        result = await db.get_savings()
        assert result["time_saved_ms"] == 0.0
        assert result["pct_duration_improvement"] == 0.0

    async def test_get_savings_zero_baseline(self) -> None:
        db = self._make_db()
        db._pool.fetchrow = AsyncMock(return_value={
            "exp_avg_duration": 0.0, "exp_avg_steps": 0.0,
            "exp_success_rate": 0.0, "exp_avg_cost": 0.0,
            "gui_avg_duration": 1000.0, "gui_avg_steps": 3.0,
            "gui_success_rate": 1.0, "gui_avg_cost": 0.05,
            "guided_count": 5,
        })
        result = await db.get_savings()
        assert result["pct_duration_improvement"] == 0.0

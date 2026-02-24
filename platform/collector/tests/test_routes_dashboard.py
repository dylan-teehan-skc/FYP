"""Tests for dashboard endpoints."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

from httpx import AsyncClient

from .conftest import MockDatabase


class TestListWorkflows:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/workflows")
        assert response.status_code == 200
        data = response.json()
        assert data["workflows"] == []
        assert data["total"] == 0

    async def test_pagination_params_forwarded(
        self, client: AsyncClient, mock_db: MockDatabase
    ) -> None:
        mock_db.list_workflows = AsyncMock(return_value={"workflows": [], "total": 5})
        response = await client.get("/workflows?limit=10&offset=2")
        assert response.status_code == 200
        mock_db.list_workflows.assert_awaited_once_with(limit=10, offset=2)

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        ts = datetime.datetime(2025, 2, 23, 10, 0, 0, tzinfo=datetime.UTC)
        mock_db.list_workflows = AsyncMock(return_value={
            "workflows": [
                {
                    "workflow_id": "abc-123",
                    "task_description": "Refund order #42",
                    "status": "success",
                    "duration_ms": 1800.0,
                    "steps": 4,
                    "is_guided": True,
                    "timestamp": ts,
                }
            ],
            "total": 1,
        })
        response = await client.get("/workflows")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        wf = data["workflows"][0]
        assert wf["workflow_id"] == "abc-123"
        assert wf["mode"] == "guided"
        assert wf["duration_ms"] == 1800.0
        assert wf["steps"] == 4

    async def test_exploration_mode(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        ts = datetime.datetime(2025, 2, 23, tzinfo=datetime.UTC)
        mock_db.list_workflows = AsyncMock(return_value={
            "workflows": [
                {
                    "workflow_id": "def-456",
                    "task_description": None,
                    "status": "failure",
                    "duration_ms": None,
                    "steps": None,
                    "is_guided": False,
                    "timestamp": ts,
                }
            ],
            "total": 1,
        })
        response = await client.get("/workflows")
        assert response.status_code == 200
        wf = response.json()["workflows"][0]
        assert wf["mode"] == "exploration"
        assert wf["duration_ms"] is None


class TestListOptimalPaths:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/optimal-paths")
        assert response.status_code == 200
        assert response.json()["paths"] == []

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        ts = datetime.datetime(2025, 2, 23, tzinfo=datetime.UTC)
        mock_db.list_optimal_paths = AsyncMock(return_value=[
            {
                "task_cluster": "refund",
                "tool_sequence": ["check_ticket", "get_order", "process_refund"],
                "avg_duration_ms": 1500.0,
                "avg_steps": 3.0,
                "success_rate": 0.95,
                "execution_count": 42,
                "updated_at": ts,
            }
        ])
        response = await client.get("/optimal-paths")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert len(paths) == 1
        assert paths[0]["task_cluster"] == "refund"
        assert paths[0]["tool_sequence"] == ["check_ticket", "get_order", "process_refund"]
        assert paths[0]["execution_count"] == 42


class TestModeDistribution:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/mode-distribution")
        assert response.status_code == 200
        data = response.json()
        assert data == {"exploration": 0, "guided": 0, "total": 0}

    async def test_with_counts(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_mode_distribution = AsyncMock(
            return_value={"exploration": 30, "guided": 20, "total": 50}
        )
        response = await client.get("/analytics/mode-distribution")
        assert response.status_code == 200
        data = response.json()
        assert data["exploration"] == 30
        assert data["guided"] == 20
        assert data["total"] == 50


class TestComparison:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/comparison")
        assert response.status_code == 200
        data = response.json()
        assert "exploration" in data
        assert "guided" in data
        assert data["exploration"]["count"] == 0

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_mode_comparison = AsyncMock(return_value={
            "exploration": {
                "avg_duration_ms": 3000.0,
                "avg_steps": 6.0,
                "success_rate": 0.80,
                "count": 30,
            },
            "guided": {
                "avg_duration_ms": 1800.0,
                "avg_steps": 4.0,
                "success_rate": 0.96,
                "count": 20,
            },
        })
        response = await client.get("/analytics/comparison")
        assert response.status_code == 200
        data = response.json()
        assert data["exploration"]["avg_duration_ms"] == 3000.0
        assert data["guided"]["success_rate"] == 0.96
        assert data["guided"]["count"] == 20


class TestTimeline:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/timeline")
        assert response.status_code == 200
        assert response.json()["points"] == []

    async def test_with_points(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_timeline = AsyncMock(return_value=[
            {
                "date": datetime.date(2025, 2, 20),
                "workflows": 5,
                "avg_duration_ms": 2000.0,
                "success_rate": 0.8,
                "guided_pct": 0.4,
            },
            {
                "date": datetime.date(2025, 2, 21),
                "workflows": 10,
                "avg_duration_ms": 1500.0,
                "success_rate": 0.9,
                "guided_pct": 0.6,
            },
        ])
        response = await client.get("/analytics/timeline")
        assert response.status_code == 200
        points = response.json()["points"]
        assert len(points) == 2
        assert points[0]["date"] == "2025-02-20"
        assert points[0]["workflows"] == 5
        assert points[1]["guided_pct"] == 0.6


class TestExecutionGraph:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/execution-graph")
        assert response.status_code == 200
        data = response.json()
        assert data == {"nodes": [], "edges": []}

    async def test_with_graph(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_execution_graph = AsyncMock(return_value={
            "nodes": [
                {
                    "id": "check_ticket",
                    "label": "check_ticket",
                    "avg_duration_ms": 200.0,
                    "call_count": 10,
                },
                {
                    "id": "get_order",
                    "label": "get_order",
                    "avg_duration_ms": 180.0,
                    "call_count": 8,
                },
            ],
            "edges": [
                {"source": "check_ticket", "target": "get_order", "weight": 7},
            ],
        })
        response = await client.get("/analytics/execution-graph")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["weight"] == 7


class TestBottlenecks:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/bottlenecks")
        assert response.status_code == 200
        assert response.json()["tools"] == []

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_bottlenecks = AsyncMock(return_value=[
            {
                "tool_name": "check_ticket",
                "call_count": 50,
                "avg_duration_ms": 350.0,
                "total_cost_usd": 0.05,
                "avg_calls_per_workflow": 1.25,
            }
        ])
        response = await client.get("/analytics/bottlenecks")
        assert response.status_code == 200
        tools = response.json()["tools"]
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "check_ticket"
        assert tools[0]["avg_duration_ms"] == 350.0
        assert tools[0]["avg_calls_per_workflow"] == 1.25


class TestSavings:
    async def test_zeros(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/savings")
        assert response.status_code == 200
        data = response.json()
        assert data["time_saved_ms"] == 0.0
        assert data["cost_saved_usd"] == 0.0
        assert data["pct_duration_improvement"] == 0.0

    async def test_with_savings(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_savings = AsyncMock(return_value={
            "time_saved_ms": 24000.0,
            "cost_saved_usd": 0.48,
            "pct_duration_improvement": 40.0,
            "pct_steps_improvement": 33.3,
            "pct_success_improvement": 75.0,
        })
        response = await client.get("/analytics/savings")
        assert response.status_code == 200
        data = response.json()
        assert data["time_saved_ms"] == 24000.0
        assert data["pct_duration_improvement"] == 40.0
        assert data["pct_success_improvement"] == 75.0

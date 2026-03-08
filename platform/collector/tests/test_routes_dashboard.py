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
            "guided_count": 12,
        })
        response = await client.get("/analytics/savings")
        assert response.status_code == 200
        data = response.json()
        assert data["time_saved_ms"] == 24000.0
        assert data["pct_duration_improvement"] == 40.0
        assert data["pct_success_improvement"] == 75.0


def _cluster_row(
    path_id: str = "pid-1",
    task_cluster: str = "Refund Processing",
    **overrides,
) -> dict:
    """Helper to build a cluster summary row."""
    ts = datetime.datetime(2025, 2, 23, tzinfo=datetime.UTC)
    base = {
        "path_id": path_id,
        "task_cluster": task_cluster,
        "tool_sequence": ["check_ticket", "process_refund"],
        "avg_duration_ms": 1500.0,
        "avg_steps": 3.0,
        "success_rate": 0.95,
        "execution_count": 10,
        "workflow_count": 8,
        "updated_at": ts,
        "task_description": "Process customer refund",
    }
    base.update(overrides)
    return base


def _mode_stats_dict() -> dict:
    return {
        "exp_avg_duration": 3000.0,
        "exp_avg_steps": 6.0,
        "exp_success_rate": 0.80,
        "exp_count": 5,
        "exp_avg_cost": 0.01,
        "gui_avg_duration": 1500.0,
        "gui_avg_steps": 3.0,
        "gui_success_rate": 0.96,
        "gui_count": 3,
        "gui_avg_cost": 0.005,
    }


def _workflow_row(workflow_id: str = "wf-1", **overrides) -> dict:
    ts = datetime.datetime(2025, 2, 23, 10, 0, 0, tzinfo=datetime.UTC)
    base = {
        "workflow_id": workflow_id,
        "task_description": "refund order",
        "similarity": 0.92,
        "status": "success",
        "duration_ms": 1800.0,
        "steps": 4,
        "is_guided": True,
        "timestamp": ts,
        "total_cost_usd": 0.003,
    }
    base.update(overrides)
    return base


class TestListTaskClusters:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters")
        assert response.status_code == 200
        assert response.json()["clusters"] == []

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.list_task_clusters = AsyncMock(return_value=[_cluster_row()])
        response = await client.get("/task-clusters")
        assert response.status_code == 200
        clusters = response.json()["clusters"]
        assert len(clusters) == 1
        assert clusters[0]["task_cluster"] == "Refund Processing"
        assert clusters[0]["execution_count"] == 10


class TestListTaskClustersGrouped:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/grouped")
        assert response.status_code == 200
        assert response.json()["groups"] == []

    async def test_single_group_no_subclusters(
        self, client: AsyncClient, mock_db: MockDatabase
    ) -> None:
        mock_db.list_task_clusters = AsyncMock(return_value=[
            _cluster_row(path_id="pid-1", task_cluster="Refund Processing"),
        ])
        response = await client.get("/task-clusters/grouped")
        assert response.status_code == 200
        groups = response.json()["groups"]
        assert len(groups) == 1
        assert groups[0]["name"] == "Refund Processing"
        assert groups[0]["total_workflows"] == 8

    async def test_group_with_subclusters(
        self, client: AsyncClient, mock_db: MockDatabase
    ) -> None:
        mock_db.list_task_clusters = AsyncMock(return_value=[
            _cluster_row(
                path_id="pid-1",
                task_cluster="Refund Processing",
                workflow_count=10,
            ),
            _cluster_row(
                path_id="pid-2",
                task_cluster="Refund Processing (subcluster_0)",
                workflow_count=6,
            ),
            _cluster_row(
                path_id="pid-3",
                task_cluster="Refund Processing (subcluster_1)",
                workflow_count=4,
            ),
        ])
        response = await client.get("/task-clusters/grouped")
        assert response.status_code == 200
        groups = response.json()["groups"]
        assert len(groups) == 1
        assert groups[0]["name"] == "Refund Processing"
        assert groups[0]["total_workflows"] == 10
        assert len(groups[0]["subclusters"]) == 3


class TestClusterGroupDetail:
    async def test_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/group/NonExistent/detail")
        assert response.status_code == 404

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_group_path_ids = AsyncMock(return_value=["pid-1", "pid-2"])
        mock_db.list_task_clusters = AsyncMock(return_value=[
            _cluster_row(path_id="pid-1", task_cluster="Refund Processing"),
            _cluster_row(
                path_id="pid-2",
                task_cluster="Refund Processing (subcluster_0)",
                workflow_count=5,
            ),
        ])
        mock_db.get_group_workflows = AsyncMock(return_value={
            "workflows": [_workflow_row()],
            "mode_stats": _mode_stats_dict(),
            "avg_conformance": 0.85,
        })
        mock_db.get_group_distinct_paths = AsyncMock(return_value=[
            {"tool_sequence": ["check_ticket", "process_refund"], "workflow_count": 10},
            {"tool_sequence": ["check_ticket", "escalate"], "workflow_count": 3},
        ])
        response = await client.get("/task-clusters/group/Refund%20Processing/detail")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Refund Processing"
        assert len(data["workflows"]) == 1
        assert data["avg_conformance"] == 0.85
        assert data["mode_stats"]["guided"]["count"] == 3
        assert data["optimal_sequence"] == ["check_ticket", "process_refund"]
        assert len(data["distinct_paths"]) == 2
        assert data["distinct_paths"][0]["workflow_count"] == 10


class TestClusterGroupExecutionGraph:
    async def test_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/group/NonExistent/execution-graph")
        assert response.status_code == 404

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_group_path_ids = AsyncMock(return_value=["pid-1"])
        mock_db.get_group_execution_graph = AsyncMock(return_value={
            "nodes": [
                {"id": "check_ticket", "label": "check_ticket",
                 "avg_duration_ms": 200.0, "call_count": 5},
            ],
            "edges": [
                {"source": "check_ticket", "target": "process_refund", "weight": 4},
            ],
        })
        response = await client.get("/task-clusters/group/Refund/execution-graph")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 1


class TestClusterGroupBottlenecks:
    async def test_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/group/NonExistent/bottlenecks")
        assert response.status_code == 404

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_group_path_ids = AsyncMock(return_value=["pid-1"])
        mock_db.get_group_bottlenecks = AsyncMock(return_value=[
            {
                "tool_name": "check_ticket",
                "call_count": 20,
                "avg_duration_ms": 250.0,
                "total_cost_usd": 0.02,
                "avg_calls_per_workflow": 1.1,
            }
        ])
        response = await client.get("/task-clusters/group/Refund/bottlenecks")
        assert response.status_code == 200
        tools = response.json()["tools"]
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "check_ticket"


class TestClusterExecutionGraph:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/pid-1/execution-graph")
        assert response.status_code == 200
        data = response.json()
        assert data == {"nodes": [], "edges": []}

    async def test_with_graph(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_cluster_execution_graph = AsyncMock(return_value={
            "nodes": [
                {"id": "get_order", "label": "get_order",
                 "avg_duration_ms": 140.0, "call_count": 6},
            ],
            "edges": [],
        })
        response = await client.get("/task-clusters/pid-1/execution-graph")
        assert response.status_code == 200
        assert len(response.json()["nodes"]) == 1


class TestClusterBottlenecks:
    async def test_empty(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/pid-1/bottlenecks")
        assert response.status_code == 200
        assert response.json()["tools"] == []

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_cluster_bottlenecks = AsyncMock(return_value=[
            {
                "tool_name": "process_refund",
                "call_count": 15,
                "avg_duration_ms": 320.0,
                "total_cost_usd": 0.03,
                "avg_calls_per_workflow": 1.0,
            }
        ])
        response = await client.get("/task-clusters/pid-1/bottlenecks")
        assert response.status_code == 200
        tools = response.json()["tools"]
        assert len(tools) == 1
        assert tools[0]["avg_duration_ms"] == 320.0


class TestClusterDetail:
    async def test_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/task-clusters/pid-999/workflows")
        assert response.status_code == 404

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        path_row = _cluster_row()
        mock_db.get_cluster_workflows = AsyncMock(return_value={
            "path": path_row,
            "workflows": [_workflow_row()],
            "mode_stats": _mode_stats_dict(),
            "avg_conformance": 0.90,
        })
        response = await client.get("/task-clusters/pid-1/workflows")
        assert response.status_code == 200
        data = response.json()
        assert data["task_cluster"] == "Refund Processing"
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["similarity"] == 0.92
        assert data["mode_stats"]["exploration"]["count"] == 5
        assert data["avg_conformance"] == 0.90

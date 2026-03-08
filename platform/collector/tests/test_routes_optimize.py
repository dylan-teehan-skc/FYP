"""Tests for optimization endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import AsyncClient

from .conftest import MockDatabase, MockEmbeddingService


class TestOptimizePath:
    async def test_exploration_when_no_paths(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        mock_db.find_similar_paths = AsyncMock(return_value=None)
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "exploration"
        assert data["path"] is None

    async def test_exploration_when_embedding_fails(
        self, client: AsyncClient, mock_embedding_service: MockEmbeddingService,
    ) -> None:
        mock_embedding_service.generate = AsyncMock(return_value=None)
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund"}
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "exploration"

    async def test_guided_mode_high_similarity(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        mock_db.find_similar_paths = AsyncMock(return_value={
            "tool_sequence": ["check_ticket", "get_order", "process_refund"],
            "avg_duration_ms": 2500.0,
            "avg_steps": 6.0,
            "success_rate": 0.95,
            "execution_count": 15,
            "similarity": 0.95,
            "guided_success_rate": None,
            "exploration_success_rate": None,
        })
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund for ORD-789"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "guided"
        assert data["path"] == ["check_ticket", "get_order", "process_refund"]
        assert data["confidence"] == 0.95
        assert data["success_rate"] == 0.95
        assert data["execution_count"] == 15

    async def test_exploration_when_below_threshold(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        mock_db.find_similar_paths = AsyncMock(return_value={
            "tool_sequence": ["check_ticket"],
            "avg_duration_ms": 1000.0,
            "avg_steps": 3.0,
            "success_rate": 0.80,
            "execution_count": 5,
            "similarity": 0.45,
            "guided_success_rate": None,
            "exploration_success_rate": None,
        })
        response = await client.post(
            "/optimize/path", json={"task_description": "Unknown task"}
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "exploration"

    async def test_exploration_when_guided_regresses(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        """Fall back to exploration when guided rate drops below exploration."""
        mock_db.find_similar_paths = AsyncMock(return_value={
            "tool_sequence": ["check_ticket", "get_order"],
            "avg_duration_ms": 2000.0,
            "avg_steps": 5.0,
            "success_rate": 0.90,
            "execution_count": 30,
            "similarity": 0.95,
            "guided_success_rate": 0.60,
            "exploration_success_rate": 0.90,
        })
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund"}
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "exploration"

    async def test_guided_when_no_regression_data(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        """Return guided when regression rates are null (no data yet)."""
        mock_db.find_similar_paths = AsyncMock(return_value={
            "tool_sequence": ["check_ticket", "get_order"],
            "avg_duration_ms": 2000.0,
            "avg_steps": 5.0,
            "success_rate": 0.90,
            "execution_count": 30,
            "similarity": 0.95,
            "guided_success_rate": None,
            "exploration_success_rate": None,
        })
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund"}
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "guided"

    async def test_guided_when_rates_within_margin(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        """Return guided when guided rate is within margin of exploration."""
        mock_db.find_similar_paths = AsyncMock(return_value={
            "tool_sequence": ["check_ticket", "get_order"],
            "avg_duration_ms": 2000.0,
            "avg_steps": 5.0,
            "success_rate": 0.90,
            "execution_count": 30,
            "similarity": 0.95,
            "guided_success_rate": 0.85,
            "exploration_success_rate": 0.90,
        })
        response = await client.post(
            "/optimize/path", json={"task_description": "Handle refund"}
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "guided"

    async def test_missing_task_description(self, client: AsyncClient) -> None:
        response = await client.post("/optimize/path", json={})
        assert response.status_code == 422

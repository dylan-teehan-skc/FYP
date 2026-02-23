"""Tests for analytics endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock

from httpx import AsyncClient

from .conftest import MockDatabase


class TestAnalyticsSummary:
    async def test_empty_database(self, client: AsyncClient) -> None:
        response = await client.get("/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_workflows"] == 0
        assert data["total_events"] == 0
        assert data["top_tools"] == []

    async def test_with_data(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_analytics_summary = AsyncMock(return_value={
            "total_workflows": 25,
            "total_events": 150,
            "avg_duration_ms": 2500.0,
            "avg_steps": 5.5,
            "success_rate": 0.92,
            "top_tools": [
                {"tool_name": "check_ticket", "call_count": 25, "avg_duration_ms": 200.0},
                {"tool_name": "get_order", "call_count": 20, "avg_duration_ms": 180.0},
            ],
        })
        response = await client.get("/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_workflows"] == 25
        assert data["success_rate"] == 0.92
        assert len(data["top_tools"]) == 2
        assert data["top_tools"][0]["tool_name"] == "check_ticket"

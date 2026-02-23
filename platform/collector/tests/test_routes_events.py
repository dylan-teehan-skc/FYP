"""Tests for event ingestion endpoints."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from .conftest import MockDatabase


class TestReceiveEvent:
    async def test_valid_event(
        self, client: AsyncClient, mock_db: MockDatabase, sample_event_data: dict[str, Any],
    ) -> None:
        response = await client.post("/events", json=sample_event_data)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_db.insert_event.assert_called_once()

    async def test_minimal_event(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440001",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440001",
            "timestamp": "2025-02-23T10:00:00Z",
            "activity": "workflow:start",
        }
        response = await client.post("/events", json=event)
        assert response.status_code == 200
        mock_db.insert_event.assert_called_once()

    async def test_invalid_status_rejected(self, client: AsyncClient) -> None:
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440002",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440002",
            "timestamp": "2025-02-23T10:00:00Z",
            "activity": "test",
            "status": "invalid",
        }
        response = await client.post("/events", json=event)
        assert response.status_code == 422

    async def test_missing_required_field(self, client: AsyncClient) -> None:
        event = {"event_id": "test", "timestamp": "2025-02-23T10:00:00Z", "activity": "test"}
        response = await client.post("/events", json=event)
        assert response.status_code == 422

    async def test_all_fields_populated(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440003",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440003",
            "timestamp": "2025-02-23T10:00:00Z",
            "activity": "tool_call:process_refund",
            "agent_name": "refund-agent",
            "agent_role": "processor",
            "tool_name": "process_refund",
            "tool_parameters": {"order_id": "ORD-5001"},
            "tool_response": {"refund_id": "R-001"},
            "llm_model": "gpt-4o",
            "llm_prompt_tokens": 500,
            "llm_completion_tokens": 150,
            "llm_reasoning": "Processing refund",
            "duration_ms": 1234.5,
            "cost_usd": 0.023,
            "status": "success",
            "error_message": None,
            "step_number": 4,
            "parent_event_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        response = await client.post("/events", json=event)
        assert response.status_code == 200


class TestReceiveBatch:
    async def test_valid_batch(
        self, client: AsyncClient, mock_db: MockDatabase, sample_event_data: dict[str, Any],
    ) -> None:
        batch = {"events": [sample_event_data]}
        response = await client.post("/events/batch", json=batch)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["count"] == 1
        mock_db.insert_events_batch.assert_called_once()

    async def test_multiple_events(
        self, client: AsyncClient, mock_db: MockDatabase, sample_event_data: dict[str, Any],
    ) -> None:
        event2 = sample_event_data.copy()
        event2["event_id"] = "550e8400-e29b-41d4-a716-446655440099"
        event2["step_number"] = 2
        batch = {"events": [sample_event_data, event2]}
        response = await client.post("/events/batch", json=batch)
        assert response.status_code == 200
        assert response.json()["count"] == 2

    async def test_empty_batch(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        batch = {"events": []}
        response = await client.post("/events/batch", json=batch)
        assert response.status_code == 200
        assert response.json()["count"] == 0

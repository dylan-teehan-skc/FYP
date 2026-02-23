"""Tests for workflow endpoints."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from httpx import AsyncClient

from .conftest import MockDatabase, MockEmbeddingService


class TestCompleteWorkflow:
    async def test_complete_success(
        self, client: AsyncClient, mock_db: MockDatabase,
    ) -> None:
        body = {
            "workflow_id": "660e8400-e29b-41d4-a716-446655440000",
            "task_description": "Handle refund for ORD-789",
            "total_steps": 6,
            "total_duration_ms": 5000.0,
            "status": "success",
        }
        response = await client.post("/workflows/complete", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["workflow_id"] == body["workflow_id"]

    async def test_complete_triggers_embedding(
        self, client: AsyncClient, mock_db: MockDatabase,
        mock_embedding_service: MockEmbeddingService,
    ) -> None:
        body = {
            "workflow_id": "660e8400-e29b-41d4-a716-446655440001",
            "task_description": "Handle refund",
            "total_steps": 3,
            "total_duration_ms": 2000.0,
        }
        await client.post("/workflows/complete", json=body)
        # Give the background task time to complete
        await asyncio.sleep(0.05)
        mock_db.upsert_embedding.assert_called_once()

    async def test_complete_with_failure_status(self, client: AsyncClient) -> None:
        body = {
            "workflow_id": "660e8400-e29b-41d4-a716-446655440002",
            "task_description": "Failed workflow",
            "total_steps": 2,
            "total_duration_ms": 1000.0,
            "status": "failure",
        }
        response = await client.post("/workflows/complete", json=body)
        assert response.status_code == 200


class TestGetTrace:
    async def test_trace_found(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_row = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "workflow_id": "660e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-02-23T10:00:00+00:00",
            "activity": "tool_call:check_ticket",
            "agent_name": "agent",
            "agent_role": "triage",
            "tool_name": "check_ticket",
            "tool_parameters": {},
            "tool_response": {},
            "llm_model": "",
            "llm_prompt_tokens": 0,
            "llm_completion_tokens": 0,
            "llm_reasoning": "",
            "duration_ms": 100.0,
            "cost_usd": 0.0,
            "status": "success",
            "error_message": None,
            "step_number": 1,
            "parent_event_id": None,
        }
        mock_db.get_workflow_trace = AsyncMock(return_value=[mock_row])
        response = await client.get("/workflows/660e8400-e29b-41d4-a716-446655440000/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert data["events"][0]["activity"] == "tool_call:check_ticket"

    async def test_trace_not_found(self, client: AsyncClient, mock_db: MockDatabase) -> None:
        mock_db.get_workflow_trace = AsyncMock(return_value=[])
        response = await client.get("/workflows/nonexistent-wf/trace")
        assert response.status_code == 404

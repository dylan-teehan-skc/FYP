"""Shared fixtures for collector tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from collector.app import create_app
from collector.config import Settings
from collector.websocket import ConnectionManager


class MockDatabase:
    """In-memory mock database for testing."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.embeddings: list[dict[str, Any]] = []
        self.insert_event = AsyncMock(side_effect=self._insert_event)
        self.insert_events_batch = AsyncMock(side_effect=self._insert_events_batch)
        self.get_workflow_trace = AsyncMock(return_value=[])
        self.get_task_description = AsyncMock(return_value=None)
        self.upsert_embedding = AsyncMock()
        self.find_similar_paths = AsyncMock(return_value=None)
        self.get_analytics_summary = AsyncMock(return_value={
            "total_workflows": 0,
            "total_events": 0,
            "avg_duration_ms": None,
            "avg_steps": None,
            "success_rate": None,
            "top_tools": [],
        })
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.list_workflows = AsyncMock(return_value={"workflows": [], "total": 0})
        self.list_optimal_paths = AsyncMock(return_value=[])
        self.get_mode_distribution = AsyncMock(
            return_value={"exploration": 0, "guided": 0, "total": 0}
        )
        self.get_mode_comparison = AsyncMock(return_value={
            "exploration": {
                "avg_duration_ms": None,
                "avg_steps": None,
                "success_rate": None,
                "count": 0,
            },
            "guided": {
                "avg_duration_ms": None,
                "avg_steps": None,
                "success_rate": None,
                "count": 0,
            },
        })
        self.get_timeline = AsyncMock(return_value=[])
        self.get_execution_graph = AsyncMock(return_value={"nodes": [], "edges": []})
        self.get_bottlenecks = AsyncMock(return_value=[])
        self.get_savings = AsyncMock(return_value={
            "time_saved_ms": 0.0,
            "cost_saved_usd": 0.0,
            "pct_duration_improvement": 0.0,
            "pct_steps_improvement": 0.0,
            "pct_success_improvement": 0.0,
            "guided_count": 0,
        })
        self.list_task_clusters = AsyncMock(return_value=[])
        self.get_cluster_workflows = AsyncMock(return_value={
            "path": None, "workflows": [], "mode_stats": None,
        })
        self.get_cluster_execution_graph = AsyncMock(
            return_value={"nodes": [], "edges": []}
        )
        self.get_cluster_bottlenecks = AsyncMock(return_value=[])
        self.get_group_path_ids = AsyncMock(return_value=[])
        self.get_group_workflows = AsyncMock(return_value={
            "workflows": [], "mode_stats": None, "avg_conformance": None,
        })
        self.get_group_execution_graph = AsyncMock(
            return_value={"nodes": [], "edges": []}
        )
        self.get_group_bottlenecks = AsyncMock(return_value=[])
        self.list_active_workflows = AsyncMock(return_value={"workflows": [], "total": 0})

    async def _insert_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    async def _insert_events_batch(self, events: list[dict[str, Any]]) -> None:
        self.events.extend(events)


class MockEmbeddingService:
    """Mock embedding service that returns deterministic vectors."""

    def __init__(self) -> None:
        self._model = "test-model"

    async def generate(self, text: str) -> list[float]:
        return [0.1] * 768


@pytest.fixture
def mock_db() -> MockDatabase:
    return MockDatabase()


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    return MockEmbeddingService()


@pytest.fixture
def app(mock_db: MockDatabase, mock_embedding_service: MockEmbeddingService):
    """Create a test app with mocked dependencies."""
    settings = Settings(database_url="postgresql://test:test@localhost/test")
    test_app = create_app(settings)
    test_app.state.settings = settings
    test_app.state.db = mock_db
    test_app.state.embedding_service = mock_embedding_service
    test_app.state.ws_manager = ConnectionManager()
    return test_app


@pytest.fixture
async def client(app):
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_event_data() -> dict[str, Any]:
    """A valid event payload as sent by the SDK."""
    return {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "workflow_id": "660e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-02-23T10:00:00Z",
        "activity": "tool_call:check_ticket",
        "agent_name": "triage-agent",
        "agent_role": "triage",
        "tool_name": "check_ticket",
        "tool_parameters": {"ticket_id": "T-1001"},
        "tool_response": {"status": "open"},
        "llm_model": "gpt-4",
        "llm_prompt_tokens": 100,
        "llm_completion_tokens": 50,
        "llm_reasoning": "Need to check ticket",
        "duration_ms": 230.0,
        "cost_usd": 0.002,
        "status": "success",
        "error_message": None,
        "step_number": 1,
        "parent_event_id": None,
    }

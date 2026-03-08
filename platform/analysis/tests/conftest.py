"""Shared fixtures for analysis engine tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from analysis.models import EventRecord, WorkflowTrace


class MockAnalysisDatabase:
    """In-memory mock database for analysis tests."""

    def __init__(self) -> None:
        self.fetch_all_workflow_ids = AsyncMock(return_value=[])
        self.fetch_workflow_events = AsyncMock(return_value=[])
        self.fetch_all_embeddings = AsyncMock(return_value=[])
        self.fetch_embedding_for_workflow = AsyncMock(return_value=[0.1] * 768)
        self.fetch_centroid_embedding = AsyncMock(return_value=[0.1] * 768)
        self.fetch_mode_success_rates = AsyncMock(
            return_value={"guided": None, "exploration": None}
        )
        self.upsert_optimal_path = AsyncMock()
        self.clear_optimal_paths = AsyncMock()
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()


@pytest.fixture
def mock_db() -> MockAnalysisDatabase:
    return MockAnalysisDatabase()


def make_event(
    workflow_id: str = "wf-1",
    activity: str = "tool_call:check_ticket",
    tool_name: str | None = "check_ticket",
    step_number: int = 1,
    duration_ms: float = 200.0,
    cost_usd: float = 0.001,
    status: str = "success",
    **kwargs: Any,
) -> EventRecord:
    """Helper to create an EventRecord with sensible defaults."""
    return EventRecord(
        event_id=kwargs.get("event_id", f"evt-{step_number}"),
        workflow_id=workflow_id,
        timestamp=kwargs.get("timestamp", datetime(2025, 2, 23, 10, 0, step_number,
                                                    tzinfo=UTC)),
        activity=activity,
        agent_name=kwargs.get("agent_name", "agent"),
        agent_role=kwargs.get("agent_role", "triage"),
        tool_name=tool_name,
        duration_ms=duration_ms,
        cost_usd=cost_usd,
        status=status,
        step_number=step_number,
    )


@pytest.fixture
def sample_events() -> list[EventRecord]:
    """6 events for T-1001 eligible refund workflow."""
    return [
        make_event(tool_name="check_ticket", step_number=1, duration_ms=230.0),
        make_event(tool_name="get_order", step_number=2, duration_ms=140.0,
                   activity="tool_call:get_order"),
        make_event(tool_name="check_refund_eligibility", step_number=3, duration_ms=95.0,
                   activity="tool_call:check_refund_eligibility"),
        make_event(tool_name="process_refund", step_number=4, duration_ms=320.0,
                   activity="tool_call:process_refund"),
        make_event(tool_name="send_message", step_number=5, duration_ms=180.0,
                   activity="tool_call:send_message"),
        make_event(tool_name="close_ticket", step_number=6, duration_ms=150.0,
                   activity="tool_call:close_ticket"),
    ]


@pytest.fixture
def sample_trace(sample_events: list[EventRecord]) -> WorkflowTrace:
    """Pre-built trace from sample_events."""
    return WorkflowTrace(
        workflow_id="wf-1",
        events=sample_events,
        tool_sequence=[
            "check_ticket", "get_order", "check_refund_eligibility",
            "process_refund", "send_message", "close_ticket",
        ],
        total_duration_ms=1115.0,
        total_cost_usd=0.006,
        total_steps=6,
        success=True,
    )


@pytest.fixture
def sample_traces_cluster(sample_trace: WorkflowTrace) -> list[WorkflowTrace]:
    """5 similar traces for testing cluster analysis."""
    traces = []
    for i in range(5):
        t = sample_trace.model_copy(deep=True)
        t.workflow_id = f"wf-{i + 1}"
        t.total_duration_ms = 1115.0 + i * 50
        traces.append(t)
    return traces

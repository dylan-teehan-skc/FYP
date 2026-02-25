"""Tests for trace reconstruction."""

from __future__ import annotations

from unittest.mock import AsyncMock

from analysis.models import WorkflowTrace
from analysis.traces import (
    compute_total_cost,
    compute_total_duration,
    compute_trace_success,
    extract_tool_sequence,
    reconstruct_all_traces,
    traces_to_dataframe,
)
from tests.conftest import MockAnalysisDatabase, make_event


class TestExtractToolSequence:
    def test_filters_non_tool_events(self) -> None:
        events = [
            make_event(activity="workflow:start", tool_name=None, step_number=0),
            make_event(tool_name="check_ticket", step_number=1),
            make_event(tool_name="get_order", step_number=2, activity="tool_call:get_order"),
            make_event(activity="workflow:complete", tool_name=None, step_number=3),
        ]
        result = extract_tool_sequence(events)
        assert result == ["check_ticket", "get_order"]

    def test_orders_by_step_number(self) -> None:
        events = [
            make_event(tool_name="b", step_number=2),
            make_event(tool_name="a", step_number=1),
        ]
        result = extract_tool_sequence(events)
        assert result == ["a", "b"]

    def test_empty_events(self) -> None:
        assert extract_tool_sequence([]) == []


class TestComputeTraceSuccess:
    def test_success(self) -> None:
        events = [
            make_event(tool_name="a", step_number=1),
            make_event(activity="workflow:complete", tool_name=None,
                       step_number=2, status="success"),
        ]
        assert compute_trace_success(events) is True

    def test_failure(self) -> None:
        events = [
            make_event(activity="workflow:complete", tool_name=None,
                       step_number=1, status="failure"),
        ]
        assert compute_trace_success(events) is False

    def test_no_complete_event(self) -> None:
        events = [make_event(tool_name="a", step_number=1)]
        assert compute_trace_success(events) is False


class TestComputeDuration:
    def test_uses_workflow_complete_duration(self) -> None:
        events = [
            make_event(tool_name="a", step_number=1, duration_ms=100.0),
            make_event(activity="workflow:complete", tool_name=None,
                       step_number=2, duration_ms=500.0),
        ]
        assert compute_total_duration(events) == 500.0

    def test_sums_tool_durations_without_complete(self) -> None:
        events = [
            make_event(tool_name="a", step_number=1, duration_ms=100.0),
            make_event(tool_name="b", step_number=2, duration_ms=200.0),
        ]
        assert compute_total_duration(events) == 300.0

    def test_compute_total_cost(self) -> None:
        events = [
            make_event(cost_usd=0.001, step_number=1),
            make_event(cost_usd=0.002, step_number=2),
        ]
        assert compute_total_cost(events) == pytest.approx(0.003)


class TestTracesToDataframe:
    def test_creates_dataframe(self, sample_trace: WorkflowTrace) -> None:
        df = traces_to_dataframe([sample_trace])
        assert len(df) == 6
        assert "case:concept:name" in df.columns
        assert "concept:name" in df.columns
        assert "time:timestamp" in df.columns

    def test_empty_traces(self) -> None:
        df = traces_to_dataframe([])
        assert len(df) == 0
        assert "case:concept:name" in df.columns


import pytest  # noqa: E402 (used by pytest.approx above)


class TestReconstructAllTraces:
    async def test_returns_traces(self) -> None:
        mock_db = MockAnalysisDatabase()
        mock_db.fetch_all_workflow_ids = AsyncMock(return_value=["wf-1", "wf-2"])
        mock_db.fetch_workflow_events = AsyncMock(return_value=[
            {
                "event_id": "evt-1",
                "workflow_id": "wf-1",
                "timestamp": "2025-02-23T10:00:01",
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
                "duration_ms": 200.0,
                "cost_usd": 0.001,
                "status": "success",
                "error_message": None,
                "step_number": 1,
                "parent_event_id": None,
            }
        ])
        traces = await reconstruct_all_traces(mock_db)
        assert len(traces) == 2
        assert all(isinstance(t, WorkflowTrace) for t in traces)

    async def test_empty_database(self) -> None:
        mock_db = MockAnalysisDatabase()
        mock_db.fetch_all_workflow_ids = AsyncMock(return_value=[])
        traces = await reconstruct_all_traces(mock_db)
        assert traces == []

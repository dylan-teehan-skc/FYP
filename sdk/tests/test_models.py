"""Tests for Pydantic v2 event and response models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from workflow_optimizer.models import (
    OptimalPathResponse,
    WorkflowCompleteRequest,
    WorkflowEvent,
)


class TestWorkflowEvent:
    def test_auto_generates_event_id(self) -> None:
        event = WorkflowEvent(workflow_id="wf-1", activity="tool_call:test")
        assert event.event_id
        uuid.UUID(event.event_id)  # validates UUID format

    def test_auto_generates_timestamp(self) -> None:
        before = datetime.now(UTC)
        event = WorkflowEvent(workflow_id="wf-1", activity="tool_call:test")
        after = datetime.now(UTC)
        assert before <= event.timestamp <= after

    def test_unique_event_ids(self) -> None:
        e1 = WorkflowEvent(workflow_id="wf-1", activity="test")
        e2 = WorkflowEvent(workflow_id="wf-1", activity="test")
        assert e1.event_id != e2.event_id

    def test_valid_status_values(self) -> None:
        for status in ("success", "failure", "timeout", "loop_detected"):
            event = WorkflowEvent(
                workflow_id="wf-1", activity="test", status=status
            )
            assert event.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError, match="status must be one of"):
            WorkflowEvent(workflow_id="wf-1", activity="test", status="invalid")

    def test_empty_activity_rejected(self) -> None:
        with pytest.raises(ValidationError, match="activity must not be empty"):
            WorkflowEvent(workflow_id="wf-1", activity="   ")

    def test_defaults_for_optional_fields(self) -> None:
        event = WorkflowEvent(workflow_id="wf-1", activity="test")
        assert event.agent_name == ""
        assert event.agent_role == ""
        assert event.tool_name is None
        assert event.tool_parameters == {}
        assert event.tool_response == {}
        assert event.llm_model == ""
        assert event.llm_prompt_tokens == 0
        assert event.llm_completion_tokens == 0
        assert event.llm_reasoning == ""
        assert event.duration_ms == 0.0
        assert event.cost_usd == 0.0
        assert event.status == "success"
        assert event.error_message is None
        assert event.step_number == 0
        assert event.parent_event_id is None

    def test_serialization_roundtrip(self) -> None:
        event = WorkflowEvent(
            workflow_id="wf-1",
            activity="tool_call:check_ticket",
            tool_name="check_ticket",
            tool_parameters={"ticket_id": "T-1"},
            duration_ms=42.5,
            step_number=1,
        )
        data = event.model_dump(mode="json")
        assert isinstance(data["timestamp"], str)  # ISO 8601
        assert data["workflow_id"] == "wf-1"
        assert data["tool_name"] == "check_ticket"
        restored = WorkflowEvent.model_validate(data)
        assert restored.workflow_id == event.workflow_id
        assert restored.tool_name == event.tool_name

    def test_full_event_with_all_fields(self) -> None:
        event = WorkflowEvent(
            workflow_id="wf-full",
            activity="tool_call:process_refund",
            agent_name="refund-agent",
            agent_role="processor",
            tool_name="process_refund",
            tool_parameters={"order_id": "ORD-5001"},
            tool_response={"refund_id": "R-001", "status": "processed"},
            llm_model="gpt-4o",
            llm_prompt_tokens=500,
            llm_completion_tokens=150,
            llm_reasoning="Customer eligible for refund",
            duration_ms=1234.5,
            cost_usd=0.023,
            status="success",
            step_number=4,
            parent_event_id="parent-123",
        )
        data = event.model_dump(mode="json")
        assert data["agent_name"] == "refund-agent"
        assert data["llm_prompt_tokens"] == 500
        assert data["cost_usd"] == 0.023
        assert data["parent_event_id"] == "parent-123"

    def test_llm_fields_default_to_zero(self) -> None:
        event = WorkflowEvent(workflow_id="wf-1", activity="test")
        assert event.llm_prompt_tokens == 0
        assert event.llm_completion_tokens == 0
        assert event.llm_reasoning == ""


class TestOptimalPathResponse:
    def test_exploration_mode(self) -> None:
        resp = OptimalPathResponse(mode="exploration")
        assert resp.mode == "exploration"
        assert resp.path is None
        assert resp.confidence is None

    def test_guided_mode(self) -> None:
        resp = OptimalPathResponse(
            mode="guided",
            path=["check_ticket", "get_order", "process_refund"],
            confidence=0.92,
            avg_duration_ms=3400.0,
            avg_steps=6.0,
            success_rate=0.95,
            execution_count=15,
        )
        assert resp.mode == "guided"
        assert len(resp.path) == 3
        assert resp.confidence == 0.92
        assert resp.execution_count == 15


class TestWorkflowCompleteRequest:
    def test_required_fields(self) -> None:
        req = WorkflowCompleteRequest(
            workflow_id="wf-1",
            task_description="Handle refund",
            total_steps=6,
            total_duration_ms=5000.0,
        )
        assert req.status == "success"

    def test_failure_status(self) -> None:
        req = WorkflowCompleteRequest(
            workflow_id="wf-1",
            task_description="Handle refund",
            total_steps=3,
            total_duration_ms=2000.0,
            status="failure",
        )
        assert req.status == "failure"

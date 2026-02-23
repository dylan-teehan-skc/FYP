"""Tests for TraceContext and StepContext context managers."""

from __future__ import annotations

import pytest

from workflow_optimizer.exceptions import TraceStateError
from workflow_optimizer.trace import TraceContext

from .conftest import MockTransport


class TestTraceContext:
    async def test_workflow_id_generated(self, mock_transport: MockTransport) -> None:
        trace = TraceContext("test task", mock_transport)
        assert trace.workflow_id
        assert len(trace.workflow_id) == 36  # UUID format

    async def test_start_event_emitted(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport):
            pass
        start_events = [e for e in mock_transport.events if e.activity == "workflow:start"]
        assert len(start_events) == 1

    async def test_complete_event_emitted(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport):
            pass
        complete_events = [e for e in mock_transport.events if e.activity == "workflow:complete"]
        assert len(complete_events) == 1
        assert complete_events[0].status == "success"

    async def test_fail_event_on_exception(self, mock_transport: MockTransport) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            async with TraceContext("test task", mock_transport):
                raise RuntimeError("boom")
        fail_events = [e for e in mock_transport.events if e.activity == "workflow:fail"]
        assert len(fail_events) == 1
        assert fail_events[0].status == "failure"
        assert fail_events[0].error_message == "boom"

    async def test_complete_workflow_called(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport):
            pass
        assert len(mock_transport.completed_workflows) == 1
        cw = mock_transport.completed_workflows[0]
        assert cw["task_description"] == "test task"
        assert cw["status"] == "success"

    async def test_agent_name_propagates(self, mock_transport: MockTransport) -> None:
        async with TraceContext(
            "test task", mock_transport, agent_name="test-agent", agent_role="tester",
        ):
            pass
        start_event = mock_transport.events[0]
        assert start_event.agent_name == "test-agent"
        assert start_event.agent_role == "tester"

    async def test_duration_tracked(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport):
            pass
        complete = [e for e in mock_transport.events if e.activity == "workflow:complete"][0]
        assert complete.duration_ms >= 0


class TestStepContext:
    async def test_step_counter_increments(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a"):
                pass
            with trace.step("tool_b"):
                pass
        step_events = [e for e in mock_transport.events if e.activity.startswith("tool_call:")]
        assert step_events[0].step_number == 1
        assert step_events[1].step_number == 2

    async def test_step_timing_captured(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a"):
                pass
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.duration_ms >= 0

    async def test_set_response(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a") as step:
                step.set_response({"result": "ok"})
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.tool_response == {"result": "ok"}

    async def test_set_error(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a") as step:
                step.set_error("something went wrong")
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.status == "failure"
        assert step_event.error_message == "something went wrong"

    async def test_set_cost(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a") as step:
                step.set_cost(0.05)
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.cost_usd == 0.05

    async def test_exception_sets_failure_status(self, mock_transport: MockTransport) -> None:
        with pytest.raises(ValueError, match="step error"):
            async with TraceContext("test task", mock_transport) as trace:
                with trace.step("tool_a"):
                    raise ValueError("step error")
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.status == "failure"
        assert step_event.error_message == "step error"

    async def test_step_outside_trace_raises(self, mock_transport: MockTransport) -> None:
        trace = TraceContext("test task", mock_transport)
        with pytest.raises(TraceStateError, match="Cannot create step outside active trace"):
            trace.step("tool_a")

    async def test_agent_name_cascade(self, mock_transport: MockTransport) -> None:
        async with TraceContext(
            "test task", mock_transport, agent_name="trace-agent",
        ) as trace:
            # Step without override inherits from trace
            with trace.step("tool_a"):
                pass
            # Step with override uses its own
            with trace.step("tool_b", agent_name="step-agent"):
                pass
        steps = [e for e in mock_transport.events if e.activity.startswith("tool_call:")]
        assert steps[0].agent_name == "trace-agent"
        assert steps[1].agent_name == "step-agent"

    async def test_event_id_accessible(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a") as step:
                assert step.event_id
                assert len(step.event_id) == 36

    async def test_parent_event_id(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("tool_a") as parent:
                pass
            with trace.step("tool_b", parent_event_id=parent.event_id):
                pass
        steps = [e for e in mock_transport.events if e.activity.startswith("tool_call:")]
        assert steps[1].parent_event_id == steps[0].event_id

    async def test_params_captured(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step("check_ticket", params={"ticket_id": "T-1001"}):
                pass
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.tool_parameters == {"ticket_id": "T-1001"}

    async def test_llm_fields_captured(self, mock_transport: MockTransport) -> None:
        async with TraceContext("test task", mock_transport) as trace:
            with trace.step(
                "tool_a",
                llm_model="gpt-4o",
                llm_prompt_tokens=100,
                llm_completion_tokens=50,
                llm_reasoning="decided to use tool_a",
            ):
                pass
        step_event = [e for e in mock_transport.events if e.activity.startswith("tool_call:")][0]
        assert step_event.llm_model == "gpt-4o"
        assert step_event.llm_prompt_tokens == 100
        assert step_event.llm_completion_tokens == 50
        assert step_event.llm_reasoning == "decided to use tool_a"

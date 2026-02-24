"""Trace and step context managers for workflow event capture."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from workflow_optimizer.exceptions import TraceStateError
from workflow_optimizer.models import WorkflowCompleteRequest, WorkflowEvent
from workflow_optimizer.transport import HttpTransport

logger = logging.getLogger("workflow_optimizer.trace")


class StepContext:
    """Sync context manager that captures a single workflow step."""

    def __init__(
        self,
        trace: TraceContext,
        tool_name: str,
        params: dict[str, Any] | None = None,
        agent_name: str = "",
        agent_role: str = "",
        llm_model: str = "",
        llm_prompt_tokens: int = 0,
        llm_completion_tokens: int = 0,
        llm_reasoning: str = "",
        parent_event_id: str | None = None,
    ) -> None:
        self._trace = trace
        self._tool_name = tool_name
        self._params = params or {}
        self._agent_name = agent_name
        self._agent_role = agent_role
        self._llm_model = llm_model
        self._llm_prompt_tokens = llm_prompt_tokens
        self._llm_completion_tokens = llm_completion_tokens
        self._llm_reasoning = llm_reasoning
        self._parent_event_id = parent_event_id
        self._event_id = str(uuid.uuid4())
        self._step_number = 0
        self._start_time = 0.0
        self._response: dict[str, Any] = {}
        self._status = "success"
        self._error_message: str | None = None
        self._cost_usd = 0.0

    @property
    def event_id(self) -> str:
        return self._event_id

    def set_response(self, response: dict[str, Any]) -> None:
        """Set the tool response after execution."""
        self._response = response

    def set_error(self, error: str) -> None:
        """Mark this step as failed with an error message."""
        self._status = "failure"
        self._error_message = error

    def set_cost(self, cost_usd: float) -> None:
        """Set the estimated cost of this step."""
        self._cost_usd = cost_usd

    def __enter__(self) -> StepContext:
        self._trace._step_counter += 1
        self._step_number = self._trace._step_counter
        self._start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        duration_ms = (time.perf_counter() - self._start_time) * 1000

        if exc_type is not None and self._status == "success":
            self._status = "failure"
            self._error_message = str(exc_val)

        event = WorkflowEvent(
            event_id=self._event_id,
            workflow_id=self._trace.workflow_id,
            activity=f"tool_call:{self._tool_name}",
            agent_name=self._agent_name or self._trace._agent_name,
            agent_role=self._agent_role or self._trace._agent_role,
            tool_name=self._tool_name,
            tool_parameters=self._params,
            tool_response=self._response,
            llm_model=self._llm_model,
            llm_prompt_tokens=self._llm_prompt_tokens,
            llm_completion_tokens=self._llm_completion_tokens,
            llm_reasoning=self._llm_reasoning,
            duration_ms=duration_ms,
            cost_usd=self._cost_usd,
            status=self._status,
            error_message=self._error_message,
            step_number=self._step_number,
            parent_event_id=self._parent_event_id,
        )
        self._trace._transport.enqueue(event)
        logger.debug(
            "Step captured, tool=%s, step=%d, status=%s, duration=%.1fms",
            self._tool_name, self._step_number, self._status, duration_ms,
        )


class TraceContext:
    """Async context manager that captures a full workflow trace."""

    def __init__(
        self,
        task_description: str,
        transport: HttpTransport,
        agent_name: str = "",
        agent_role: str = "",
    ) -> None:
        self._task_description = task_description
        self._transport = transport
        self._agent_name = agent_name
        self._agent_role = agent_role
        self._workflow_id = str(uuid.uuid4())
        self._step_counter = 0
        self._start_time = 0.0
        self._active = False

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    def step(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        *,
        agent_name: str | None = None,
        agent_role: str | None = None,
        llm_model: str = "",
        llm_prompt_tokens: int = 0,
        llm_completion_tokens: int = 0,
        llm_reasoning: str = "",
        parent_event_id: str | None = None,
    ) -> StepContext:
        """Create a step context manager for a single tool call."""
        if not self._active:
            msg = "Cannot create step outside active trace"
            raise TraceStateError(msg)
        return StepContext(
            trace=self,
            tool_name=tool_name,
            params=params,
            agent_name=agent_name or "",
            agent_role=agent_role or "",
            llm_model=llm_model,
            llm_prompt_tokens=llm_prompt_tokens,
            llm_completion_tokens=llm_completion_tokens,
            llm_reasoning=llm_reasoning,
            parent_event_id=parent_event_id,
        )

    def emit_mode(self, mode: str) -> None:
        """Emit an optimize:guided or optimize:exploration event."""
        if not self._active:
            msg = "Cannot emit mode outside active trace"
            raise TraceStateError(msg)
        event = WorkflowEvent(
            workflow_id=self._workflow_id,
            activity=f"optimize:{mode}",
            agent_name=self._agent_name,
            agent_role=self._agent_role,
            step_number=0,
        )
        self._transport.enqueue(event)
        logger.debug("Mode event emitted, workflow_id=%s, mode=%s", self._workflow_id, mode)

    async def __aenter__(self) -> TraceContext:
        if not self._transport._opened:
            await self._transport.open()
        self._active = True
        self._start_time = time.perf_counter()

        start_event = WorkflowEvent(
            workflow_id=self._workflow_id,
            activity="workflow:start",
            agent_name=self._agent_name,
            agent_role=self._agent_role,
            step_number=0,
        )
        self._transport.enqueue(start_event)
        logger.info(
            "Trace started, workflow_id=%s, task=%s",
            self._workflow_id, self._task_description,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        duration_ms = (time.perf_counter() - self._start_time) * 1000

        if exc_type is not None:
            fail_event = WorkflowEvent(
                workflow_id=self._workflow_id,
                activity="workflow:fail",
                agent_name=self._agent_name,
                agent_role=self._agent_role,
                duration_ms=duration_ms,
                status="failure",
                error_message=str(exc_val),
                step_number=self._step_counter + 1,
            )
            self._transport.enqueue(fail_event)
            status = "failure"
        else:
            complete_event = WorkflowEvent(
                workflow_id=self._workflow_id,
                activity="workflow:complete",
                agent_name=self._agent_name,
                agent_role=self._agent_role,
                duration_ms=duration_ms,
                status="success",
                step_number=self._step_counter + 1,
            )
            self._transport.enqueue(complete_event)
            status = "success"

        await self._transport.complete_workflow(
            WorkflowCompleteRequest(
                workflow_id=self._workflow_id,
                task_description=self._task_description,
                total_steps=self._step_counter,
                total_duration_ms=duration_ms,
                status=status,
            )
        )
        await self._transport.flush()
        self._active = False
        logger.info(
            "Trace ended, workflow_id=%s, status=%s, steps=%d, duration=%.1fms",
            self._workflow_id, status, self._step_counter, duration_ms,
        )

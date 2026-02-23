"""Shared fixtures for SDK tests."""

from __future__ import annotations

from typing import Any

import pytest

from workflow_optimizer.models import OptimalPathResponse, WorkflowEvent
from workflow_optimizer.transport import HttpTransport


class MockTransport(HttpTransport):
    """In-memory transport that records enqueued events without HTTP calls."""

    def __init__(self) -> None:
        super().__init__(endpoint="http://test:9000")
        self._opened = True
        self.events: list[WorkflowEvent] = []
        self.completed_workflows: list[dict[str, Any]] = []
        self._optimal_path_response = OptimalPathResponse(mode="exploration")

    def enqueue(self, event: WorkflowEvent) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        pass

    async def complete_workflow(self, request: Any) -> None:
        self.completed_workflows.append(request.model_dump())

    async def get_optimal_path(self, task_description: str) -> OptimalPathResponse:
        return self._optimal_path_response

    async def open(self) -> None:
        self._opened = True

    async def close(self) -> None:
        self._opened = False


@pytest.fixture
def mock_transport() -> MockTransport:
    return MockTransport()


@pytest.fixture
def sample_event() -> WorkflowEvent:
    return WorkflowEvent(
        workflow_id="wf-test-001",
        activity="tool_call:check_ticket",
        tool_name="check_ticket",
        tool_parameters={"ticket_id": "T-1001"},
        step_number=1,
    )

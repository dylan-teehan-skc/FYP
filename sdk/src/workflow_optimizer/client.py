"""WorkflowOptimizer client — public entry point for the SDK."""

from __future__ import annotations

import logging
from typing import Any

from workflow_optimizer.models import OptimalPathResponse
from workflow_optimizer.trace import TraceContext
from workflow_optimizer.transport import HttpTransport

logger = logging.getLogger("workflow_optimizer.client")


class WorkflowOptimizer:
    """Lightweight client that captures AI agent workflow traces.

    Usage::

        optimizer = WorkflowOptimizer(endpoint="http://localhost:9000")

        guidance = await optimizer.get_optimal_path("Handle refund")

        async with optimizer.trace("Handle refund") as trace:
            with trace.step("check_ticket", params={"id": "T-1"}) as step:
                result = await check_ticket("T-1")
                step.set_response(result)
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:9000",
        *,
        agent_name: str = "",
        agent_role: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        batch_size: int = 50,
        flush_interval: float = 5.0,
    ) -> None:
        self._transport = HttpTransport(
            endpoint=endpoint,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            batch_size=batch_size,
            flush_interval=flush_interval,
        )
        self._agent_name = agent_name
        self._agent_role = agent_role

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @property
    def agent_role(self) -> str:
        return self._agent_role

    async def open(self) -> None:
        """Explicitly open the transport. Called automatically on first use."""
        await self._transport.open()

    async def close(self) -> None:
        """Close the transport and flush remaining events."""
        await self._transport.close()

    async def __aenter__(self) -> WorkflowOptimizer:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    def trace(
        self,
        task_description: str,
        *,
        agent_name: str | None = None,
        agent_role: str | None = None,
    ) -> TraceContext:
        """Create a trace context manager for a full workflow.

        Agent name and role cascade: step override -> trace override -> optimizer default.
        """
        return TraceContext(
            task_description=task_description,
            transport=self._transport,
            agent_name=agent_name or self._agent_name,
            agent_role=agent_role or self._agent_role,
        )

    async def get_optimal_path(self, task_description: str) -> OptimalPathResponse:
        """Query the collector for the optimal execution path.

        Auto-opens transport if not already open. Returns exploration-mode
        response if the collector is unreachable.
        """
        if not self._transport._opened:
            await self._transport.open()
        return await self._transport.get_optimal_path(task_description)

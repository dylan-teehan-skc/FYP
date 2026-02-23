"""HTTP transport for communicating with the collector service."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from workflow_optimizer.models import (
    OptimalPathResponse,
    WorkflowCompleteRequest,
    WorkflowEvent,
)

logger = logging.getLogger("workflow_optimizer.transport")


class HttpTransport:
    """Async HTTP client for the collector with batching and retry."""

    def __init__(
        self,
        endpoint: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        batch_size: int = 50,
        flush_interval: float = 5.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._session: aiohttp.ClientSession | None = None
        self._buffer: list[WorkflowEvent] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._opened = False

    async def open(self) -> None:
        """Create the aiohttp session and start the flush loop."""
        if self._opened:
            return
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        self._flush_task = asyncio.create_task(self._flush_loop())
        self._opened = True
        logger.info("Transport opened, endpoint=%s", self._endpoint)

    async def close(self) -> None:
        """Flush remaining events and close the session."""
        if not self._opened:
            return
        self._opened = False
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()
        if self._session is not None:
            await self._session.close()
            self._session = None
        logger.info("Transport closed")

    def enqueue(self, event: WorkflowEvent) -> None:
        """Add an event to the buffer. Triggers flush if batch_size reached."""
        self._buffer.append(event)
        if len(self._buffer) >= self._batch_size:
            asyncio.create_task(self.flush())

    async def flush(self) -> None:
        """Send all buffered events to the collector in a batch."""
        async with self._buffer_lock:
            if not self._buffer:
                return
            batch = self._buffer.copy()
            self._buffer.clear()
        await self.send_batch(batch)

    async def send_event(self, event: WorkflowEvent) -> None:
        """Send a single event immediately (bypass buffer)."""
        await self._request(
            "POST", "/events", event.model_dump(mode="json")
        )

    async def send_batch(self, events: list[WorkflowEvent]) -> None:
        """Send a batch of events to POST /events/batch."""
        if not events:
            return
        payload = {"events": [e.model_dump(mode="json") for e in events]}
        await self._request("POST", "/events/batch", payload)

    async def complete_workflow(self, request: WorkflowCompleteRequest) -> None:
        """Send POST /workflows/complete to trigger embedding generation."""
        await self._request(
            "POST", "/workflows/complete", request.model_dump(mode="json")
        )

    async def get_optimal_path(self, task_description: str) -> OptimalPathResponse:
        """Query POST /optimize/path for optimal execution path."""
        data = await self._request(
            "POST", "/optimize/path", {"task_description": task_description}
        )
        if not data:
            return OptimalPathResponse(mode="exploration")
        return OptimalPathResponse.model_validate(data)

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry logic and graceful degradation."""
        if self._session is None:
            logger.warning("Transport not open, dropping request to %s", path)
            return {}

        url = f"{self._endpoint}{path}"
        last_error: str | None = None

        for attempt in range(self._max_retries):
            try:
                async with self._session.request(
                    method, url, json=json_data
                ) as response:
                    response.raise_for_status()
                    result: dict[str, Any] = await response.json()
                    return result
            except aiohttp.ClientError as e:
                last_error = str(e)
                logger.warning(
                    "Request retry, path=%s, attempt=%d, error=%s",
                    path, attempt + 1, last_error,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        logger.error(
            "Request failed after %d attempts, path=%s, error=%s",
            self._max_retries, path, last_error,
        )
        return {}

    async def _flush_loop(self) -> None:
        """Background task that periodically flushes the event buffer."""
        try:
            while True:
                await asyncio.sleep(self._flush_interval)
                await self.flush()
        except asyncio.CancelledError:
            pass

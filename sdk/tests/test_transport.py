"""Tests for HTTP transport layer."""

from __future__ import annotations

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses

from workflow_optimizer.models import WorkflowCompleteRequest, WorkflowEvent
from workflow_optimizer.transport import HttpTransport

ENDPOINT = "http://localhost:9000"


@pytest.fixture
def transport() -> HttpTransport:
    return HttpTransport(
        endpoint=ENDPOINT,
        timeout=5,
        max_retries=2,
        retry_delay=0.01,
        batch_size=3,
        flush_interval=60.0,
    )


class TestSessionLifecycle:
    async def test_open_creates_session(self, transport: HttpTransport) -> None:
        await transport.open()
        assert transport._opened is True
        assert transport._session is not None
        await transport.close()

    async def test_close_cleans_up(self, transport: HttpTransport) -> None:
        await transport.open()
        await transport.close()
        assert transport._opened is False
        assert transport._session is None
        assert transport._flush_task is None

    async def test_double_open_is_safe(self, transport: HttpTransport) -> None:
        await transport.open()
        session = transport._session
        await transport.open()  # should not create new session
        assert transport._session is session
        await transport.close()

    async def test_close_without_open_is_safe(self, transport: HttpTransport) -> None:
        await transport.close()  # should not raise


class TestBufferAndFlush:
    async def test_enqueue_adds_to_buffer(self, transport: HttpTransport) -> None:
        await transport.open()
        event = WorkflowEvent(workflow_id="wf-1", activity="test")
        transport.enqueue(event)
        assert len(transport._buffer) == 1
        await transport.close()

    async def test_flush_sends_batch(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(f"{ENDPOINT}/events/batch", payload={"status": "ok"})
            transport.enqueue(WorkflowEvent(workflow_id="wf-1", activity="s1"))
            transport.enqueue(WorkflowEvent(workflow_id="wf-1", activity="s2"))
            await transport.flush()
            assert len(transport._buffer) == 0
        await transport.close()

    async def test_flush_empty_buffer_is_noop(self, transport: HttpTransport) -> None:
        await transport.open()
        await transport.flush()  # should not make HTTP call or raise
        await transport.close()

    async def test_batch_size_triggers_flush(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(f"{ENDPOINT}/events/batch", payload={"status": "ok"})
            for i in range(3):
                transport.enqueue(WorkflowEvent(workflow_id="wf-1", activity=f"s{i}"))
            # Give the auto-flush task a moment to run
            await asyncio.sleep(0.05)
            assert len(transport._buffer) == 0
        await transport.close()


class TestRetryAndDegradation:
    async def test_retry_on_failure(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(f"{ENDPOINT}/events", exception=aiohttp.ClientConnectionError("network error"))
            m.post(f"{ENDPOINT}/events", payload={"status": "ok"})
            event = WorkflowEvent(workflow_id="wf-1", activity="test")
            await transport.send_event(event)
        await transport.close()

    async def test_max_retries_degrades_gracefully(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(f"{ENDPOINT}/events", exception=aiohttp.ClientConnectionError("fail"))
            m.post(f"{ENDPOINT}/events", exception=aiohttp.ClientConnectionError("fail"))
            event = WorkflowEvent(workflow_id="wf-1", activity="test")
            await transport.send_event(event)  # should not raise
        await transport.close()

    async def test_request_without_session_drops_silently(
        self, transport: HttpTransport,
    ) -> None:
        # Not opened, so _session is None
        result = await transport._request("POST", "/events", {})
        assert result == {}


class TestOptimalPath:
    async def test_guided_response(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(
                f"{ENDPOINT}/optimize/path",
                payload={
                    "mode": "guided",
                    "path": ["check_ticket", "get_order"],
                    "confidence": 0.9,
                    "avg_duration_ms": 2000.0,
                    "avg_steps": 5.0,
                    "success_rate": 0.95,
                    "execution_count": 10,
                },
            )
            result = await transport.get_optimal_path("Handle refund")
            assert result.mode == "guided"
            assert result.path == ["check_ticket", "get_order"]
            assert result.confidence == 0.9
        await transport.close()

    async def test_exploration_fallback_on_error(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(f"{ENDPOINT}/optimize/path", exception=aiohttp.ClientConnectionError("down"))
            m.post(f"{ENDPOINT}/optimize/path", exception=aiohttp.ClientConnectionError("down"))
            result = await transport.get_optimal_path("Handle refund")
            assert result.mode == "exploration"
            assert result.path is None
        await transport.close()


class TestCompleteWorkflow:
    async def test_complete_workflow_sends_request(self, transport: HttpTransport) -> None:
        await transport.open()
        with aioresponses() as m:
            m.post(f"{ENDPOINT}/workflows/complete", payload={"status": "ok"})
            req = WorkflowCompleteRequest(
                workflow_id="wf-1",
                task_description="test",
                total_steps=5,
                total_duration_ms=3000.0,
            )
            await transport.complete_workflow(req)
        await transport.close()

"""Tests for WebSocket connection manager."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from collector.websocket import ConnectionManager


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self, fail_send: bool = False) -> None:
        self.fail_send = fail_send
        self.accept = AsyncMock()
        self.send_json = AsyncMock(side_effect=self._send_json)
        self.closed = False

    async def _send_json(self, data: dict[str, Any]) -> None:
        if self.fail_send:
            raise Exception("Connection closed")


class TestConnectionManager:
    @pytest.fixture
    def manager(self) -> ConnectionManager:
        return ConnectionManager()

    async def test_connect(self, manager: ConnectionManager) -> None:
        ws = MockWebSocket()
        await manager.connect(ws, workflow_id="test-workflow-1")
        ws.accept.assert_called_once()
        assert ws in manager._connections
        assert manager._connections[ws] == "test-workflow-1"

    async def test_connect_without_filter(self, manager: ConnectionManager) -> None:
        ws = MockWebSocket()
        await manager.connect(ws, workflow_id=None)
        ws.accept.assert_called_once()
        assert ws in manager._connections
        assert manager._connections[ws] is None

    async def test_disconnect(self, manager: ConnectionManager) -> None:
        ws = MockWebSocket()
        await manager.connect(ws, workflow_id="test-workflow-1")
        assert ws in manager._connections
        await manager.disconnect(ws)
        assert ws not in manager._connections

    async def test_disconnect_nonexistent(self, manager: ConnectionManager) -> None:
        ws = MockWebSocket()
        await manager.disconnect(ws)
        assert ws not in manager._connections

    async def test_broadcast_no_connections(self, manager: ConnectionManager) -> None:
        event_data = {"workflow_id": "test-wf-1", "event": "test"}
        await manager.broadcast(event_data)

    async def test_broadcast_to_all(self, manager: ConnectionManager) -> None:
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await manager.connect(ws1, workflow_id=None)
        await manager.connect(ws2, workflow_id=None)

        event_data = {"workflow_id": "test-wf-1", "event": "test"}
        await manager.broadcast(event_data)

        ws1.send_json.assert_called_once_with(event_data)
        ws2.send_json.assert_called_once_with(event_data)

    async def test_broadcast_with_filter_match(self, manager: ConnectionManager) -> None:
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await manager.connect(ws1, workflow_id="test-wf-1")
        await manager.connect(ws2, workflow_id="test-wf-2")

        event_data = {"workflow_id": "test-wf-1", "event": "test"}
        await manager.broadcast(event_data)

        ws1.send_json.assert_called_once_with(event_data)
        ws2.send_json.assert_not_called()

    async def test_broadcast_removes_dead_connections(
        self, manager: ConnectionManager
    ) -> None:
        ws1 = MockWebSocket(fail_send=True)
        ws2 = MockWebSocket()
        await manager.connect(ws1, workflow_id=None)
        await manager.connect(ws2, workflow_id=None)

        event_data = {"workflow_id": "test-wf-1", "event": "test"}
        await manager.broadcast(event_data)

        assert ws1 not in manager._connections
        assert ws2 in manager._connections
        ws2.send_json.assert_called_once_with(event_data)

    async def test_broadcast_batch(self, manager: ConnectionManager) -> None:
        ws = MockWebSocket()
        await manager.connect(ws, workflow_id=None)

        events = [
            {"workflow_id": "wf-1", "event": "test1"},
            {"workflow_id": "wf-2", "event": "test2"},
        ]
        await manager.broadcast_batch(events)

        assert ws.send_json.call_count == 2
        ws.send_json.assert_any_call(events[0])
        ws.send_json.assert_any_call(events[1])

    async def test_broadcast_batch_empty(self, manager: ConnectionManager) -> None:
        ws = MockWebSocket()
        await manager.connect(ws, workflow_id=None)

        await manager.broadcast_batch([])

        ws.send_json.assert_not_called()

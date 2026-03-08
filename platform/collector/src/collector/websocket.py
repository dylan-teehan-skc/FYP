"""WebSocket connection manager for real-time event broadcasting."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from collector.logger import get_logger

log = get_logger("collector.websocket")


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, str | None] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, workflow_id: str | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = workflow_id
        log.info("ws_connected", workflow_filter=workflow_id)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(self, event_data: dict[str, Any]) -> None:
        """Send an event to all connected clients (filtered by workflow_id)."""
        async with self._lock:
            connections = list(self._connections.items())

        if not connections:
            return

        workflow_id = str(event_data.get("workflow_id", ""))
        dead: list[WebSocket] = []

        for ws, filter_id in connections:
            if filter_id is not None and filter_id != workflow_id:
                continue
            try:
                await ws.send_json(event_data)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)

    async def broadcast_batch(self, events: list[dict[str, Any]]) -> None:
        for event_data in events:
            await self.broadcast(event_data)

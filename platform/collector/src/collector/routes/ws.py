"""WebSocket endpoint for real-time event streaming."""

from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    workflow_id: str | None = Query(default=None),
) -> None:
    manager = websocket.app.state.ws_manager
    await manager.connect(websocket, workflow_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

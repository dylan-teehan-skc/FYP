"""Tests for WebSocket endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import WebSocketDisconnect


class TestWebSocketEvents:
    async def test_websocket_connection(self, app) -> None:
        """Test WebSocket connection and disconnection."""
        mock_ws = AsyncMock()
        mock_ws.app = app
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

        mock_manager = AsyncMock()
        with patch.object(app.state, "ws_manager", mock_manager):
            from collector.routes.ws import websocket_events

            await websocket_events(mock_ws, workflow_id="test-workflow-1")

            mock_manager.connect.assert_called_once_with(
                mock_ws, "test-workflow-1"
            )
            mock_manager.disconnect.assert_called_once_with(mock_ws)

    async def test_websocket_connection_no_filter(self, app) -> None:
        """Test WebSocket connection without workflow filter."""
        mock_ws = AsyncMock()
        mock_ws.app = app
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

        mock_manager = AsyncMock()
        with patch.object(app.state, "ws_manager", mock_manager):
            from collector.routes.ws import websocket_events

            await websocket_events(mock_ws, workflow_id=None)

            mock_manager.connect.assert_called_once_with(mock_ws, None)
            mock_manager.disconnect.assert_called_once_with(mock_ws)

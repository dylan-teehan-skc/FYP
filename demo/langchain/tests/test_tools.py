"""Tests for MCP tool wrappers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools import (
    _call_mcp,
    check_ticket_status,
    get_order_details,
    process_refund,
    reset_mcp_state,
)


def _make_mock_client(json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx.AsyncClient with sync json()/raise_for_status()."""
    response = MagicMock()
    response.json.return_value = json_data or {"status": "ok"}
    response.raise_for_status.return_value = None

    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_client() -> MagicMock:
    return _make_mock_client()


class TestCallMCP:
    @pytest.mark.asyncio
    async def test_posts_to_tools_call(self, mock_client: MagicMock) -> None:
        with patch("tools._get_client", return_value=mock_client):
            result = await _call_mcp("check_ticket_status", {"ticket_id": "T-1001"})

        mock_client.post.assert_called_once_with(
            "/tools/call",
            json={"name": "check_ticket_status", "arguments": {"ticket_id": "T-1001"}},
        )
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self) -> None:
        client = _make_mock_client()
        client.post.return_value.raise_for_status.side_effect = Exception("500")
        with patch("tools._get_client", return_value=client):
            with pytest.raises(Exception, match="500"):
                await _call_mcp("bad_tool", {})


class TestToolFunctions:
    @pytest.mark.asyncio
    async def test_check_ticket_status(self) -> None:
        client = _make_mock_client({"ticket_id": "T-1001", "status": "open"})
        with patch("tools._get_client", return_value=client):
            result = await check_ticket_status.ainvoke({"ticket_id": "T-1001"})

        parsed = json.loads(result)
        assert parsed["ticket_id"] == "T-1001"
        assert parsed["status"] == "open"

    @pytest.mark.asyncio
    async def test_get_order_details(self) -> None:
        client = _make_mock_client({"order_id": "ORD-5001", "total": 79.99})
        with patch("tools._get_client", return_value=client):
            result = await get_order_details.ainvoke({"order_id": "ORD-5001"})

        parsed = json.loads(result)
        assert parsed["order_id"] == "ORD-5001"

    @pytest.mark.asyncio
    async def test_process_refund(self) -> None:
        client = _make_mock_client({"refund_id": "R-100"})
        with patch("tools._get_client", return_value=client):
            result = await process_refund.ainvoke({
                "order_id": "ORD-5001",
                "amount": 79.99,
                "reason": "defective",
            })

        parsed = json.loads(result)
        assert parsed["refund_id"] == "R-100"


class TestResetMCPState:
    @pytest.mark.asyncio
    async def test_posts_reset(self, mock_client: MagicMock) -> None:
        with patch("tools._get_client", return_value=mock_client):
            await reset_mcp_state()

        mock_client.post.assert_called_once_with("/reset")

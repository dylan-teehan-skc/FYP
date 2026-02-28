"""LangChain tool definitions wrapping MCP tool server calls."""

from __future__ import annotations

import json
from typing import Any

import httpx
from langchain_core.tools import tool

MCP_SERVER_URL = "http://localhost:8000"
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=MCP_SERVER_URL, timeout=30.0)
    return _client


async def set_mcp_url(url: str) -> None:
    global _client, MCP_SERVER_URL
    MCP_SERVER_URL = url
    if _client is not None:
        await _client.aclose()
    _client = httpx.AsyncClient(base_url=url, timeout=30.0)


async def _call_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    client = _get_client()
    resp = await client.post("/tools/call", json={"name": tool_name, "arguments": arguments})
    resp.raise_for_status()
    return resp.json()


async def reset_mcp_state() -> None:
    client = _get_client()
    resp = await client.post("/reset")
    resp.raise_for_status()


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@tool
async def check_ticket_status(ticket_id: str) -> str:
    """Retrieve current status of a support ticket."""
    result = await _call_mcp("check_ticket_status", {"ticket_id": ticket_id})
    return json.dumps(result)


@tool
async def get_order_details(order_id: str) -> str:
    """Get details of a customer order including items, total, and payment status."""
    result = await _call_mcp("get_order_details", {"order_id": order_id})
    return json.dumps(result)


@tool
async def check_refund_eligibility(order_id: str) -> str:
    """Check if an order is eligible for refund based on return policy."""
    result = await _call_mcp("check_refund_eligibility", {"order_id": order_id})
    return json.dumps(result)


@tool
async def process_refund(order_id: str, amount: float, reason: str) -> str:
    """Process a refund for an eligible order."""
    result = await _call_mcp(
        "process_refund", {"order_id": order_id, "amount": amount, "reason": reason}
    )
    return json.dumps(result)


@tool
async def send_customer_message(customer_id: str, subject: str, message: str) -> str:
    """Send a message to the customer via email."""
    result = await _call_mcp(
        "send_customer_message",
        {"customer_id": customer_id, "subject": subject, "message": message},
    )
    return json.dumps(result)


@tool
async def close_ticket(ticket_id: str, resolution_summary: str) -> str:
    """Mark ticket as resolved with a resolution summary."""
    result = await _call_mcp(
        "close_ticket", {"ticket_id": ticket_id, "resolution_summary": resolution_summary}
    )
    return json.dumps(result)


@tool
async def get_customer_history(customer_id: str) -> str:
    """Retrieve past orders and tickets for a customer."""
    result = await _call_mcp("get_customer_history", {"customer_id": customer_id})
    return json.dumps(result)


@tool
async def search_knowledge_base(query: str) -> str:
    """Search internal documentation for policies and procedures."""
    result = await _call_mcp("search_knowledge_base", {"query": query})
    return json.dumps(result)


@tool
async def escalate_ticket(ticket_id: str, reason: str) -> str:
    """Escalate a support ticket to a supervisor with a reason."""
    result = await _call_mcp("escalate_ticket", {"ticket_id": ticket_id, "reason": reason})
    return json.dumps(result)


@tool
async def apply_discount(order_id: str, discount_percent: float, reason: str = "") -> str:
    """Apply a percentage discount to a customer order."""
    args: dict[str, Any] = {"order_id": order_id, "discount_percent": discount_percent}
    if reason:
        args["reason"] = reason
    result = await _call_mcp("apply_discount", args)
    return json.dumps(result)


@tool
async def check_warranty(order_id: str) -> str:
    """Check warranty status and coverage for an order."""
    result = await _call_mcp("check_warranty", {"order_id": order_id})
    return json.dumps(result)


@tool
async def get_shipping_status(order_id: str) -> str:
    """Get shipping and tracking information for an order."""
    result = await _call_mcp("get_shipping_status", {"order_id": order_id})
    return json.dumps(result)


@tool
async def schedule_callback(customer_id: str, topic: str, preferred_time: str = "") -> str:
    """Schedule a phone callback for a customer."""
    args: dict[str, Any] = {"customer_id": customer_id, "topic": topic}
    if preferred_time:
        args["preferred_time"] = preferred_time
    result = await _call_mcp("schedule_callback", args)
    return json.dumps(result)


ALL_TOOLS = [
    check_ticket_status,
    get_order_details,
    check_refund_eligibility,
    process_refund,
    send_customer_message,
    close_ticket,
    get_customer_history,
    search_knowledge_base,
    escalate_ticket,
    apply_discount,
    check_warranty,
    get_shipping_status,
    schedule_callback,
]

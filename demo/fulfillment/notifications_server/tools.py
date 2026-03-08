"""Tool implementations for the notifications MCP server."""

from __future__ import annotations

import uuid

from mcp_server import database as db


def get_notification_preferences(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}
    row = db.get_notification_preferences(customer_id)
    if not row:
        return {"error": f"No notification preferences found for {customer_id}"}
    return {
        "customer_id": row["customer_id"],
        "email": row["email"],
        "phone": row["phone"],
        "preferred_channel": row["preferred"],
        "opted_out": bool(row["opted_out"]),
    }


def send_notification(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    order_id = arguments.get("order_id")
    channel = arguments.get("channel")
    template = arguments.get("template")

    if not customer_id or not order_id or not channel or not template:
        return {"error": "customer_id, order_id, channel, and template are required"}

    prefs = db.get_notification_preferences(customer_id)
    if not prefs:
        return {"error": f"No notification preferences found for {customer_id}"}

    if prefs["opted_out"]:
        return {"error": "Customer has opted out of notifications"}

    if channel == "sms" and not prefs["phone"]:
        return {"error": "Notification could not be sent via this channel"}

    notification_id = f"NOTIF-{uuid.uuid4().hex[:8]}"
    db.create_notification(notification_id, customer_id, order_id, channel, template)

    return {
        "notification_id": notification_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "channel": channel,
        "template": template,
        "status": "sent",
    }


def get_notification_history(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}
    rows = db.get_notifications_for_order(order_id)
    return {
        "order_id": order_id,
        "notifications": [
            {
                "notification_id": r["notification_id"],
                "customer_id": r["customer_id"],
                "channel": r["channel"],
                "template": r["template"],
            }
            for r in rows
        ],
    }


DISPATCH: dict[str, callable] = {
    "get_notification_preferences": get_notification_preferences,
    "send_notification": send_notification,
    "get_notification_history": get_notification_history,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments)

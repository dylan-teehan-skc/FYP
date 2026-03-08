"""Tool implementations for the inventory management MCP server."""

from __future__ import annotations

import uuid

from mcp_server import database as db


def reserve_inventory(arguments: dict) -> dict:
    warehouse_id = arguments.get("warehouse_id")
    product_id = arguments.get("product_id")
    quantity = arguments.get("quantity")

    if not warehouse_id or not product_id or quantity is None:
        return {"error": "warehouse_id, product_id, and quantity are required"}

    quantity = int(quantity)
    reservation_id = f"RES-{uuid.uuid4().hex[:8]}"

    success = db.create_reservation(
        reservation_id, warehouse_id, product_id, quantity,
    )
    if not success:
        return {"error": "Reservation failed"}

    return {
        "reservation_id": reservation_id,
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "quantity": quantity,
        "status": "active",
    }


def cancel_reservation(arguments: dict) -> dict:
    reservation_id = arguments.get("reservation_id")
    if not reservation_id:
        return {"error": "reservation_id is required"}

    result = db.cancel_reservation(reservation_id)
    if not result:
        return {"error": f"Reservation {reservation_id} not found or not active"}

    return {
        "reservation_id": reservation_id,
        "status": "cancelled",
        "restored_quantity": result["quantity"],
        "warehouse_id": result["warehouse_id"],
        "product_id": result["product_id"],
    }


def get_reservation(arguments: dict) -> dict:
    reservation_id = arguments.get("reservation_id")
    if not reservation_id:
        return {"error": "reservation_id is required"}

    row = db.get_reservation(reservation_id)
    if not row:
        return {"error": f"Reservation {reservation_id} not found"}

    return {
        "reservation_id": row["reservation_id"],
        "warehouse_id": row["warehouse_id"],
        "product_id": row["product_id"],
        "quantity": row["quantity"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def check_restock_eta(arguments: dict) -> dict:
    warehouse_id = arguments.get("warehouse_id")
    product_id = arguments.get("product_id")
    if not warehouse_id or not product_id:
        return {"error": "warehouse_id and product_id are required"}

    row = db.get_restock_eta(warehouse_id, product_id)
    if not row or row["expected_date"] is None:
        return {
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "restock_scheduled": False,
            "message": "No restock currently scheduled",
        }

    return {
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "restock_scheduled": True,
        "expected_date": row["expected_date"],
        "expected_quantity": row["quantity"],
    }


DISPATCH: dict[str, callable] = {
    "reserve_inventory": reserve_inventory,
    "cancel_reservation": cancel_reservation,
    "get_reservation": get_reservation,
    "check_restock_eta": check_restock_eta,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments)

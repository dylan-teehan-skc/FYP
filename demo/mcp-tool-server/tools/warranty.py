"""Warranty tool: check_warranty."""

from data import WARRANTY_DAYS


def check_warranty(arguments: dict, state) -> dict:
    order_id = arguments.get("order_id")
    order = state.get_order(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}

    if order["status"] != "delivered":
        return {
            "order_id": order_id,
            "warranty_status": "not_applicable",
            "reason": f"Order status is '{order['status']}', warranty starts after delivery",
        }

    days = order.get("days_since_delivery")
    if days is None:
        return {
            "order_id": order_id,
            "warranty_status": "unknown",
            "reason": "Delivery date not available",
        }

    remaining = WARRANTY_DAYS - days
    if remaining <= 0:
        return {
            "order_id": order_id,
            "warranty_status": "expired",
            "warranty_period_days": WARRANTY_DAYS,
            "days_since_delivery": days,
            "message": "Warranty has expired",
        }

    return {
        "order_id": order_id,
        "warranty_status": "active",
        "warranty_period_days": WARRANTY_DAYS,
        "days_since_delivery": days,
        "days_remaining": remaining,
        "message": f"Warranty active — {remaining} days remaining",
    }

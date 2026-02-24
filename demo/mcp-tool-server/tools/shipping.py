"""Shipping tool: get_shipping_status."""

from data import SHIPPING_INFO


def get_shipping_status(arguments: dict, state) -> dict:
    order_id = arguments.get("order_id")
    order = state.get_order(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}

    if order["status"] == "processing":
        return {
            "order_id": order_id,
            "shipping_status": "not_shipped",
            "message": "Order is still being processed and has not shipped yet",
        }

    if order["status"] == "delivered":
        return {
            "order_id": order_id,
            "shipping_status": "delivered",
            "message": (
                f"Order was delivered {order['days_since_delivery']} days ago"
            ),
        }

    shipping = SHIPPING_INFO.get(order_id)
    if shipping is None:
        return {
            "order_id": order_id,
            "shipping_status": "shipped",
            "message": "Order has shipped but tracking details are unavailable",
        }

    return {
        "order_id": order_id,
        "shipping_status": shipping["status"],
        "carrier": shipping["carrier"],
        "tracking_number": shipping["tracking_number"],
        "estimated_delivery": shipping["estimated_delivery"],
        "last_location": shipping["last_location"],
    }

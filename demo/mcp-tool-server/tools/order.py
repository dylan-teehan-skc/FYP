"""Order tools: get_order_details, check_refund_eligibility, process_refund."""

from data import REFUND_WINDOW_DAYS, _days_ago


def get_order_details(arguments: dict, state) -> dict:
    order_id = arguments.get("order_id")
    order = state.get_order(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}

    result = {
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "product": order["product"],
        "amount": order["amount"],
        "status": order["status"],
        "payment_method": order["payment_method"],
    }

    if order["days_since_delivery"] is not None:
        result["delivered_at"] = _days_ago(order["days_since_delivery"])
    else:
        result["delivered_at"] = None

    if order.get("refund_status"):
        result["refund_status"] = order["refund_status"]

    return result


def check_refund_eligibility(arguments: dict, state) -> dict:
    order_id = arguments.get("order_id")
    order = state.get_order(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}

    if state.is_refund_processed(order_id):
        return {
            "order_id": order_id,
            "eligible": False,
            "reason": "Refund has already been processed for this order",
        }

    if order["status"] != "delivered":
        return {
            "order_id": order_id,
            "eligible": False,
            "reason": (
                f"Order status is '{order['status']}', "
                "refunds only available for delivered orders"
            ),
        }

    days = order["days_since_delivery"]
    if days is not None and days > REFUND_WINDOW_DAYS:
        return {
            "order_id": order_id,
            "eligible": False,
            "reason": (
                f"Order was delivered {days} days ago, "
                f"outside the {REFUND_WINDOW_DAYS}-day return window"
            ),
        }

    return {
        "order_id": order_id,
        "eligible": True,
        "max_refund_amount": order["amount"],
        "reason": f"Order is within the {REFUND_WINDOW_DAYS}-day return window",
    }


def process_refund(arguments: dict, state) -> dict:
    order_id = arguments.get("order_id")
    amount = arguments.get("amount")
    reason = arguments.get("reason", "")

    order = state.get_order(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}

    if state.is_refund_processed(order_id):
        return {"error": f"Refund already processed for order {order_id}"}

    if amount is not None and amount > order["amount"]:
        return {"error": f"Refund amount ${amount} exceeds order total ${order['amount']}"}

    refund = state.process_refund(order_id, amount or order["amount"], reason)
    return {
        "refund_id": refund["refund_id"],
        "order_id": order_id,
        "amount": refund["amount"],
        "status": "processed",
        "estimated_arrival": "3-5 business days",
        "processed_at": refund["processed_at"],
    }

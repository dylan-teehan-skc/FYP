"""Customer tools: get_customer_history, send_customer_message."""

from data import CUSTOMERS


def get_customer_history(arguments: dict, state) -> dict:
    customer_id = arguments.get("customer_id")
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}

    orders = [
        {
            "order_id": o["order_id"],
            "product": o["product"],
            "amount": o["amount"],
            "status": o["status"],
        }
        for o in state.orders.values()
        if o["customer_id"] == customer_id
    ]

    tickets = [
        {
            "ticket_id": t["ticket_id"],
            "type": t["type"],
            "status": t["status"],
            "subject": t["subject"],
        }
        for t in state.tickets.values()
        if t["customer_id"] == customer_id
    ]

    total_spent = sum(o["amount"] for o in orders)

    return {
        "customer_id": customer_id,
        "name": customer["name"],
        "email": customer["email"],
        "tier": customer["tier"],
        "orders": orders,
        "tickets": tickets,
        "total_spent": total_spent,
    }


def send_customer_message(arguments: dict, state) -> dict:
    customer_id = arguments.get("customer_id")
    subject = arguments.get("subject", "")
    message = arguments.get("message", "")

    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}

    record = state.record_message(customer_id, subject, message)
    return {
        "message_id": record["message_id"],
        "sent_to": customer["email"],
        "subject": subject,
        "status": "sent",
        "sent_at": record["sent_at"],
    }


def apply_discount(arguments: dict, state) -> dict:
    order_id = arguments.get("order_id")
    discount_percent = arguments.get("discount_percent", 0)
    reason = arguments.get("reason", "")

    order = state.get_order(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}

    if discount_percent < 1 or discount_percent > 50:
        return {"error": "Discount must be between 1% and 50%"}

    if order_id in state.applied_discounts:
        return {"error": f"Discount already applied to order {order_id}"}

    record = state.apply_discount(order_id, discount_percent, reason)
    return {
        "order_id": order_id,
        "original_amount": record["original_amount"],
        "discount_percent": record["discount_percent"],
        "new_amount": record["new_amount"],
        "status": "applied",
        "applied_at": record["applied_at"],
    }


def schedule_callback(arguments: dict, state) -> dict:
    customer_id = arguments.get("customer_id")
    preferred_time = arguments.get("preferred_time", "next business day")
    topic = arguments.get("topic", "")

    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}

    record = state.schedule_callback(customer_id, preferred_time, topic)
    return {
        "callback_id": record["callback_id"],
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "preferred_time": preferred_time,
        "topic": topic,
        "status": "scheduled",
        "scheduled_at": record["scheduled_at"],
    }

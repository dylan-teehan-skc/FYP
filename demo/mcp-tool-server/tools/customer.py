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

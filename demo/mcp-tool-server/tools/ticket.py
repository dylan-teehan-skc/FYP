"""Ticket tools: check_ticket_status, close_ticket."""


def check_ticket_status(arguments: dict, state) -> dict:
    ticket_id = arguments.get("ticket_id")
    ticket = state.get_ticket(ticket_id)
    if ticket is None:
        return {"error": f"Ticket {ticket_id} not found"}
    return {
        "ticket_id": ticket["ticket_id"],
        "status": ticket["status"],
        "type": ticket["type"],
        "subject": ticket["subject"],
        "customer_id": ticket["customer_id"],
        "order_id": ticket["order_id"],
        "created_at": ticket["created_at"],
    }


def close_ticket(arguments: dict, state) -> dict:
    ticket_id = arguments.get("ticket_id")
    resolution_summary = arguments.get("resolution_summary", "")

    ticket = state.get_ticket(ticket_id)
    if ticket is None:
        return {"error": f"Ticket {ticket_id} not found"}
    if ticket["status"] == "closed":
        return {"error": f"Ticket {ticket_id} is already closed"}

    updated = state.close_ticket(ticket_id, resolution_summary)
    return {
        "ticket_id": updated["ticket_id"],
        "status": "closed",
        "resolution_summary": resolution_summary,
        "closed_at": updated["closed_at"],
    }

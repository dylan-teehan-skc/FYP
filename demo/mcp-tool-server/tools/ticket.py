"""Ticket tools: check_ticket_status, close_ticket, escalate_ticket."""


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


def escalate_ticket(arguments: dict, state) -> dict:
    ticket_id = arguments.get("ticket_id")
    reason = arguments.get("reason", "")

    ticket = state.get_ticket(ticket_id)
    if ticket is None:
        return {"error": f"Ticket {ticket_id} not found"}
    if ticket["status"] == "escalated":
        return {"error": f"Ticket {ticket_id} is already escalated"}

    result = state.escalate_ticket(ticket_id, reason)
    return {
        "ticket_id": result["ticket_id"],
        "status": "escalated",
        "reason": reason,
        "escalated_at": result["escalated_at"],
        "message": "Ticket has been escalated to a supervisor",
    }

"""Tool dispatcher for the MCP tool server."""

from tools.customer import get_customer_history, send_customer_message
from tools.knowledge import search_knowledge_base
from tools.order import check_refund_eligibility, get_order_details, process_refund
from tools.schemas import TOOLS
from tools.ticket import check_ticket_status, close_ticket

_DISPATCH = {
    "check_ticket_status": check_ticket_status,
    "get_order_details": get_order_details,
    "check_refund_eligibility": check_refund_eligibility,
    "process_refund": process_refund,
    "send_customer_message": send_customer_message,
    "close_ticket": close_ticket,
    "get_customer_history": get_customer_history,
    "search_knowledge_base": search_knowledge_base,
}


def execute_tool(name: str, arguments: dict, state) -> dict:
    handler = _DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments, state)


__all__ = ["TOOLS", "execute_tool"]

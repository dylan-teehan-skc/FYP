"""Tool definitions with input schemas for the MCP protocol."""

TOOLS = [
    {
        "name": "check_ticket_status",
        "description": "Retrieve current status of a support ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "The support ticket ID (e.g. T-1001)"}
            },
            "required": ["ticket_id"],
        },
    },
    {
        "name": "get_order_details",
        "description": "Get details of a customer order including items, total, and payment status",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID (e.g. ORD-5001)"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "check_refund_eligibility",
        "description": "Check if an order is eligible for refund based on return policy",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID to check eligibility for"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": "Process a refund for an eligible order",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID to refund"},
                "amount": {"type": "number", "description": "The refund amount in USD"},
                "reason": {"type": "string", "description": "Reason for the refund"},
            },
            "required": ["order_id", "amount", "reason"],
        },
    },
    {
        "name": "send_customer_message",
        "description": "Send a message to the customer via email",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID (e.g. C-101)"},
                "subject": {"type": "string", "description": "Email subject line"},
                "message": {"type": "string", "description": "Email body content"},
            },
            "required": ["customer_id", "subject", "message"],
        },
    },
    {
        "name": "close_ticket",
        "description": "Mark ticket as resolved with a resolution summary",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "The ticket ID to close"},
                "resolution_summary": {"type": "string", "description": "Summary of how the issue was resolved"},
            },
            "required": ["ticket_id", "resolution_summary"],
        },
    },
    {
        "name": "get_customer_history",
        "description": "Retrieve past orders and tickets for a customer",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID (e.g. C-101)"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "Search internal documentation for policies and procedures",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for the knowledge base"}
            },
            "required": ["query"],
        },
    },
]

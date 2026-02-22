"""Tool definitions and implementations."""

TOOLS = [
    {
        "name": "check_ticket_status",
        "description": "Retrieve current status of a support ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"}
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "get_order_details",
        "description": "Get details of a customer order including items, total, and payment status",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "check_refund_eligibility",
        "description": "Check if an order is eligible for refund based on policy",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "process_refund",
        "description": "Process a refund for an eligible order",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "reason": {"type": "string"}
            },
            "required": ["order_id", "amount", "reason"]
        }
    },
    {
        "name": "send_customer_message",
        "description": "Send a message to the customer via email",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "subject": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["customer_id", "subject", "message"]
        }
    },
    {
        "name": "close_ticket",
        "description": "Mark ticket as resolved with a resolution summary",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "resolution_summary": {"type": "string"}
            },
            "required": ["ticket_id", "resolution_summary"]
        }
    },
    {
        "name": "get_customer_history",
        "description": "Retrieve past orders and tickets for a customer",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "search_knowledge_base",
        "description": "Search internal documentation for policies and procedures",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]


def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool and return mock response."""

    if name == "check_ticket_status":
        return {
            "ticket_id": arguments["ticket_id"],
            "status": "open",
            "type": "refund_request",
            "customer_id": "C-789",
            "order_id": "ORD-12345",
            "created_at": "2024-01-15T10:30:00Z",
            "description": "Customer requesting refund for order ORD-12345"
        }

    elif name == "get_order_details":
        return {
            "order_id": arguments["order_id"],
            "customer_id": "C-789",
            "status": "delivered",
            "total": 99.99,
            "items": [
                {"name": "Wireless Headphones", "quantity": 1, "price": 99.99}
            ],
            "payment_method": "credit_card",
            "order_date": "2024-01-10T14:20:00Z",
            "delivery_date": "2024-01-13T11:00:00Z"
        }

    elif name == "check_refund_eligibility":
        return {
            "order_id": arguments["order_id"],
            "eligible": True,
            "reason": "Within 30-day return window",
            "max_refund_amount": 99.99,
            "refund_method": "original_payment_method"
        }

    elif name == "process_refund":
        return {
            "success": True,
            "refund_id": "REF-98765",
            "order_id": arguments["order_id"],
            "amount": arguments["amount"],
            "status": "processed",
            "estimated_arrival": "3-5 business days"
        }

    elif name == "send_customer_message":
        return {
            "success": True,
            "message_id": "MSG-11111",
            "customer_id": arguments["customer_id"],
            "subject": arguments["subject"],
            "sent_at": "2024-01-15T10:35:00Z"
        }

    elif name == "close_ticket":
        return {
            "success": True,
            "ticket_id": arguments["ticket_id"],
            "status": "closed",
            "resolution": arguments["resolution_summary"],
            "closed_at": "2024-01-15T10:36:00Z"
        }

    elif name == "get_customer_history":
        return {
            "customer_id": arguments["customer_id"],
            "name": "John Smith",
            "email": "john.smith@email.com",
            "total_orders": 5,
            "total_spent": 450.00,
            "member_since": "2023-06-01",
            "recent_orders": [
                {"id": "ORD-12345", "total": 99.99, "status": "delivered"},
                {"id": "ORD-12300", "total": 150.00, "status": "delivered"}
            ]
        }

    elif name == "search_knowledge_base":
        return {
            "query": arguments["query"],
            "results": [
                {
                    "title": "Refund Policy",
                    "content": "Full refunds available within 30 days of delivery. Refunds processed to original payment method within 3-5 business days."
                },
                {
                    "title": "Refund Process",
                    "content": "1. Verify order eligibility 2. Process refund 3. Notify customer 4. Close ticket"
                }
            ]
        }

    return {"error": f"Unknown tool: {name}"}

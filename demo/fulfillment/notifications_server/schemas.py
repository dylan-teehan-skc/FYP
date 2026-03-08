"""Tool schema definitions for /tools/list endpoint."""

TOOLS = [
    {
        "name": "get_notification_preferences",
        "description": (
            "Look up a customer's notification preferences."
            " Returns their email, phone number, preferred"
            " channel (email/sms/both), and opted_out status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID (e.g. C-301)",
                },
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "send_notification",
        "description": (
            "Send a notification to a customer for a given order."
            " Validates that the customer has not opted out and"
            " that the requested channel is available. Creates a"
            " notification record and returns the sent details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID (e.g. C-301)",
                },
                "order_id": {
                    "type": "string",
                    "description": "The order ID (e.g. ORD-201)",
                },
                "channel": {
                    "type": "string",
                    "description": "Delivery channel: email or sms",
                },
                "template": {
                    "type": "string",
                    "description": (
                        "Message template to use:"
                        " order_confirmed, shipped,"
                        " return_approved, or payment_failed"
                    ),
                },
            },
            "required": ["customer_id", "order_id", "channel", "template"],
        },
    },
    {
        "name": "get_notification_history",
        "description": (
            "Retrieve all notifications sent for a given order."
            " Returns a list of notification records including"
            " channel, template, and notification ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID (e.g. ORD-201)",
                },
            },
            "required": ["order_id"],
        },
    },
]

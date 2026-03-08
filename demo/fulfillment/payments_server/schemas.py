"""Tool schema definitions for /tools/list endpoint."""

TOOLS = [
    {
        "name": "get_payment_methods",
        "description": (
            "Get all payment methods on file for a customer."
            " Returns payment_id, method_type (credit_card,"
            " debit_card, or wallet), last_four digits, whether"
            " it is the default method, and balance for wallets."
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
        "name": "charge_payment",
        "description": (
            "Charge a payment method for an order. For wallet"
            " methods, validates that the balance is sufficient"
            " before charging. Returns a transaction_id and the"
            " resulting status ('completed' or 'failed')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID being paid for",
                },
                "payment_id": {
                    "type": "string",
                    "description": (
                        "The payment method ID to charge"
                        " (from get_payment_methods)"
                    ),
                },
                "amount": {
                    "type": "number",
                    "description": "The amount to charge in USD",
                },
            },
            "required": ["order_id", "payment_id", "amount"],
        },
    },
    {
        "name": "refund_payment",
        "description": (
            "Refund a completed payment transaction. Sets the"
            " transaction status to 'refunded'. For wallet"
            " payments, restores the balance. Only completed"
            " transactions can be refunded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": (
                        "The transaction ID to refund"
                        " (e.g. TXN-abc12345)"
                    ),
                },
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_payment_status",
        "description": (
            "Look up the details of a payment transaction by"
            " transaction ID. Returns transaction_id, order_id,"
            " payment_id, amount, status, and created_at."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": (
                        "The transaction ID to look up"
                        " (e.g. TXN-abc12345)"
                    ),
                },
            },
            "required": ["transaction_id"],
        },
    },
]

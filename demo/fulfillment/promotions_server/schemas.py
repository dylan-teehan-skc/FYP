"""Tool schema definitions for /tools/list endpoint."""

TOOLS = [
    {
        "name": "get_active_promotions",
        "description": (
            "Get all active promotions for a product. Returns"
            " promotion IDs, types (percentage/fixed/bundle),"
            " discount values, minimum quantity requirements,"
            " required loyalty tiers, and usage limits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID (e.g. P-101)",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "validate_promotion",
        "description": (
            "Check if a promotion can be applied to a specific"
            " order. Validates tier eligibility, quantity"
            " requirements, and usage limits. Returns whether"
            " the promotion is valid and the discount amount."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "promotion_id": {
                    "type": "string",
                    "description": (
                        "The promotion ID to validate"
                        " (e.g. PROMO-1)"
                    ),
                },
                "order_id": {
                    "type": "string",
                    "description": "The order ID (e.g. ORD-201)",
                },
            },
            "required": ["promotion_id", "order_id"],
        },
    },
    {
        "name": "apply_promotion",
        "description": (
            "Apply a validated promotion to an order. Records"
            " the usage so one-time promotions cannot be reused."
            " Must validate the promotion first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID (e.g. ORD-201)",
                },
                "promotion_id": {
                    "type": "string",
                    "description": (
                        "The promotion ID to apply"
                        " (e.g. PROMO-1)"
                    ),
                },
            },
            "required": ["order_id", "promotion_id"],
        },
    },
    {
        "name": "get_promotion_history",
        "description": (
            "Get all promotions previously used by a customer."
            " Useful for checking if a one-time promotion has"
            " already been redeemed."
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
]

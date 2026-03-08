"""Tool schema definitions for /tools/list endpoint."""

TOOLS = [
    {
        "name": "reserve_inventory",
        "description": (
            "Reserve stock for an order at a specific warehouse."
            " Reduces available quantity and returns a"
            " reservation ID. Fails if insufficient stock."
            " Use cancel_reservation if the order falls through."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "warehouse_id": {
                    "type": "string",
                    "description": "The warehouse ID (e.g. WH-1)",
                },
                "product_id": {
                    "type": "string",
                    "description": "The product ID (e.g. P-101)",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of units to reserve",
                },
            },
            "required": ["warehouse_id", "product_id", "quantity"],
        },
    },
    {
        "name": "cancel_reservation",
        "description": (
            "Cancel an active inventory reservation and restore"
            " the stock. Use this when payment fails or the"
            " order is blocked by risk assessment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reservation_id": {
                    "type": "string",
                    "description": (
                        "The reservation ID to cancel"
                        " (e.g. RES-abc12345)"
                    ),
                },
            },
            "required": ["reservation_id"],
        },
    },
    {
        "name": "get_reservation",
        "description": (
            "Look up an inventory reservation by ID. Returns"
            " warehouse, product, quantity, status (active/"
            " cancelled/fulfilled), and creation time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reservation_id": {
                    "type": "string",
                    "description": (
                        "The reservation ID to look up"
                        " (e.g. RES-abc12345)"
                    ),
                },
            },
            "required": ["reservation_id"],
        },
    },
    {
        "name": "check_restock_eta",
        "description": (
            "Check when out-of-stock products will be restocked"
            " at a specific warehouse. Returns expected restock"
            " date and quantity if scheduled, or indicates no"
            " restock is planned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "warehouse_id": {
                    "type": "string",
                    "description": "The warehouse ID (e.g. WH-1)",
                },
                "product_id": {
                    "type": "string",
                    "description": "The product ID (e.g. P-103)",
                },
            },
            "required": ["warehouse_id", "product_id"],
        },
    },
]

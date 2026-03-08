"""Tool schema definitions for /tools/list endpoint."""

TOOLS = [
    {
        "name": "get_order",
        "description": (
            "Look up an order by ID. Returns the customer_id,"
            " product_id, quantity, status, and order_date."
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
    {
        "name": "get_product",
        "description": (
            "Look up a product by ID. Returns the name, unit"
            " price, weight in kg, and return window in days."
            " Does NOT include warehouse info — use"
            " list_warehouses to find where it is stocked."
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
        "name": "get_customer",
        "description": (
            "Look up a customer by ID. Returns their name,"
            " shipping region, and loyalty tier"
            " (standard/gold/vip)."
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
        "name": "list_warehouses",
        "description": (
            "List all warehouses that stock a given product."
            " Returns warehouse ID, region, and available"
            " quantity for each location. Use this to find"
            " which warehouses to check for shipping."
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
        "name": "check_inventory",
        "description": (
            "Check if a product is in stock at a specific"
            " warehouse. Returns availability and quantity."
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
            },
            "required": ["warehouse_id", "product_id"],
        },
    },
    {
        "name": "get_shipping_rate",
        "description": (
            "Calculate shipping cost and delivery time between"
            " two regions for a given weight. Returns the"
            " shipping cost and estimated delivery days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_region": {
                    "type": "string",
                    "description": (
                        "Origin region of the warehouse"
                        " (east/west/central)"
                    ),
                },
                "to_region": {
                    "type": "string",
                    "description": (
                        "Destination region of the customer"
                        " (east/west/central)"
                    ),
                },
                "total_weight_kg": {
                    "type": "number",
                    "description": (
                        "Total shipment weight in kg"
                        " (product weight_kg * quantity)"
                    ),
                },
            },
            "required": ["from_region", "to_region", "total_weight_kg"],
        },
    },
    {
        "name": "submit_fulfilment",
        "description": (
            "Submit a fulfilment for an order. Requires the"
            " computed subtotal, shipping cost, discount"
            " percentage, final total, and delivery days."
            " Only works for orders with status 'pending'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to fulfil",
                },
                "subtotal": {
                    "type": "number",
                    "description": (
                        "Product price * quantity before discount"
                    ),
                },
                "shipping_cost": {
                    "type": "number",
                    "description": "Calculated shipping cost",
                },
                "discount_pct": {
                    "type": "number",
                    "description": (
                        "Loyalty discount percentage for the customer"
                    ),
                },
                "promotion_discount": {
                    "type": "number",
                    "description": (
                        "Fixed promotion discount amount"
                        " to subtract (0 if no promotion)"
                    ),
                },
                "total": {
                    "type": "number",
                    "description": (
                        "Final total:"
                        " (subtotal * (1 - discount_pct/100))"
                        " - promotion_discount"
                        " + shipping_cost"
                    ),
                },
                "delivery_days": {
                    "type": "integer",
                    "description": (
                        "Estimated delivery days from shipping rate"
                    ),
                },
            },
            "required": [
                "order_id",
                "subtotal",
                "shipping_cost",
                "discount_pct",
                "total",
                "delivery_days",
            ],
        },
    },
    {
        "name": "get_loyalty_discount",
        "description": (
            "Look up the loyalty discount percentage for a"
            " customer based on their tier."
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
        "name": "mark_backordered",
        "description": (
            "Mark an order as backordered when the product is"
            " out of stock at all warehouses. Use this instead"
            " of submit_fulfilment when inventory is"
            " unavailable everywhere."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": (
                        "The order ID to mark as backordered"
                    ),
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "check_return_eligibility",
        "description": (
            "Check if an order is eligible for return. Returns"
            " eligibility status, reason, and refund amount."
            " Orders must be fulfilled and within the product's"
            " return window. Backordered orders are always"
            " eligible for cancellation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": (
                        "The order ID to check return eligibility"
                    ),
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "process_return",
        "description": (
            "Process a return for an eligible order. Changes"
            " the order status to 'returned' and records the"
            " refund. Check return eligibility first before"
            " calling this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to return",
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Reason for the return"
                        " (e.g. 'defective', 'wrong item',"
                        " 'customer changed mind')"
                    ),
                },
            },
            "required": ["order_id", "reason"],
        },
    },
    {
        "name": "get_order_history",
        "description": (
            "Get all orders for a customer. Returns a list of"
            " orders with their IDs, products, quantities,"
            " statuses, totals, and dates. Useful for looking"
            " up past orders for returns or loyalty context."
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

"""Tool implementations for the order fulfillment MCP server."""

from __future__ import annotations

from mcp_server import database as db

DISCOUNT_BY_TIER = {"standard": 0.0, "gold": 0.05, "vip": 0.10}


def get_order(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}
    row = db.get_order(order_id)
    if not row:
        return {"error": f"Order {order_id} not found"}
    result = {
        "order_id": row["order_id"],
        "customer_id": row["customer_id"],
        "product_id": row["product_id"],
        "quantity": row["quantity"],
        "status": row["status"],
    }
    if row["total"] is not None:
        result["total"] = row["total"]
    if row["delivery_days"] is not None:
        result["delivery_days"] = row["delivery_days"]
    if row["order_date"] is not None:
        result["order_date"] = row["order_date"]
    return result


def get_product(arguments: dict) -> dict:
    product_id = arguments.get("product_id")
    if not product_id:
        return {"error": "product_id is required"}
    row = db.get_product(product_id)
    if not row:
        return {"error": f"Product {product_id} not found"}
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "price": row["price"],
        "weight_kg": row["weight_kg"],
        "return_window_days": row["return_window_days"],
    }


def get_customer(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}
    row = db.get_customer(customer_id)
    if not row:
        return {"error": f"Customer {customer_id} not found"}
    return {
        "customer_id": row["customer_id"],
        "name": row["name"],
        "region": row["region"],
        "loyalty_tier": row["loyalty_tier"],
    }


def list_warehouses(arguments: dict) -> dict:
    product_id = arguments.get("product_id")
    if not product_id:
        return {"error": "product_id is required"}
    rows = db.list_warehouses(product_id)
    if not rows:
        return {"error": f"No warehouses stock product {product_id}"}
    return {
        "product_id": product_id,
        "warehouses": [
            {
                "warehouse_id": r["warehouse_id"],
                "region": r["region"],
                "quantity_available": r["quantity_available"],
            }
            for r in rows
        ],
    }


def check_inventory(arguments: dict) -> dict:
    warehouse_id = arguments.get("warehouse_id")
    product_id = arguments.get("product_id")
    if not warehouse_id or not product_id:
        return {"error": "warehouse_id and product_id are required"}
    row = db.check_inventory(warehouse_id, product_id)
    if not row:
        return {
            "error": f"No inventory record for {product_id}"
                     f" at {warehouse_id}",
        }
    available = row["quantity_available"] > 0
    return {
        "warehouse_id": warehouse_id,
        "product_id": product_id,
        "available": available,
        "quantity_available": row["quantity_available"],
    }


def get_shipping_rate(arguments: dict) -> dict:
    from_region = arguments.get("from_region")
    to_region = arguments.get("to_region")
    total_weight_kg = arguments.get("total_weight_kg")
    if not from_region or not to_region or total_weight_kg is None:
        return {
            "error": "from_region, to_region, and"
                     " total_weight_kg are required",
        }
    total_weight_kg = float(total_weight_kg)
    row = db.get_shipping_rate(from_region, to_region)
    if not row:
        return {
            "error": f"No shipping rate from {from_region}"
                     f" to {to_region}",
        }
    cost = round(row["base_fee"] + row["rate_per_kg"] * total_weight_kg, 2)
    return {
        "from_region": from_region,
        "to_region": to_region,
        "shipping_cost": cost,
        "delivery_days": row["delivery_days"],
    }


def submit_fulfilment(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    subtotal = arguments.get("subtotal")
    shipping_cost = arguments.get("shipping_cost")
    discount_pct = arguments.get("discount_pct") or 0
    promotion_discount = arguments.get("promotion_discount") or 0
    total = arguments.get("total")
    delivery_days = arguments.get("delivery_days")

    if not order_id or total is None or delivery_days is None:
        return {"error": "order_id, total, and delivery_days are required"}

    order = db.get_order(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    if order["status"] != "pending":
        return {"error": f"Order {order_id} is already {order['status']}"}

    customer = db.get_customer(order["customer_id"])
    if customer:
        expected_pct = DISCOUNT_BY_TIER.get(
            customer["loyalty_tier"], 0.0,
        ) * 100
        if abs(float(discount_pct) - expected_pct) > 0.01:
            return {
                "error": "Invalid discount percentage",
            }

    if subtotal is not None and shipping_cost is not None:
        expected = round(
            float(subtotal) * (1 - float(discount_pct) / 100)
            - float(promotion_discount)
            + float(shipping_cost),
            2,
        )
        if abs(float(total) - expected) > 0.02:
            return {
                "error": "Total does not match expected calculation",
            }

    db.submit_fulfilment(order_id, float(total), int(delivery_days))
    return {
        "order_id": order_id,
        "status": "fulfilled",
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "discount_pct": discount_pct,
        "promotion_discount": promotion_discount,
        "total": total,
        "delivery_days": delivery_days,
    }


def get_loyalty_discount(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}
    row = db.get_customer(customer_id)
    if not row:
        return {"error": f"Customer {customer_id} not found"}
    discount = DISCOUNT_BY_TIER.get(row["loyalty_tier"], 0.0) * 100
    return {
        "customer_id": customer_id,
        "loyalty_tier": row["loyalty_tier"],
        "discount_pct": discount,
    }


def mark_backordered(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}
    order = db.get_order(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}
    if order["status"] != "pending":
        return {"error": f"Order {order_id} is already {order['status']}"}
    db.mark_backordered(order_id)
    return {"order_id": order_id, "status": "backordered"}


def check_return_eligibility(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}
    return db.check_return_eligibility(order_id)


def process_return(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    reason = arguments.get("reason", "customer requested return")
    if not order_id:
        return {"error": "order_id is required"}

    eligibility = db.check_return_eligibility(order_id)
    if not eligibility.get("eligible"):
        return {
            "error": f"Return not eligible: {eligibility.get('reason')}",
        }

    result = db.process_return(order_id, reason)
    if not result:
        return {"error": f"Order {order_id} not found"}
    return {
        "return_id": result["return_id"],
        "order_id": order_id,
        "status": "completed",
        "refund_amount": result["refund_amount"],
    }


def get_order_history(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}
    rows = db.get_order_history(customer_id)
    if not rows:
        return {"customer_id": customer_id, "orders": []}
    return {
        "customer_id": customer_id,
        "orders": [
            {
                "order_id": r["order_id"],
                "product_id": r["product_id"],
                "quantity": r["quantity"],
                "status": r["status"],
                "total": r["total"],
                "order_date": r["order_date"],
            }
            for r in rows
        ],
    }


DISPATCH: dict[str, callable] = {
    "get_order": get_order,
    "get_product": get_product,
    "get_customer": get_customer,
    "list_warehouses": list_warehouses,
    "check_inventory": check_inventory,
    "get_shipping_rate": get_shipping_rate,
    "submit_fulfilment": submit_fulfilment,
    "get_loyalty_discount": get_loyalty_discount,
    "mark_backordered": mark_backordered,
    "check_return_eligibility": check_return_eligibility,
    "process_return": process_return,
    "get_order_history": get_order_history,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments)

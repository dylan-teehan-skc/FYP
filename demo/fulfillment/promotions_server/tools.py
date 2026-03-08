"""Tool implementations for the promotions MCP server."""

from __future__ import annotations

import uuid

from mcp_server import database as db

TIER_RANK = {"standard": 0, "gold": 1, "vip": 2}


def get_active_promotions(arguments: dict) -> dict:
    product_id = arguments.get("product_id")
    if not product_id:
        return {"error": "product_id is required"}
    rows = db.get_active_promotions(product_id)
    if not rows:
        return {"product_id": product_id, "promotions": []}
    return {
        "product_id": product_id,
        "promotions": [
            {
                "promotion_id": r["promotion_id"],
                "promo_type": r["promo_type"],
                "discount_value": r["discount_value"],
                "min_quantity": r["min_quantity"],
                "required_tier": r["required_tier"],
                "max_uses_per_customer": r["max_uses_per_customer"],
            }
            for r in rows
        ],
    }


def validate_promotion(arguments: dict) -> dict:
    promotion_id = arguments.get("promotion_id")
    order_id = arguments.get("order_id")
    if not promotion_id or not order_id:
        return {"error": "promotion_id and order_id are required"}

    promo = db.get_promotion(promotion_id)
    if not promo:
        return {"error": f"Promotion {promotion_id} not found"}
    if not promo["active"]:
        return {"valid": False, "reason": "Promotion is inactive"}

    order = db.get_order(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}

    customer = db.get_customer(order["customer_id"])
    if not customer:
        return {"error": f"Customer {order['customer_id']} not found"}

    if promo["required_tier"]:
        customer_rank = TIER_RANK.get(customer["loyalty_tier"], 0)
        required_rank = TIER_RANK.get(promo["required_tier"], 0)
        if customer_rank < required_rank:
            return {
                "valid": False,
                "reason": "Customer does not meet tier requirements",
            }

    if order["quantity"] < promo["min_quantity"]:
        return {
            "valid": False,
            "reason": "Order does not meet minimum quantity",
        }

    if promo["max_uses_per_customer"] is not None:
        usage = db.get_promotion_usage_for_customer(order["customer_id"])
        uses = sum(1 for u in usage if u["promotion_id"] == promotion_id)
        if uses >= promo["max_uses_per_customer"]:
            return {
                "valid": False,
                "reason": "Promotion usage limit exceeded",
            }

    product = db.get_product(order["product_id"])
    subtotal = product["price"] * order["quantity"] if product else 0
    if promo["promo_type"] == "percentage":
        discount_amount = round(subtotal * promo["discount_value"] / 100, 2)
    else:
        discount_amount = promo["discount_value"]

    return {
        "valid": True,
        "promotion_id": promotion_id,
        "order_id": order_id,
        "discount_amount": discount_amount,
        "promo_type": promo["promo_type"],
    }


def apply_promotion(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    promotion_id = arguments.get("promotion_id")
    if not order_id or not promotion_id:
        return {"error": "order_id and promotion_id are required"}

    validation = validate_promotion(
        {"promotion_id": promotion_id, "order_id": order_id},
    )
    if not validation.get("valid"):
        return {"error": "Promotion cannot be applied"}

    usage_id = f"USAGE-{uuid.uuid4().hex[:8]}"
    order = db.get_order(order_id)
    db.create_promotion_usage(
        usage_id, promotion_id, order["customer_id"], order_id,
    )

    return {
        "usage_id": usage_id,
        "promotion_id": promotion_id,
        "order_id": order_id,
        "discount_amount": validation["discount_amount"],
        "status": "applied",
    }


def get_promotion_history(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}
    rows = db.get_promotion_usage_for_customer(customer_id)
    return {
        "customer_id": customer_id,
        "promotions_used": [
            {
                "usage_id": r["usage_id"],
                "promotion_id": r["promotion_id"],
                "order_id": r["order_id"],
            }
            for r in rows
        ],
    }


DISPATCH: dict[str, callable] = {
    "get_active_promotions": get_active_promotions,
    "validate_promotion": validate_promotion,
    "apply_promotion": apply_promotion,
    "get_promotion_history": get_promotion_history,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments)

"""Tool implementations for the risk and compliance MCP server."""

from __future__ import annotations

import json
import uuid

from mcp_server import database as db


def assess_order_risk(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}

    order = db.get_order(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}

    product = db.get_product(order["product_id"])
    if not product:
        return {"error": f"Product {order['product_id']} not found"}

    customer_id = order["customer_id"]
    estimated_total = product["price"] * order["quantity"]

    risk_score = 0.0
    flags: list[str] = []

    if estimated_total > 200.0:
        risk_score += 0.4
        flags.append("high_value")

    flag = db.get_customer_flag(customer_id)
    if flag:
        risk_score += 0.3
        flags.append("flagged_customer")

    if risk_score >= 0.7:
        decision = "block"
    elif risk_score >= 0.4:
        decision = "review"
    else:
        decision = "approve"

    assessment_id = f"RISK-{uuid.uuid4().hex[:8]}"
    db.create_risk_assessment(
        assessment_id,
        order_id,
        round(risk_score, 2),
        json.dumps(flags),
        decision,
    )

    return {
        "assessment_id": assessment_id,
        "order_id": order_id,
        "risk_score": round(risk_score, 2),
        "flags": flags,
        "decision": decision,
    }


def get_risk_assessment(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}

    row = db.get_risk_assessment(order_id)
    if not row:
        return {"error": f"No risk assessment found for order {order_id}"}

    return {
        "assessment_id": row["assessment_id"],
        "order_id": row["order_id"],
        "risk_score": row["risk_score"],
        "flags": json.loads(row["flags"]) if row["flags"] else [],
        "decision": row["decision"],
    }


def override_risk_decision(arguments: dict) -> dict:
    assessment_id = arguments.get("assessment_id")
    new_decision = arguments.get("new_decision")

    if not assessment_id:
        return {"error": "assessment_id is required"}
    if not new_decision:
        return {"error": "new_decision is required"}
    if new_decision != "approve":
        return {"error": "new_decision must be 'approve'"}

    row = db.get_connection().execute(
        "SELECT * FROM risk_assessments WHERE assessment_id = ?",
        (assessment_id,),
    ).fetchone()

    if not row:
        return {"error": f"Assessment {assessment_id} not found"}

    current_decision = row["decision"]
    if current_decision != "review":
        return {"error": "Override not permitted"}

    db.update_risk_decision(assessment_id, new_decision)

    return {
        "assessment_id": assessment_id,
        "order_id": row["order_id"],
        "previous_decision": current_decision,
        "new_decision": new_decision,
        "status": "overridden",
    }


def flag_customer(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    reason = arguments.get("reason")
    if not customer_id or not reason:
        return {"error": "customer_id and reason are required"}

    customer = db.get_customer(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    from datetime import date

    db.create_customer_flag(customer_id, reason, date.today().isoformat())
    return {
        "customer_id": customer_id,
        "reason": reason,
        "status": "flagged",
    }


def get_compliance_requirements(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    if not order_id:
        return {"error": "order_id is required"}

    order = db.get_order(order_id)
    if not order:
        return {"error": f"Order {order_id} not found"}

    product = db.get_product(order["product_id"])
    if not product:
        return {"error": f"Product {order['product_id']} not found"}

    requirements: list[dict] = []
    estimated_total = product["price"] * order["quantity"]

    if estimated_total > 200.0:
        requirements.append({
            "type": "high_value_review",
            "description": "High-value order requires additional review",
        })

    flag = db.get_customer_flag(order["customer_id"])
    if flag:
        requirements.append({
            "type": "flagged_customer_review",
            "description": "Customer requires additional review",
        })

    return {
        "order_id": order_id,
        "requirements": requirements,
        "total_checks": len(requirements),
    }


DISPATCH: dict[str, callable] = {
    "assess_order_risk": assess_order_risk,
    "get_risk_assessment": get_risk_assessment,
    "override_risk_decision": override_risk_decision,
    "flag_customer": flag_customer,
    "get_compliance_requirements": get_compliance_requirements,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments)

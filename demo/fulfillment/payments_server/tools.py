"""Tool implementations for the payments MCP server."""

from __future__ import annotations

import uuid

from mcp_server import database as db


def get_payment_methods(arguments: dict) -> dict:
    customer_id = arguments.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}
    rows = db.get_payment_methods(customer_id)
    if not rows:
        return {"error": f"No payment methods found for customer {customer_id}"}
    methods = []
    for row in rows:
        method: dict = {
            "payment_id": row["payment_id"],
            "method_type": row["method_type"],
            "last_four": row["last_four"],
            "is_default": bool(row["is_default"]),
        }
        if row["method_type"] == "wallet":
            method["balance"] = row["balance"]
        methods.append(method)
    return {"customer_id": customer_id, "payment_methods": methods}


def charge_payment(arguments: dict) -> dict:
    order_id = arguments.get("order_id")
    payment_id = arguments.get("payment_id")
    amount = arguments.get("amount")

    if not order_id or not payment_id or amount is None:
        return {"error": "order_id, payment_id, and amount are required"}

    amount = float(amount)
    method = db.get_payment_method(payment_id)
    if not method:
        return {"error": f"Payment method {payment_id} not found"}

    transaction_id = f"TXN-{uuid.uuid4().hex[:8]}"

    if method["method_type"] == "wallet":
        if (method["balance"] or 0.0) < amount:
            db.create_payment(transaction_id, order_id, payment_id, amount, "failed")
            return {
                "transaction_id": transaction_id,
                "status": "failed",
                "error": "Payment failed",
            }
        db.deduct_wallet_balance(payment_id, amount)

    db.create_payment(transaction_id, order_id, payment_id, amount, "completed")
    return {
        "transaction_id": transaction_id,
        "order_id": order_id,
        "payment_id": payment_id,
        "amount": amount,
        "status": "completed",
    }


def refund_payment(arguments: dict) -> dict:
    transaction_id = arguments.get("transaction_id")
    if not transaction_id:
        return {"error": "transaction_id is required"}

    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM payments WHERE transaction_id = ?", (transaction_id,)
    ).fetchone()

    if not row:
        return {"error": f"Transaction {transaction_id} not found"}

    txn = dict(row)
    if txn["status"] != "completed":
        return {"error": "Transaction cannot be refunded"}

    db.update_payment_status(transaction_id, "refunded")

    method = db.get_payment_method(txn["payment_id"])
    if method and method["method_type"] == "wallet":
        conn.execute(
            "UPDATE payment_methods SET balance = balance + ? WHERE payment_id = ?",
            (txn["amount"], txn["payment_id"]),
        )
        conn.commit()

    return {
        "transaction_id": transaction_id,
        "order_id": txn["order_id"],
        "amount": txn["amount"],
        "status": "refunded",
    }


def get_payment_status(arguments: dict) -> dict:
    transaction_id = arguments.get("transaction_id")
    if not transaction_id:
        return {"error": "transaction_id is required"}

    row = db.get_connection().execute(
        "SELECT * FROM payments WHERE transaction_id = ?", (transaction_id,)
    ).fetchone()

    if not row:
        return {"error": f"Transaction {transaction_id} not found"}

    txn = dict(row)
    return {
        "transaction_id": txn["transaction_id"],
        "order_id": txn["order_id"],
        "payment_id": txn["payment_id"],
        "amount": txn["amount"],
        "status": txn["status"],
        "created_at": txn["created_at"],
    }


DISPATCH: dict[str, callable] = {
    "get_payment_methods": get_payment_methods,
    "charge_payment": charge_payment,
    "refund_payment": refund_payment,
    "get_payment_status": get_payment_status,
}


def execute_tool(name: str, arguments: dict) -> dict:
    handler = DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(arguments)

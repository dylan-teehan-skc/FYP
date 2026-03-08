"""SQLite database for the order fulfillment MCP tool server."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from pathlib import Path

SEED_SQL = Path(__file__).resolve().parent.parent / "seed.sql"

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(":memory:", check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_db(_conn)
    return _conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SEED_SQL.read_text())
    conn.commit()


def reset_db() -> None:
    conn = get_connection()
    conn.executescript("""
        DROP TABLE IF EXISTS restock_schedule;
        DROP TABLE IF EXISTS reservations;
        DROP TABLE IF EXISTS promotion_usage;
        DROP TABLE IF EXISTS promotions;
        DROP TABLE IF EXISTS customer_flags;
        DROP TABLE IF EXISTS risk_assessments;
        DROP TABLE IF EXISTS risk_rules;
        DROP TABLE IF EXISTS notifications;
        DROP TABLE IF EXISTS notification_preferences;
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS payment_methods;
        DROP TABLE IF EXISTS returns;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS inventory;
        DROP TABLE IF EXISTS shipping_rates;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS warehouses;
    """)
    _init_db(conn)


def get_order(order_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    return dict(row) if row else None


def get_product(product_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    return dict(row) if row else None


def get_customer(customer_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    return dict(row) if row else None


def list_warehouses(product_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT i.warehouse_id, w.region, i.quantity_available "
        "FROM inventory i "
        "JOIN warehouses w ON i.warehouse_id = w.warehouse_id "
        "WHERE i.product_id = ? "
        "ORDER BY i.quantity_available DESC",
        (product_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def check_inventory(warehouse_id: str, product_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM inventory WHERE warehouse_id = ? AND product_id = ?",
        (warehouse_id, product_id),
    ).fetchone()
    return dict(row) if row else None


def get_shipping_rate(from_region: str, to_region: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM shipping_rates WHERE from_region = ? AND to_region = ?",
        (from_region, to_region),
    ).fetchone()
    return dict(row) if row else None


def submit_fulfilment(
    order_id: str,
    total: float,
    delivery_days: int,
    status: str = "fulfilled",
) -> bool:
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = ?, total = ?, delivery_days = ? "
        "WHERE order_id = ?",
        (status, total, delivery_days, order_id),
    )
    conn.commit()
    return True


def mark_backordered(order_id: str) -> bool:
    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = 'backordered' WHERE order_id = ?",
        (order_id,),
    )
    conn.commit()
    return True


def check_return_eligibility(order_id: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"eligible": False, "reason": f"Order {order_id} not found"}

    if order["status"] == "backordered":
        return {
            "eligible": True,
            "reason": "Backordered orders can be cancelled at any time",
            "refund_amount": 0.0,
        }

    if order["status"] != "fulfilled":
        return {
            "eligible": False,
            "reason": f"Order {order_id} has status '{order['status']}'"
                      " and cannot be returned",
        }

    product = get_product(order["product_id"])
    if not product:
        return {"eligible": False, "reason": "Product not found"}

    order_date = order.get("order_date")
    if not order_date:
        return {"eligible": False, "reason": "Order date unknown"}

    window = product["return_window_days"]
    order_dt = date.fromisoformat(order_date)
    days_since = (date.today() - order_dt).days

    if days_since > window:
        return {
            "eligible": False,
            "reason": (
                f"Return window expired: {days_since} days since purchase,"
                f" {window}-day return policy"
            ),
        }

    return {
        "eligible": True,
        "reason": (
            f"Within {window}-day return window"
            f" ({days_since} days since purchase)"
        ),
        "refund_amount": order["total"],
    }


def process_return(order_id: str, reason: str) -> dict | None:
    conn = get_connection()
    order = get_order(order_id)
    if not order:
        return None

    refund = order["total"] if order["total"] else 0.0
    return_id = f"RET-{uuid.uuid4().hex[:8]}"

    conn.execute(
        "INSERT INTO returns (return_id, order_id, status, refund_amount, "
        "reason) VALUES (?, ?, 'completed', ?, ?)",
        (return_id, order_id, refund, reason),
    )
    conn.execute(
        "UPDATE orders SET status = 'returned' WHERE order_id = ?",
        (order_id,),
    )
    conn.commit()
    return {
        "return_id": return_id,
        "order_id": order_id,
        "refund_amount": refund,
    }


def get_return_by_order(order_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM returns WHERE order_id = ?", (order_id,)
    ).fetchone()
    return dict(row) if row else None


# --- Payments ---

def get_payment_methods(customer_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM payment_methods WHERE customer_id = ? ORDER BY is_default DESC",
        (customer_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_payment_method(payment_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM payment_methods WHERE payment_id = ?", (payment_id,),
    ).fetchone()
    return dict(row) if row else None


def create_payment(
    transaction_id: str,
    order_id: str,
    payment_id: str,
    amount: float,
    status: str,
) -> bool:
    conn = get_connection()
    conn.execute(
        "INSERT INTO payments (transaction_id, order_id, payment_id, amount, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (transaction_id, order_id, payment_id, amount, status),
    )
    conn.commit()
    return True


def update_payment_status(transaction_id: str, status: str) -> bool:
    conn = get_connection()
    conn.execute(
        "UPDATE payments SET status = ? WHERE transaction_id = ?",
        (status, transaction_id),
    )
    conn.commit()
    return True


def deduct_wallet_balance(payment_id: str, amount: float) -> bool:
    conn = get_connection()
    conn.execute(
        "UPDATE payment_methods SET balance = balance - ? WHERE payment_id = ?",
        (amount, payment_id),
    )
    conn.commit()
    return True


def get_payments_for_order(order_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM payments WHERE order_id = ?", (order_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# --- Notifications ---

def get_notification_preferences(customer_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM notification_preferences WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return dict(row) if row else None


def create_notification(
    notification_id: str,
    customer_id: str,
    order_id: str,
    channel: str,
    template: str,
) -> bool:
    conn = get_connection()
    conn.execute(
        "INSERT INTO notifications (notification_id, customer_id, order_id, channel, template) "
        "VALUES (?, ?, ?, ?, ?)",
        (notification_id, customer_id, order_id, channel, template),
    )
    conn.commit()
    return True


def get_notifications_for_order(order_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM notifications WHERE order_id = ?", (order_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# --- Risk ---

def get_risk_rules() -> list[dict]:
    rows = get_connection().execute("SELECT * FROM risk_rules").fetchall()
    return [dict(row) for row in rows]


def create_risk_assessment(
    assessment_id: str,
    order_id: str,
    risk_score: float,
    flags: str,
    decision: str,
) -> bool:
    conn = get_connection()
    conn.execute(
        "INSERT INTO risk_assessments (assessment_id, order_id, risk_score, flags, decision) "
        "VALUES (?, ?, ?, ?, ?)",
        (assessment_id, order_id, risk_score, flags, decision),
    )
    conn.commit()
    return True


def get_risk_assessment(order_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM risk_assessments WHERE order_id = ?", (order_id,),
    ).fetchone()
    return dict(row) if row else None


def update_risk_decision(assessment_id: str, decision: str) -> bool:
    conn = get_connection()
    conn.execute(
        "UPDATE risk_assessments SET decision = ? WHERE assessment_id = ?",
        (decision, assessment_id),
    )
    conn.commit()
    return True


# --- Customer flags ---

def get_customer_flag(customer_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM customer_flags WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return dict(row) if row else None


def create_customer_flag(
    customer_id: str, reason: str, flagged_at: str,
) -> bool:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO customer_flags (customer_id, reason, flagged_at) "
        "VALUES (?, ?, ?)",
        (customer_id, reason, flagged_at),
    )
    conn.commit()
    return True


# --- Promotions ---

def get_active_promotions(product_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM promotions WHERE product_id = ? AND active = 1",
        (product_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_promotion(promotion_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM promotions WHERE promotion_id = ?",
        (promotion_id,),
    ).fetchone()
    return dict(row) if row else None


def get_promotion_usage_for_customer(customer_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM promotion_usage WHERE customer_id = ?",
        (customer_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_promotion_usage(
    usage_id: str, promotion_id: str, customer_id: str, order_id: str,
) -> bool:
    conn = get_connection()
    conn.execute(
        "INSERT INTO promotion_usage (usage_id, promotion_id, customer_id, order_id) "
        "VALUES (?, ?, ?, ?)",
        (usage_id, promotion_id, customer_id, order_id),
    )
    conn.commit()
    return True


# --- Inventory reservations ---

def create_reservation(
    reservation_id: str,
    warehouse_id: str,
    product_id: str,
    quantity: int,
) -> bool:
    conn = get_connection()
    inv = check_inventory(warehouse_id, product_id)
    if not inv or inv["quantity_available"] < quantity:
        return False
    conn.execute(
        "INSERT INTO reservations (reservation_id, warehouse_id, product_id, "
        "quantity, status, created_at) VALUES (?, ?, ?, ?, 'active', datetime('now'))",
        (reservation_id, warehouse_id, product_id, quantity),
    )
    conn.execute(
        "UPDATE inventory SET quantity_available = quantity_available - ? "
        "WHERE warehouse_id = ? AND product_id = ?",
        (quantity, warehouse_id, product_id),
    )
    conn.commit()
    return True


def cancel_reservation(reservation_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reservations WHERE reservation_id = ?",
        (reservation_id,),
    ).fetchone()
    if not row:
        return None
    res = dict(row)
    if res["status"] != "active":
        return None
    conn.execute(
        "UPDATE reservations SET status = 'cancelled' WHERE reservation_id = ?",
        (reservation_id,),
    )
    conn.execute(
        "UPDATE inventory SET quantity_available = quantity_available + ? "
        "WHERE warehouse_id = ? AND product_id = ?",
        (res["quantity"], res["warehouse_id"], res["product_id"]),
    )
    conn.commit()
    return res


def get_reservation(reservation_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM reservations WHERE reservation_id = ?",
        (reservation_id,),
    ).fetchone()
    return dict(row) if row else None


def get_restock_eta(warehouse_id: str, product_id: str) -> dict | None:
    row = get_connection().execute(
        "SELECT * FROM restock_schedule WHERE warehouse_id = ? AND product_id = ?",
        (warehouse_id, product_id),
    ).fetchone()
    return dict(row) if row else None


# --- Order history ---

def get_order_history(customer_id: str) -> list[dict]:
    rows = get_connection().execute(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC",
        (customer_id,),
    ).fetchall()
    return [dict(row) for row in rows]

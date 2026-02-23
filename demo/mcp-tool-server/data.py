"""Static mock data for the NovaTech Electronics demo scenario."""

from datetime import UTC, datetime, timedelta


def _days_ago(days: int) -> str:
    dt = datetime.now(UTC) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


CUSTOMERS = {
    "C-101": {
        "customer_id": "C-101",
        "name": "Alice Chen",
        "email": "alice.chen@email.com",
        "tier": "standard",
    },
    "C-102": {
        "customer_id": "C-102",
        "name": "Bob Martinez",
        "email": "bob.martinez@email.com",
        "tier": "standard",
    },
    "C-103": {
        "customer_id": "C-103",
        "name": "Carol Johnson",
        "email": "carol.johnson@email.com",
        "tier": "standard",
    },
    "C-104": {
        "customer_id": "C-104",
        "name": "David Kim",
        "email": "david.kim@email.com",
        "tier": "vip",
    },
    "C-105": {
        "customer_id": "C-105",
        "name": "Emma Wilson",
        "email": "emma.wilson@email.com",
        "tier": "standard",
    },
}

INITIAL_ORDERS = {
    "ORD-5001": {
        "order_id": "ORD-5001",
        "customer_id": "C-101",
        "product": "Wireless Earbuds Pro",
        "amount": 79.99,
        "status": "delivered",
        "days_since_delivery": 9,
        "payment_method": "credit_card",
    },
    "ORD-5002": {
        "order_id": "ORD-5002",
        "customer_id": "C-102",
        "product": "USB-C Hub Dock",
        "amount": 249.99,
        "status": "shipped",
        "days_since_delivery": None,
        "payment_method": "paypal",
    },
    "ORD-5003": {
        "order_id": "ORD-5003",
        "customer_id": "C-103",
        "product": "Bluetooth Speaker",
        "amount": 159.00,
        "status": "delivered",
        "days_since_delivery": 45,
        "payment_method": "credit_card",
    },
    "ORD-5004": {
        "order_id": "ORD-5004",
        "customer_id": "C-104",
        "product": "Noise-Cancelling Headphones",
        "amount": 349.99,
        "status": "delivered",
        "days_since_delivery": 4,
        "payment_method": "credit_card",
    },
    "ORD-5005": {
        "order_id": "ORD-5005",
        "customer_id": "C-105",
        "product": "Wireless Headphones",
        "amount": 99.99,
        "status": "delivered",
        "days_since_delivery": 7,
        "payment_method": "debit_card",
    },
}

INITIAL_TICKETS = {
    "T-1001": {
        "ticket_id": "T-1001",
        "customer_id": "C-101",
        "order_id": "ORD-5001",
        "type": "refund_request",
        "status": "open",
        "subject": "Request refund for Wireless Earbuds Pro",
        "created_at": _days_ago(1),
    },
    "T-1002": {
        "ticket_id": "T-1002",
        "customer_id": "C-102",
        "order_id": "ORD-5002",
        "type": "order_inquiry",
        "status": "open",
        "subject": "Where is my USB-C Hub Dock order?",
        "created_at": _days_ago(1),
    },
    "T-1003": {
        "ticket_id": "T-1003",
        "customer_id": "C-103",
        "order_id": "ORD-5003",
        "type": "refund_request",
        "status": "open",
        "subject": "Want to return Bluetooth Speaker",
        "created_at": _days_ago(1),
    },
    "T-1004": {
        "ticket_id": "T-1004",
        "customer_id": "C-104",
        "order_id": "ORD-5004",
        "type": "complaint",
        "status": "open",
        "subject": "Noise-cancelling feature not working properly",
        "created_at": _days_ago(1),
    },
    "T-1005": {
        "ticket_id": "T-1005",
        "customer_id": "C-105",
        "order_id": "ORD-5005",
        "type": "product_support",
        "status": "open",
        "subject": "Cannot pair Wireless Headphones with phone",
        "created_at": _days_ago(1),
    },
}

REFUND_WINDOW_DAYS = 30

KNOWLEDGE_BASE = {
    "KB-001": {
        "article_id": "KB-001",
        "title": "Refund Policy",
        "content": (
            "NovaTech offers a 30-day return window from the date of delivery. "
            "Refunds are processed to the original payment method within 3-5 business days. "
            "Items must be in original packaging. Digital products are non-refundable. "
            "To request a refund, contact support with your order number."
        ),
        "keywords": ["refund", "return", "policy", "money back", "30 day", "return window"],
    },
    "KB-002": {
        "article_id": "KB-002",
        "title": "VIP Customer Handling",
        "content": (
            "VIP customers receive priority support with dedicated agents. "
            "They are eligible for complimentary express shipping on replacements. "
            "VIP complaints should be escalated immediately and resolved within 24 hours. "
            "Offer goodwill gestures such as discount codes or free accessories when appropriate."
        ),
        "keywords": ["vip", "priority", "premium", "escalate", "dedicated", "complimentary"],
    },
    "KB-003": {
        "article_id": "KB-003",
        "title": "Wireless Pairing Guide",
        "content": (
            "To pair wireless headphones or earbuds: "
            "1. Turn on Bluetooth on your device. "
            "2. Press and hold the power button on the headphones for "
            "5 seconds until the LED flashes blue. "
            "3. Select the device name from the Bluetooth menu on your phone. "
            "4. If pairing fails, reset by holding power + volume down for 10 seconds. "
            "5. Ensure no other devices are connected to the headphones."
        ),
        "keywords": [
            "pair", "pairing", "bluetooth", "connect",
            "wireless", "headphones", "earbuds",
        ],
    },
    "KB-004": {
        "article_id": "KB-004",
        "title": "Warranty Information",
        "content": (
            "All NovaTech products come with a 1-year manufacturer warranty. "
            "The warranty covers defects in materials and workmanship under normal use. "
            "Physical damage, water damage, and unauthorised modifications are not covered. "
            "To file a warranty claim, provide your order number and a description of the issue."
        ),
        "keywords": ["warranty", "defect", "manufacturer", "coverage", "claim", "repair"],
    },
    "KB-005": {
        "article_id": "KB-005",
        "title": "Shipping and Delivery",
        "content": (
            "Standard shipping takes 3-5 business days. "
            "Express shipping is available for an additional fee. "
            "All orders include tracking. You will receive a tracking number "
            "via email once your order ships. "
            "If your order has not arrived within the expected window, "
            "contact support with your order number."
        ),
        "keywords": ["shipping", "delivery", "tracking", "express", "arrival", "transit"],
    },
}

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
    "C-106": {
        "customer_id": "C-106",
        "name": "Frank Torres",
        "email": "frank.torres@email.com",
        "tier": "gold",
    },
    "C-107": {
        "customer_id": "C-107",
        "name": "Grace Patel",
        "email": "grace.patel@email.com",
        "tier": "standard",
    },
    "C-108": {
        "customer_id": "C-108",
        "name": "Henry Nakamura",
        "email": "henry.nakamura@email.com",
        "tier": "platinum",
    },
    "C-109": {
        "customer_id": "C-109",
        "name": "Ivy Johansson",
        "email": "ivy.johansson@email.com",
        "tier": "standard",
    },
    "C-110": {
        "customer_id": "C-110",
        "name": "Jake Morrison",
        "email": "jake.morrison@email.com",
        "tier": "gold",
    },
    "C-111": {
        "customer_id": "C-111",
        "name": "Karen Liu",
        "email": "karen.liu@email.com",
        "tier": "standard",
    },
    "C-112": {
        "customer_id": "C-112",
        "name": "Leo Santos",
        "email": "leo.santos@email.com",
        "tier": "platinum",
    },
    "C-113": {
        "customer_id": "C-113",
        "name": "Mia Thompson",
        "email": "mia.thompson@email.com",
        "tier": "standard",
    },
    "C-114": {
        "customer_id": "C-114",
        "name": "Noah Andersen",
        "email": "noah.andersen@email.com",
        "tier": "gold",
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
    "ORD-5006": {
        "order_id": "ORD-5006",
        "customer_id": "C-106",
        "product": "Smart Watch Pro",
        "amount": 299.99,
        "status": "delivered",
        "days_since_delivery": 10,
        "payment_method": "credit_card",
    },
    "ORD-5007": {
        "order_id": "ORD-5007",
        "customer_id": "C-107",
        "product": "Portable Charger",
        "amount": 49.99,
        "status": "shipped",
        "days_since_delivery": None,
        "payment_method": "paypal",
    },
    "ORD-5008": {
        "order_id": "ORD-5008",
        "customer_id": "C-108",
        "product": "4K Webcam Ultra",
        "amount": 189.99,
        "status": "delivered",
        "days_since_delivery": 45,
        "payment_method": "credit_card",
    },
    "ORD-5009": {
        "order_id": "ORD-5009",
        "customer_id": "C-109",
        "product": "Wireless Mouse",
        "amount": 39.99,
        "status": "delivered",
        "days_since_delivery": 5,
        "payment_method": "debit_card",
    },
    "ORD-5010": {
        "order_id": "ORD-5010",
        "customer_id": "C-106",
        "product": "Laptop Stand Deluxe",
        "amount": 129.99,
        "status": "processing",
        "days_since_delivery": None,
        "payment_method": "credit_card",
    },
    "ORD-5011": {
        "order_id": "ORD-5011",
        "customer_id": "C-108",
        "product": "Mechanical Keyboard",
        "amount": 179.99,
        "status": "delivered",
        "days_since_delivery": 3,
        "payment_method": "credit_card",
    },
    "ORD-5012": {
        "order_id": "ORD-5012",
        "customer_id": "C-110",
        "product": "Noise-Cancelling Headphones",
        "amount": 349.99,
        "status": "delivered",
        "days_since_delivery": 12,
        "payment_method": "credit_card",
    },
    "ORD-5013": {
        "order_id": "ORD-5013",
        "customer_id": "C-111",
        "product": "Smart Watch Pro",
        "amount": 299.99,
        "status": "delivered",
        "days_since_delivery": 15,
        "payment_method": "paypal",
    },
    "ORD-5014": {
        "order_id": "ORD-5014",
        "customer_id": "C-112",
        "product": "4K Webcam Ultra",
        "amount": 189.99,
        "status": "delivered",
        "days_since_delivery": 8,
        "payment_method": "credit_card",
    },
    "ORD-5015": {
        "order_id": "ORD-5015",
        "customer_id": "C-113",
        "product": "Wireless Earbuds Pro",
        "amount": 79.99,
        "status": "shipped",
        "days_since_delivery": None,
        "payment_method": "debit_card",
    },
    "ORD-5016": {
        "order_id": "ORD-5016",
        "customer_id": "C-114",
        "product": "Bluetooth Speaker",
        "amount": 159.00,
        "status": "delivered",
        "days_since_delivery": 6,
        "payment_method": "credit_card",
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
    "T-1006": {
        "ticket_id": "T-1006",
        "customer_id": "C-106",
        "order_id": "ORD-5006",
        "type": "product_support",
        "status": "open",
        "subject": "Smart Watch not charging after a week",
        "created_at": _days_ago(1),
    },
    "T-1007": {
        "ticket_id": "T-1007",
        "customer_id": "C-107",
        "order_id": "ORD-5007",
        "type": "order_inquiry",
        "status": "open",
        "subject": "Where is my package?",
        "created_at": _days_ago(1),
    },
    "T-1008": {
        "ticket_id": "T-1008",
        "customer_id": "C-108",
        "order_id": "ORD-5008",
        "type": "complaint",
        "status": "open",
        "subject": "Webcam image quality poor, want resolution",
        "created_at": _days_ago(1),
    },
    "T-1009": {
        "ticket_id": "T-1009",
        "customer_id": "C-109",
        "order_id": "ORD-5009",
        "type": "complaint",
        "status": "open",
        "subject": "Received wrong color mouse",
        "created_at": _days_ago(1),
    },
    "T-1010": {
        "ticket_id": "T-1010",
        "customer_id": "C-106",
        "order_id": "ORD-5010",
        "type": "order_inquiry",
        "status": "open",
        "subject": "Cancel my laptop stand order",
        "created_at": _days_ago(1),
    },
    "T-1011": {
        "ticket_id": "T-1011",
        "customer_id": "C-110",
        "order_id": "ORD-5012",
        "type": "refund_request",
        "status": "open",
        "subject": "Want refund for Noise-Cancelling Headphones",
        "created_at": _days_ago(1),
    },
    "T-1012": {
        "ticket_id": "T-1012",
        "customer_id": "C-111",
        "order_id": "ORD-5013",
        "type": "complaint",
        "status": "open",
        "subject": "Smart Watch screen flickering after update",
        "created_at": _days_ago(1),
    },
    "T-1013": {
        "ticket_id": "T-1013",
        "customer_id": "C-112",
        "order_id": "ORD-5014",
        "type": "complaint",
        "status": "open",
        "subject": "Webcam keeps disconnecting during video calls",
        "created_at": _days_ago(1),
    },
    "T-1014": {
        "ticket_id": "T-1014",
        "customer_id": "C-113",
        "order_id": "ORD-5015",
        "type": "order_inquiry",
        "status": "open",
        "subject": "Where are my Wireless Earbuds Pro?",
        "created_at": _days_ago(1),
    },
    "T-1015": {
        "ticket_id": "T-1015",
        "customer_id": "C-114",
        "order_id": "ORD-5016",
        "type": "refund_request",
        "status": "open",
        "subject": "Return request for Bluetooth Speaker",
        "created_at": _days_ago(1),
    },
}

REFUND_WINDOW_DAYS = 30
WARRANTY_DAYS = 365

SHIPPING_INFO = {
    "ORD-5002": {
        "order_id": "ORD-5002",
        "carrier": "FedEx",
        "tracking_number": "FX-9281736450",
        "status": "in_transit",
        "estimated_delivery": _days_ago(-2),
        "last_location": "Distribution Center, Chicago IL",
    },
    "ORD-5007": {
        "order_id": "ORD-5007",
        "carrier": "UPS",
        "tracking_number": "UPS-7463829105",
        "status": "in_transit",
        "estimated_delivery": _days_ago(-1),
        "last_location": "Sorting Facility, Denver CO",
    },
    "ORD-5015": {
        "order_id": "ORD-5015",
        "carrier": "USPS",
        "tracking_number": "USPS-3847562910",
        "status": "in_transit",
        "estimated_delivery": _days_ago(-3),
        "last_location": "Regional Hub, Atlanta GA",
    },
}

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
    "KB-006": {
        "article_id": "KB-006",
        "title": "Warranty Claims Process",
        "content": (
            "To file a warranty claim: 1. Check warranty status using the order ID. "
            "2. Verify the reported issue falls under warranty coverage. "
            "3. If covered, offer repair or replacement at no charge. "
            "4. If the claim is complex or involves a high-value item, "
            "escalate to a supervisor for approval. "
            "5. Gold and Platinum customers receive expedited warranty service."
        ),
        "keywords": [
            "warranty", "claim", "repair", "replacement",
            "coverage", "defect", "escalate",
        ],
    },
    "KB-007": {
        "article_id": "KB-007",
        "title": "Order Cancellation Policy",
        "content": (
            "Orders in 'processing' status can be cancelled immediately with a full refund. "
            "Orders that have already shipped cannot be cancelled — "
            "the customer must wait for delivery and then initiate a return. "
            "To cancel, verify the order status first, then confirm with the customer."
        ),
        "keywords": [
            "cancel", "cancellation", "processing",
            "shipped", "return", "order",
        ],
    },
}

"""Mutable demo state manager with reset support."""

import copy
from datetime import datetime, timezone

from data import INITIAL_ORDERS, INITIAL_TICKETS


class StateManager:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.orders = copy.deepcopy(INITIAL_ORDERS)
        self.tickets = copy.deepcopy(INITIAL_TICKETS)
        self.processed_refunds: dict[str, dict] = {}
        self.sent_messages: list[dict] = []

    def get_order(self, order_id: str) -> dict | None:
        return self.orders.get(order_id)

    def get_ticket(self, ticket_id: str) -> dict | None:
        return self.tickets.get(ticket_id)

    def close_ticket(self, ticket_id: str, resolution_summary: str) -> dict | None:
        ticket = self.tickets.get(ticket_id)
        if ticket is None:
            return None
        ticket["status"] = "closed"
        ticket["resolution_summary"] = resolution_summary
        ticket["closed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return ticket

    def process_refund(self, order_id: str, amount: float, reason: str) -> dict | None:
        order = self.orders.get(order_id)
        if order is None:
            return None
        refund_id = f"REF-{order_id.split('-')[1]}"
        refund = {
            "refund_id": refund_id,
            "order_id": order_id,
            "amount": amount,
            "reason": reason,
            "status": "processed",
            "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.processed_refunds[order_id] = refund
        order["refund_status"] = "refunded"
        return refund

    def is_refund_processed(self, order_id: str) -> bool:
        return order_id in self.processed_refunds

    def record_message(self, customer_id: str, subject: str, message: str) -> dict:
        msg_id = f"MSG-{len(self.sent_messages) + 1:04d}"
        record = {
            "message_id": msg_id,
            "customer_id": customer_id,
            "subject": subject,
            "message": message,
            "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.sent_messages.append(record)
        return record

"""Tests for individual tool handlers."""

from tools import execute_tool
from tools.customer import (
    apply_discount,
    get_customer_history,
    schedule_callback,
    send_customer_message,
)
from tools.knowledge import search_knowledge_base
from tools.order import check_refund_eligibility, get_order_details, process_refund
from tools.shipping import get_shipping_status
from tools.ticket import check_ticket_status, close_ticket, escalate_ticket
from tools.warranty import check_warranty


class TestCheckTicketStatus:
    def test_existing_ticket(self, state):
        result = check_ticket_status({"ticket_id": "T-1001"}, state)
        assert result["ticket_id"] == "T-1001"
        assert result["status"] == "open"
        assert result["type"] == "refund_request"
        assert result["customer_id"] == "C-101"

    def test_missing_ticket(self, state):
        result = check_ticket_status({"ticket_id": "T-9999"}, state)
        assert "error" in result


class TestCloseTicket:
    def test_close_ticket(self, state):
        result = close_ticket(
            {"ticket_id": "T-1001", "resolution_summary": "Refunded"}, state
        )
        assert result["status"] == "closed"
        assert result["resolution_summary"] == "Refunded"
        assert "closed_at" in result

    def test_close_missing_ticket(self, state):
        result = close_ticket(
            {"ticket_id": "T-9999", "resolution_summary": "n/a"}, state
        )
        assert "error" in result

    def test_close_already_closed(self, state):
        close_ticket({"ticket_id": "T-1001", "resolution_summary": "done"}, state)
        result = close_ticket(
            {"ticket_id": "T-1001", "resolution_summary": "again"}, state
        )
        assert "error" in result
        assert "already closed" in result["error"]


class TestGetOrderDetails:
    def test_delivered_order(self, state):
        result = get_order_details({"order_id": "ORD-5001"}, state)
        assert result["order_id"] == "ORD-5001"
        assert result["product"] == "Wireless Earbuds Pro"
        assert result["amount"] == 79.99
        assert result["delivered_at"] is not None

    def test_shipped_order(self, state):
        result = get_order_details({"order_id": "ORD-5002"}, state)
        assert result["status"] == "shipped"
        assert result["delivered_at"] is None

    def test_missing_order(self, state):
        result = get_order_details({"order_id": "ORD-9999"}, state)
        assert "error" in result

    def test_refunded_order_shows_status(self, state):
        state.process_refund("ORD-5001", 79.99, "test")
        result = get_order_details({"order_id": "ORD-5001"}, state)
        assert result["refund_status"] == "refunded"


class TestCheckRefundEligibility:
    def test_eligible_order(self, state):
        result = check_refund_eligibility({"order_id": "ORD-5001"}, state)
        assert result["eligible"] is True
        assert result["max_refund_amount"] == 79.99

    def test_shipped_not_eligible(self, state):
        result = check_refund_eligibility({"order_id": "ORD-5002"}, state)
        assert result["eligible"] is False
        assert "shipped" in result["reason"]

    def test_outside_window(self, state):
        result = check_refund_eligibility({"order_id": "ORD-5003"}, state)
        assert result["eligible"] is False
        assert "45 days" in result["reason"]

    def test_already_refunded(self, state):
        state.process_refund("ORD-5001", 79.99, "test")
        result = check_refund_eligibility({"order_id": "ORD-5001"}, state)
        assert result["eligible"] is False
        assert "already been processed" in result["reason"]

    def test_missing_order(self, state):
        result = check_refund_eligibility({"order_id": "ORD-9999"}, state)
        assert "error" in result


class TestProcessRefund:
    def test_process_refund(self, state):
        result = process_refund(
            {"order_id": "ORD-5001", "amount": 79.99, "reason": "Defective"}, state
        )
        assert result["refund_id"] == "REF-5001"
        assert result["amount"] == 79.99
        assert result["status"] == "processed"

    def test_double_refund_blocked(self, state):
        process_refund(
            {"order_id": "ORD-5001", "amount": 79.99, "reason": "first"}, state
        )
        result = process_refund(
            {"order_id": "ORD-5001", "amount": 79.99, "reason": "second"}, state
        )
        assert "error" in result

    def test_amount_exceeds_total(self, state):
        result = process_refund(
            {"order_id": "ORD-5001", "amount": 999.99, "reason": "test"}, state
        )
        assert "error" in result
        assert "exceeds" in result["error"]

    def test_missing_order(self, state):
        result = process_refund(
            {"order_id": "ORD-9999", "amount": 10.0, "reason": "test"}, state
        )
        assert "error" in result


class TestGetCustomerHistory:
    def test_existing_customer(self, state):
        result = get_customer_history({"customer_id": "C-101"}, state)
        assert result["customer_id"] == "C-101"
        assert result["name"] == "Alice Chen"
        assert len(result["orders"]) >= 1
        assert len(result["tickets"]) >= 1
        assert result["total_spent"] > 0

    def test_vip_customer(self, state):
        result = get_customer_history({"customer_id": "C-104"}, state)
        assert result["tier"] == "vip"

    def test_missing_customer(self, state):
        result = get_customer_history({"customer_id": "C-999"}, state)
        assert "error" in result


class TestSendCustomerMessage:
    def test_send_message(self, state):
        result = send_customer_message(
            {
                "customer_id": "C-101",
                "subject": "Your refund",
                "message": "Refund processed.",
            },
            state,
        )
        assert result["status"] == "sent"
        assert result["sent_to"] == "alice.chen@email.com"
        assert "message_id" in result
        assert "sent_at" in result

    def test_missing_customer(self, state):
        result = send_customer_message(
            {"customer_id": "C-999", "subject": "Hi", "message": "Hello"}, state
        )
        assert "error" in result


class TestSearchKnowledgeBase:
    def test_refund_query(self, state):
        result = search_knowledge_base({"query": "refund policy"}, state)
        assert result["results_count"] >= 1
        titles = [r["title"] for r in result["results"]]
        assert "Refund Policy" in titles

    def test_pairing_query(self, state):
        result = search_knowledge_base({"query": "bluetooth pairing"}, state)
        assert result["results_count"] >= 1
        titles = [r["title"] for r in result["results"]]
        assert "Wireless Pairing Guide" in titles

    def test_empty_query(self, state):
        result = search_knowledge_base({"query": ""}, state)
        assert "error" in result

    def test_no_results(self, state):
        result = search_knowledge_base({"query": "xyznonexistent"}, state)
        assert result["results_count"] == 0


class TestEscalateTicket:
    def test_escalate(self, state):
        result = escalate_ticket(
            {"ticket_id": "T-1001", "reason": "VIP complaint"}, state
        )
        assert result["status"] == "escalated"
        assert result["reason"] == "VIP complaint"
        assert "escalated_at" in result

    def test_escalate_missing(self, state):
        result = escalate_ticket(
            {"ticket_id": "T-9999", "reason": "test"}, state
        )
        assert "error" in result

    def test_escalate_already_escalated(self, state):
        escalate_ticket({"ticket_id": "T-1001", "reason": "first"}, state)
        result = escalate_ticket(
            {"ticket_id": "T-1001", "reason": "second"}, state
        )
        assert "error" in result
        assert "already escalated" in result["error"]


class TestApplyDiscount:
    def test_apply(self, state):
        result = apply_discount(
            {"order_id": "ORD-5001", "discount_percent": 10, "reason": "loyalty"},
            state,
        )
        assert result["status"] == "applied"
        assert result["discount_percent"] == 10
        assert result["new_amount"] == 71.99

    def test_missing_order(self, state):
        result = apply_discount(
            {"order_id": "ORD-9999", "discount_percent": 10}, state
        )
        assert "error" in result

    def test_invalid_percent(self, state):
        result = apply_discount(
            {"order_id": "ORD-5001", "discount_percent": 60}, state
        )
        assert "error" in result
        assert "between 1% and 50%" in result["error"]

    def test_double_discount(self, state):
        apply_discount(
            {"order_id": "ORD-5001", "discount_percent": 10}, state
        )
        result = apply_discount(
            {"order_id": "ORD-5001", "discount_percent": 5}, state
        )
        assert "error" in result
        assert "already applied" in result["error"]


class TestCheckWarranty:
    def test_active_warranty(self, state):
        result = check_warranty({"order_id": "ORD-5001"}, state)
        assert result["warranty_status"] == "active"
        assert result["days_remaining"] > 0

    def test_not_delivered(self, state):
        result = check_warranty({"order_id": "ORD-5007"}, state)
        assert result["warranty_status"] == "not_applicable"

    def test_missing_order(self, state):
        result = check_warranty({"order_id": "ORD-9999"}, state)
        assert "error" in result

    def test_processing_order(self, state):
        result = check_warranty({"order_id": "ORD-5010"}, state)
        assert result["warranty_status"] == "not_applicable"


class TestGetShippingStatus:
    def test_shipped_with_tracking(self, state):
        result = get_shipping_status({"order_id": "ORD-5007"}, state)
        assert result["shipping_status"] == "in_transit"
        assert result["carrier"] == "UPS"
        assert "tracking_number" in result

    def test_delivered_order(self, state):
        result = get_shipping_status({"order_id": "ORD-5001"}, state)
        assert result["shipping_status"] == "delivered"

    def test_processing_order(self, state):
        result = get_shipping_status({"order_id": "ORD-5010"}, state)
        assert result["shipping_status"] == "not_shipped"

    def test_missing_order(self, state):
        result = get_shipping_status({"order_id": "ORD-9999"}, state)
        assert "error" in result


class TestScheduleCallback:
    def test_schedule(self, state):
        result = schedule_callback(
            {"customer_id": "C-101", "topic": "refund follow-up"}, state
        )
        assert result["status"] == "scheduled"
        assert result["customer_name"] == "Alice Chen"
        assert "callback_id" in result

    def test_with_preferred_time(self, state):
        result = schedule_callback(
            {
                "customer_id": "C-101",
                "preferred_time": "tomorrow 2pm",
                "topic": "warranty",
            },
            state,
        )
        assert result["preferred_time"] == "tomorrow 2pm"

    def test_missing_customer(self, state):
        result = schedule_callback(
            {"customer_id": "C-999", "topic": "test"}, state
        )
        assert "error" in result


class TestExecuteToolDispatcher:
    def test_known_tool(self, state):
        result = execute_tool("check_ticket_status", {"ticket_id": "T-1001"}, state)
        assert result["ticket_id"] == "T-1001"

    def test_unknown_tool(self, state):
        result = execute_tool("nonexistent_tool", {}, state)
        assert "error" in result
        assert "Unknown tool" in result["error"]

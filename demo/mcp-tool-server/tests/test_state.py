"""Tests for StateManager."""



class TestStateManagerInit:
    def test_orders_loaded(self, state):
        assert len(state.orders) == 11
        assert "ORD-5001" in state.orders

    def test_tickets_loaded(self, state):
        assert len(state.tickets) == 10
        assert "T-1001" in state.tickets

    def test_no_refunds_initially(self, state):
        assert state.processed_refunds == {}

    def test_no_messages_initially(self, state):
        assert state.sent_messages == []


class TestGetOrder:
    def test_existing_order(self, state):
        order = state.get_order("ORD-5001")
        assert order is not None
        assert order["product"] == "Wireless Earbuds Pro"

    def test_missing_order(self, state):
        assert state.get_order("ORD-9999") is None


class TestGetTicket:
    def test_existing_ticket(self, state):
        ticket = state.get_ticket("T-1001")
        assert ticket is not None
        assert ticket["type"] == "refund_request"

    def test_missing_ticket(self, state):
        assert state.get_ticket("T-9999") is None


class TestCloseTicket:
    def test_close_open_ticket(self, state):
        result = state.close_ticket("T-1001", "Resolved via refund")
        assert result is not None
        assert result["status"] == "closed"
        assert result["resolution_summary"] == "Resolved via refund"
        assert "closed_at" in result

    def test_close_missing_ticket(self, state):
        assert state.close_ticket("T-9999", "n/a") is None

    def test_ticket_stays_closed(self, state):
        state.close_ticket("T-1001", "Done")
        ticket = state.get_ticket("T-1001")
        assert ticket["status"] == "closed"


class TestProcessRefund:
    def test_process_refund(self, state):
        refund = state.process_refund("ORD-5001", 79.99, "Customer request")
        assert refund is not None
        assert refund["refund_id"] == "REF-5001"
        assert refund["amount"] == 79.99
        assert refund["status"] == "processed"
        assert "processed_at" in refund

    def test_order_marked_refunded(self, state):
        state.process_refund("ORD-5001", 79.99, "test")
        assert state.orders["ORD-5001"]["refund_status"] == "refunded"

    def test_missing_order(self, state):
        assert state.process_refund("ORD-9999", 10.0, "test") is None

    def test_is_refund_processed(self, state):
        assert state.is_refund_processed("ORD-5001") is False
        state.process_refund("ORD-5001", 79.99, "test")
        assert state.is_refund_processed("ORD-5001") is True


class TestRecordMessage:
    def test_record_message(self, state):
        msg = state.record_message("C-101", "Hi", "Hello there")
        assert msg["message_id"] == "MSG-0001"
        assert msg["customer_id"] == "C-101"
        assert msg["subject"] == "Hi"
        assert len(state.sent_messages) == 1

    def test_incremental_ids(self, state):
        state.record_message("C-101", "a", "b")
        msg2 = state.record_message("C-102", "c", "d")
        assert msg2["message_id"] == "MSG-0002"
        assert len(state.sent_messages) == 2


class TestReset:
    def test_reset_clears_mutations(self, state):
        state.close_ticket("T-1001", "done")
        state.process_refund("ORD-5001", 79.99, "test")
        state.record_message("C-101", "hi", "hello")

        state.reset()

        assert state.get_ticket("T-1001")["status"] == "open"
        assert state.is_refund_processed("ORD-5001") is False
        assert state.sent_messages == []
        assert "refund_status" not in state.orders["ORD-5001"]

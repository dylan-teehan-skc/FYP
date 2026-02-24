"""Tests for the FastAPI endpoints."""

from fastapi.testclient import TestClient

from main import app, state

client = TestClient(app)


def setup_function():
    """Reset state before each test."""
    state.reset()


class TestListTools:
    def test_returns_tools(self):
        response = client.get("/tools/list")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 13

    def test_tool_has_schema(self):
        response = client.get("/tools/list")
        tool = response.json()["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool


class TestCallTool:
    def test_call_check_ticket(self):
        response = client.post(
            "/tools/call",
            json={"name": "check_ticket_status", "arguments": {"ticket_id": "T-1001"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == "T-1001"
        assert data["status"] == "open"

    def test_call_unknown_tool(self):
        response = client.post(
            "/tools/call",
            json={"name": "nonexistent", "arguments": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_call_get_order(self):
        response = client.post(
            "/tools/call",
            json={"name": "get_order_details", "arguments": {"order_id": "ORD-5001"}},
        )
        assert response.status_code == 200
        assert response.json()["product"] == "Wireless Earbuds Pro"

    def test_call_search_kb(self):
        response = client.post(
            "/tools/call",
            json={"name": "search_knowledge_base", "arguments": {"query": "refund"}},
        )
        assert response.status_code == 200
        assert response.json()["results_count"] >= 1


class TestReset:
    def test_reset_endpoint(self):
        # Mutate state first
        client.post(
            "/tools/call",
            json={
                "name": "close_ticket",
                "arguments": {"ticket_id": "T-1001", "resolution_summary": "done"},
            },
        )

        # Reset
        response = client.post("/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "reset"

        # Verify state restored
        response = client.post(
            "/tools/call",
            json={"name": "check_ticket_status", "arguments": {"ticket_id": "T-1001"}},
        )
        assert response.json()["status"] == "open"

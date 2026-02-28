"""Tests for multi-agent graph structure and routing."""

from __future__ import annotations

import os

from langchain_core.messages import AIMessage

os.environ.setdefault("GOOGLE_API_KEY", "test-key")

from multi_agent.graph import (
    MultiAgentState,
    build_multi_agent_graph,
    route_after_supervisor,
)


class TestRouteAfterSupervisor:
    def test_routes_to_refund(self) -> None:
        state: MultiAgentState = {
            "messages": [AIMessage(content="Ticket is a refund request. ROUTE:REFUND")],
        }
        assert route_after_supervisor(state) == "refund_agent"

    def test_routes_to_support(self) -> None:
        state: MultiAgentState = {
            "messages": [AIMessage(content="Ticket is an order inquiry. ROUTE:SUPPORT")],
        }
        assert route_after_supervisor(state) == "support_agent"

    def test_defaults_to_support(self) -> None:
        state: MultiAgentState = {
            "messages": [AIMessage(content="I'm not sure what to do.")],
        }
        assert route_after_supervisor(state) == "support_agent"

    def test_empty_messages(self) -> None:
        state: MultiAgentState = {"messages": []}
        assert route_after_supervisor(state) == "support_agent"

    def test_case_insensitive(self) -> None:
        state: MultiAgentState = {
            "messages": [AIMessage(content="route:refund")],
        }
        assert route_after_supervisor(state) == "refund_agent"


class TestBuildMultiAgentGraph:
    def test_graph_has_correct_nodes(self) -> None:
        graph = build_multi_agent_graph("gemini-2.5-flash-lite")
        node_names = list(graph.nodes.keys())
        assert "supervisor" in node_names
        assert "refund_agent" in node_names
        assert "support_agent" in node_names

    def test_graph_compiles(self) -> None:
        graph = build_multi_agent_graph("gemini-2.5-flash-lite")
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")

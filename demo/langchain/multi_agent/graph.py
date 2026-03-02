"""LangGraph multi-agent graph with supervisor routing to specialists."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from langchain.agents import create_agent
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from tools import (
    apply_discount,
    check_refund_eligibility,
    check_ticket_status,
    check_warranty,
    close_ticket,
    escalate_ticket,
    get_customer_history,
    get_order_details,
    get_shipping_status,
    process_refund,
    schedule_callback,
    search_knowledge_base,
    send_customer_message,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

SUPERVISOR_PROMPT = (PROMPTS_DIR / "supervisor.txt").read_text()
REFUND_PROMPT = (PROMPTS_DIR / "refund.txt").read_text()
SUPPORT_PROMPT = (PROMPTS_DIR / "support.txt").read_text()

REFUND_TOOLS = [
    check_ticket_status,
    get_order_details,
    check_refund_eligibility,
    process_refund,
    send_customer_message,
    close_ticket,
]

SUPPORT_TOOLS = [
    check_ticket_status,
    get_order_details,
    check_refund_eligibility,
    process_refund,
    send_customer_message,
    close_ticket,
    get_customer_history,
    search_knowledge_base,
    escalate_ticket,
    apply_discount,
    check_warranty,
    get_shipping_status,
    schedule_callback,
]


class MultiAgentState(TypedDict):
    messages: Annotated[list, add_messages]


def route_after_supervisor(state: MultiAgentState) -> str:
    """Inspect supervisor output to route to the correct specialist."""
    messages = state.get("messages", [])
    if not messages:
        return "support_agent"

    last_content = ""
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content.strip():
            last_content = content.upper()
            break

    if "ROUTE:REFUND" in last_content:
        return "refund_agent"
    return "support_agent"


def build_multi_agent_graph(model_name: str) -> CompiledStateGraph:
    """Build a supervisor → specialist multi-agent graph."""
    model = f"google_genai:{model_name}"

    supervisor = create_agent(
        model=model,
        tools=[check_ticket_status],
        system_prompt=SUPERVISOR_PROMPT,
        name="supervisor",
    )
    refund_agent = create_agent(
        model=model,
        tools=REFUND_TOOLS,
        system_prompt=REFUND_PROMPT,
        name="refund_agent",
    )
    support_agent = create_agent(
        model=model,
        tools=SUPPORT_TOOLS,
        system_prompt=SUPPORT_PROMPT,
        name="support_agent",
    )

    builder = StateGraph(MultiAgentState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("refund_agent", refund_agent)
    builder.add_node("support_agent", support_agent)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        ["refund_agent", "support_agent"],
    )
    builder.add_edge("refund_agent", END)
    builder.add_edge("support_agent", END)

    return builder.compile()

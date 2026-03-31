"""LangChain agent demo with workflow-optimizer-sdk tracing."""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from workflow_optimizer import OptimalPathResponse, WorkflowOptimizer

from callback import WorkflowOptimizerCallbackHandler
from logger import get_logger, init_logging
from tools import ALL_TOOLS, close_client, reset_mcp_state, set_mcp_url

log = get_logger("langchain_demo")

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "reasoning.txt").read_text()


@dataclass(frozen=True)
class Scenario:
    ticket_id: str
    order_id: str
    customer_id: str
    workflow_type: str
    task_description: str
    expect_error: bool = False


SCENARIOS: list[Scenario] = [
    Scenario(
        ticket_id="T-1001",
        order_id="ORD-5001",
        customer_id="C-101",
        workflow_type="refund_request",
        task_description=(
            "Support ticket T-1001: Customer Alice Chen wants a refund for "
            "order ORD-5001 (Wireless Earbuds Pro, $79.99). "
            "Please resolve this ticket."
        ),
    ),
    Scenario(
        ticket_id="T-1002",
        order_id="ORD-5002",
        customer_id="C-102",
        workflow_type="order_inquiry",
        task_description=(
            "Support ticket T-1002: Customer Bob Martinez is asking about "
            "the status of order ORD-5002 (USB-C Hub Dock, $249.99). "
            "Please resolve this ticket."
        ),
    ),
    Scenario(
        ticket_id="T-1004",
        order_id="ORD-5004",
        customer_id="C-104",
        workflow_type="complaint",
        task_description=(
            "Support ticket T-1004: Customer David Kim has an issue "
            "with order ORD-5004 (Noise-Cancelling Headphones, $349.99). "
            "Please resolve this ticket."
        ),
    ),
    Scenario(
        ticket_id="T-1006",
        order_id="ORD-5006",
        customer_id="C-106",
        workflow_type="warranty_claim",
        task_description=(
            "Support ticket T-1006: Frank Torres says his Smart Watch Pro "
            "from order ORD-5006 stopped charging after a week. "
            "He's frustrated. Please resolve this ticket."
        ),
    ),
    Scenario(
        ticket_id="T-1007",
        order_id="ORD-5007",
        customer_id="C-107",
        workflow_type="shipping_inquiry",
        task_description=(
            "Support ticket T-1007: Grace Patel needs an update on "
            "the shipping status for order ORD-5007. "
            "Please resolve this ticket."
        ),
    ),
    # --- Error scenarios ---
    Scenario(
        ticket_id="T-9999",
        order_id="ORD-5001",
        customer_id="C-101",
        workflow_type="error_invalid_ticket",
        task_description=(
            "Support ticket T-9999: A customer has reported an issue. "
            "Please check ticket T-9999 and resolve it."
        ),
        expect_error=True,
    ),
    Scenario(
        ticket_id="T-1001",
        order_id="ORD-9999",
        customer_id="C-101",
        workflow_type="error_invalid_order",
        task_description=(
            "Support ticket T-1001: Customer Alice Chen is asking about "
            "order ORD-9999 which she cannot find. "
            "Please look up order ORD-9999 and resolve the ticket."
        ),
        expect_error=True,
    ),
]


@dataclass
class ScenarioResult:
    scenario: Scenario
    round_number: int
    mode: str
    success: bool
    steps: int
    duration_ms: float
    workflow_id: str
    confidence: float | None
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0


def build_guided_context(response: OptimalPathResponse) -> str:
    if response.mode != "guided" or not response.path:
        return ""

    numbered = "\n".join(f"  {i}. {tool}" for i, tool in enumerate(response.path, 1))
    parts = [
        "OPTIMIZATION HINT: A proven tool sequence for this type of task:",
        numbered,
    ]
    if response.success_rate is not None and response.execution_count is not None:
        parts.append(
            f"({response.success_rate:.0%} success rate, "
            f"{response.execution_count} previous runs)"
        )
    parts.append(
        "Execute tools in this order. Skip any tool that already "
        "shows [SUCCESS] in your execution history."
    )
    if response.failure_warnings:
        parts.append("\nKNOWN FAILURE MODES:")
        for warning in response.failure_warnings:
            parts.append(f"- {warning}")
    return "\n".join(parts)


def build_agent(model_name: str) -> CompiledStateGraph:
    return create_agent(
        model=f"google_genai:{model_name}",
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


async def run_scenario(
    scenario: Scenario,
    round_number: int,
    agent: CompiledStateGraph,
    optimizer: WorkflowOptimizer,
    model_name: str,
) -> ScenarioResult:
    log.info(
        "scenario_start",
        round=round_number,
        ticket=scenario.ticket_id,
        type=scenario.workflow_type,
    )

    guidance = await optimizer.get_optimal_path(scenario.task_description)
    mode = guidance.mode
    context = build_guided_context(guidance)

    if mode == "guided":
        log.info(
            "guided_mode",
            ticket=scenario.ticket_id,
            path=guidance.path,
            confidence=guidance.confidence,
        )

    start = time.perf_counter()

    async with optimizer.trace(
        scenario.task_description,
        agent_name="LangChainSupportAgent",
        agent_role="customer_support",
    ) as trace:
        trace.emit_mode(mode)

        handler = WorkflowOptimizerCallbackHandler(trace=trace, llm_model=model_name)

        input_text = scenario.task_description
        if context:
            input_text = f"{input_text}\n\n{context}"

        try:
            await agent.ainvoke(
                {"messages": [{"role": "user", "content": input_text}]},
                config={"callbacks": [handler], "recursion_limit": 30},
            )
            success = True
        except Exception as e:
            log.error("scenario_error", ticket=scenario.ticket_id, error=str(e)[:300])
            success = False

    duration_ms = (time.perf_counter() - start) * 1000

    status = "SUCCESS" if success else "FAILED"
    if scenario.expect_error:
        status += " (error scenario)"

    log.info(
        "scenario_complete",
        ticket=scenario.ticket_id,
        status=status,
        mode=mode,
        duration_ms=round(duration_ms),
        prompt_tokens=handler.total_prompt_tokens,
        completion_tokens=handler.total_completion_tokens,
    )

    return ScenarioResult(
        scenario=scenario,
        round_number=round_number,
        mode=mode,
        success=success,
        steps=trace._step_counter,
        duration_ms=duration_ms,
        workflow_id=trace.workflow_id,
        confidence=guidance.confidence,
        total_prompt_tokens=handler.total_prompt_tokens,
        total_completion_tokens=handler.total_completion_tokens,
    )


def log_round_summary(round_number: int, results: list[ScenarioResult]) -> None:
    total = len(results)
    successes = sum(1 for r in results if r.success)
    guided = sum(1 for r in results if r.mode == "guided")
    avg_duration = sum(r.duration_ms for r in results) / total if total else 0
    total_tokens = sum(r.total_prompt_tokens + r.total_completion_tokens for r in results)

    log.info(
        "round_summary",
        round=round_number,
        total=total,
        successes=successes,
        guided=guided,
        exploration=total - guided,
        avg_duration_ms=round(avg_duration),
        total_tokens=total_tokens,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LangChain demo with SDK tracing")
    parser.add_argument("--rounds", type=int, default=2, help="Number of rounds (default: 2)")
    parser.add_argument(
        "--collector-url",
        type=str,
        default="http://localhost:9000",
        help="Collector service URL (default: http://localhost:9000)",
    )
    parser.add_argument(
        "--mcp-url",
        type=str,
        default="http://localhost:8000",
        help="MCP tool server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash-lite",
        help="Model name for ChatGoogleGenerativeAI (default: gemini-2.5-flash-lite)",
    )
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()
    init_logging()

    log.info("demo_start", rounds=args.rounds, collector=args.collector_url, mcp=args.mcp_url)

    await set_mcp_url(args.mcp_url)
    agent = build_agent(args.model)

    optimizer = WorkflowOptimizer(
        endpoint=args.collector_url,
        agent_name="LangChainSupportAgent",
        agent_role="customer_support",
    )

    try:
        async with optimizer:
            all_results: list[ScenarioResult] = []
            for round_num in range(1, args.rounds + 1):
                log.info("round_start", round=round_num)
                await reset_mcp_state()

                round_results = []
                for scenario in SCENARIOS:
                    result = await run_scenario(
                        scenario, round_num, agent, optimizer, args.model,
                    )
                    round_results.append(result)

                log_round_summary(round_num, round_results)
                all_results.extend(round_results)

            log.info(
                "demo_complete",
                total_scenarios=len(all_results),
                total_successes=sum(1 for r in all_results if r.success),
            )
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())

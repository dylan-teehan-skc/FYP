"""Demo runner for NovaTech customer support scenarios."""

import argparse
import asyncio
import logging
import os
import random
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

from dotenv import load_dotenv  # noqa: E402
from workflow_optimizer import OptimalPathResponse, WorkflowOptimizer  # noqa: E402
from workflow_optimizer.trace import TraceContext  # noqa: E402

from agent.agent import Agent  # noqa: E402
from mcp.client import MCPClient  # noqa: E402
from reasoning.engine import ReasoningEngine  # noqa: E402
from utils.config import AppConfig  # noqa: E402
from utils.exceptions import ConfigurationError, LoopDetectedError  # noqa: E402
from utils.logger import get_logger, init_logging  # noqa: E402

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """A single NovaTech demo scenario."""

    ticket_id: str
    order_id: str
    customer_id: str
    workflow_type: str
    task_description: str
    expected_steps: int


@dataclass
class LastDecision:
    """Shared state: reasoning engine writes, tracing MCP client reads."""

    reasoning: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class ScenarioResult:
    """Metrics captured from a single scenario execution."""

    scenario: Scenario
    round_number: int
    mode: str
    success: bool
    steps: int
    duration_ms: float
    tool_sequence: list[str]
    workflow_id: str
    confidence: float | None
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: list[Scenario] = [
    Scenario(
        ticket_id="T-1001",
        order_id="ORD-5001",
        customer_id="C-101",
        workflow_type="refund_request",
        task_description=(
            "Handle support ticket T-1001: Customer Alice Chen requests a refund "
            "for order ORD-5001 (Wireless Earbuds Pro, $79.99). Check ticket status, "
            "look up the order, check refund eligibility, process refund if eligible, "
            "notify the customer, and close the ticket."
        ),
        expected_steps=6,
    ),
    Scenario(
        ticket_id="T-1002",
        order_id="ORD-5002",
        customer_id="C-102",
        workflow_type="order_inquiry",
        task_description=(
            "Handle support ticket T-1002: Customer Bob Martinez inquires about "
            "order ORD-5002 status (USB-C Hub Dock, $249.99). Check ticket status, "
            "look up the order, inform the customer of the current status, and "
            "close the ticket."
        ),
        expected_steps=4,
    ),
    Scenario(
        ticket_id="T-1003",
        order_id="ORD-5003",
        customer_id="C-103",
        workflow_type="refund_request",
        task_description=(
            "Handle support ticket T-1003: Customer Carol Johnson requests a refund "
            "for order ORD-5003 (Bluetooth Speaker, $159.00). Check ticket status, "
            "look up the order, check refund eligibility, if denied search for "
            "the refund policy to explain, notify the customer, and close the ticket."
        ),
        expected_steps=6,
    ),
    Scenario(
        ticket_id="T-1004",
        order_id="ORD-5004",
        customer_id="C-104",
        workflow_type="complaint",
        task_description=(
            "Handle support ticket T-1004: VIP customer David Kim complains about "
            "order ORD-5004 (Noise-Cancelling Headphones, $349.99). Check ticket "
            "status, look up customer history to see VIP tier, look up the order, "
            "search the knowledge base for VIP handling policy, send a resolution "
            "message, and close the ticket."
        ),
        expected_steps=6,
    ),
    Scenario(
        ticket_id="T-1005",
        order_id="ORD-5005",
        customer_id="C-105",
        workflow_type="product_support",
        task_description=(
            "Handle support ticket T-1005: Customer Emma Wilson needs help pairing "
            "her Wireless Headphones from order ORD-5005 ($99.99). Check ticket "
            "status, search the knowledge base for pairing instructions, send the "
            "instructions to the customer, and close the ticket."
        ),
        expected_steps=4,
    ),
]


# ---------------------------------------------------------------------------
# Tracing wrappers (transparent proxy pattern)
# ---------------------------------------------------------------------------

class TracingReasoningEngine:
    """Wraps ReasoningEngine, captures LLM metrics into LastDecision."""

    def __init__(self, inner: ReasoningEngine, last_decision: LastDecision) -> None:
        self._inner = inner
        self._last_decision = last_decision
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    def reset_totals(self) -> None:
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0

    @property
    def total_prompt_tokens(self) -> int:
        return self._total_prompt_tokens

    @property
    def total_completion_tokens(self) -> int:
        return self._total_completion_tokens

    async def reason(
        self,
        task: str,
        context: str,
        tools_doc: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        result = await self._inner.reason(task, context, tools_doc, history)
        self._last_decision.reasoning = result.get("reasoning", "")
        self._last_decision.prompt_tokens = result.get("prompt_tokens", 0)
        self._last_decision.completion_tokens = result.get("completion_tokens", 0)
        self._total_prompt_tokens += self._last_decision.prompt_tokens
        self._total_completion_tokens += self._last_decision.completion_tokens
        return result


class TracingMCPClient:
    """Transparent proxy: wraps MCPClient, records each tool call as an SDK trace step."""

    def __init__(
        self,
        inner: MCPClient,
        last_decision: LastDecision,
        llm_model: str,
    ) -> None:
        self._inner = inner
        self._trace: TraceContext | None = None
        self._last_decision = last_decision
        self._llm_model = llm_model

    def set_trace(self, trace: TraceContext | None) -> None:
        self._trace = trace

    async def connect(self) -> bool:
        return await self._inner.connect()

    async def close(self) -> None:
        await self._inner.close()

    def get_tools_documentation(self) -> str:
        return self._inner.get_tools_documentation()

    async def call_tool(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        if self._trace is None:
            return await self._inner.call_tool(tool_name, parameters)

        with self._trace.step(
            tool_name,
            params=parameters,
            llm_model=self._llm_model,
            llm_prompt_tokens=self._last_decision.prompt_tokens,
            llm_completion_tokens=self._last_decision.completion_tokens,
            llm_reasoning=self._last_decision.reasoning,
        ) as step:
            result = await self._inner.call_tool(tool_name, parameters)
            if result["success"]:
                step.set_response(result.get("result", {}))
            else:
                step.set_error(result.get("error", "unknown error"))
            return result


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_config() -> AppConfig:
    config_path = Path(__file__).parent / "config.json"
    try:
        return AppConfig.model_validate_json(config_path.read_text())
    except FileNotFoundError as e:
        raise ConfigurationError(f"Config file not found: {config_path}") from e
    except Exception as e:
        raise ConfigurationError(f"Invalid configuration: {e}") from e


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run NovaTech demo scenarios across multiple rounds"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of rounds to run (default: 3)",
    )
    parser.add_argument(
        "--collector-url",
        type=str,
        default="http://localhost:9000",
        help="Collector service URL (default: http://localhost:9000)",
    )
    return parser.parse_args()


def build_guided_context(response: OptimalPathResponse) -> str:
    """Format an optimal path response into agent context for guided mode."""
    if response.mode != "guided" or not response.path:
        return ""

    steps = " -> ".join(response.path)
    parts = [
        "GUIDED MODE: An optimal execution path has been identified for this task type.",
        f"Recommended tool sequence: {steps}",
    ]
    if response.success_rate is not None and response.execution_count is not None:
        parts.append(
            f"This path has a {response.success_rate:.0%} success rate "
            f"across {response.execution_count} previous executions."
        )
    if response.avg_duration_ms is not None and response.avg_steps is not None:
        parts.append(
            f"Average duration: {response.avg_duration_ms:.0f}ms, "
            f"average steps: {response.avg_steps:.1f}."
        )
    parts.append(
        "Follow this sequence unless you have a specific reason to deviate. "
        "Execute each tool in order, using information from previous steps to "
        "fill parameters for subsequent tools."
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Execution functions
# ---------------------------------------------------------------------------

async def run_scenario(
    scenario: Scenario,
    round_number: int,
    tracing_mcp: TracingMCPClient,
    tracing_reasoning: TracingReasoningEngine,
    optimizer: WorkflowOptimizer,
    config: AppConfig,
) -> ScenarioResult:
    """Run a single scenario with SDK tracing and return metrics."""
    log = get_logger("demo_runner")

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

    agent = Agent(
        name="SupportAgent",
        role="customer_support",
        reasoning_engine=tracing_reasoning,
        mcp_client=tracing_mcp,
        loop_threshold=config.agent.loop_detection_threshold,
        loop_window=config.agent.loop_detection_window,
    )

    tracing_reasoning.reset_totals()
    start = time.perf_counter()

    async with optimizer.trace(
        scenario.task_description,
        agent_name="SupportAgent",
        agent_role="customer_support",
    ) as trace:
        tracing_mcp.set_trace(trace)
        try:
            result = await agent.execute(scenario.task_description, context=context)
            success = result["success"]
            steps = result.get("steps", 0)
            history = result.get("history", [])
        except LoopDetectedError as e:
            log.warning("loop_detected", ticket=scenario.ticket_id, error=str(e))
            success = False
            steps = len(agent.action_history)
            history = agent.action_history
        finally:
            tracing_mcp.set_trace(None)

    duration_ms = (time.perf_counter() - start) * 1000
    tool_sequence = [h["action"] for h in history if h.get("action")]

    return ScenarioResult(
        scenario=scenario,
        round_number=round_number,
        mode=mode,
        success=success,
        steps=steps,
        duration_ms=duration_ms,
        tool_sequence=tool_sequence,
        workflow_id=trace.workflow_id,
        confidence=guidance.confidence,
        total_prompt_tokens=tracing_reasoning.total_prompt_tokens,
        total_completion_tokens=tracing_reasoning.total_completion_tokens,
    )


async def run_round(
    round_number: int,
    total_rounds: int,
    scenarios: list[Scenario],
    tracing_mcp: TracingMCPClient,
    tracing_reasoning: TracingReasoningEngine,
    optimizer: WorkflowOptimizer,
    config: AppConfig,
) -> list[ScenarioResult]:
    """Run all scenarios for one round, shuffled."""
    log = get_logger("demo_runner")
    log.info("round_start", round=round_number, total_rounds=total_rounds)

    shuffled = list(scenarios)
    random.shuffle(shuffled)

    results: list[ScenarioResult] = []
    for i, scenario in enumerate(shuffled, 1):
        log.info(
            "scenario_start",
            round=round_number,
            index=f"{i}/{len(shuffled)}",
            ticket=scenario.ticket_id,
            type=scenario.workflow_type,
        )

        result = await run_scenario(
            scenario, round_number, tracing_mcp, tracing_reasoning,
            optimizer, config,
        )
        results.append(result)

        status = "SUCCESS" if result.success else "FAILED"
        log.info(
            "scenario_complete",
            ticket=scenario.ticket_id,
            type=scenario.workflow_type,
            mode=result.mode,
            status=status,
            steps=result.steps,
            expected=scenario.expected_steps,
            duration_ms=round(result.duration_ms),
            tools=" -> ".join(result.tool_sequence),
        )

    return results


# ---------------------------------------------------------------------------
# Summary display (structlog, never print)
# ---------------------------------------------------------------------------

def log_round_summary(round_number: int, results: list[ScenarioResult]) -> None:
    log = get_logger("demo_runner")
    total = len(results)
    if total == 0:
        return

    successes = sum(1 for r in results if r.success)
    avg_steps = sum(r.steps for r in results) / total
    avg_duration = sum(r.duration_ms for r in results) / total
    guided_count = sum(1 for r in results if r.mode == "guided")
    total_prompt = sum(r.total_prompt_tokens for r in results)
    total_completion = sum(r.total_completion_tokens for r in results)

    log.info(
        "round_summary",
        round=round_number,
        success=f"{successes}/{total}",
        avg_steps=round(avg_steps, 1),
        avg_duration_ms=round(avg_duration),
        guided=guided_count,
        exploration=total - guided_count,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
    )


def log_final_summary(all_results: list[ScenarioResult]) -> None:
    log = get_logger("demo_runner")

    if not all_results:
        log.info("no_results")
        return

    exploration = [r for r in all_results if r.mode == "exploration"]
    guided = [r for r in all_results if r.mode == "guided"]

    def avg(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    summary: dict[str, Any] = {
        "total_workflows": len(all_results),
        "total_success": sum(1 for r in all_results if r.success),
        "total_prompt_tokens": sum(r.total_prompt_tokens for r in all_results),
        "total_completion_tokens": sum(r.total_completion_tokens for r in all_results),
    }

    if exploration:
        summary["exploration_count"] = len(exploration)
        summary["exploration_avg_steps"] = round(avg([r.steps for r in exploration]), 1)
        summary["exploration_avg_duration_ms"] = round(avg([r.duration_ms for r in exploration]))
        summary["exploration_success_rate"] = round(
            sum(1 for r in exploration if r.success) / len(exploration), 2
        )

    if guided:
        summary["guided_count"] = len(guided)
        summary["guided_avg_steps"] = round(avg([r.steps for r in guided]), 1)
        summary["guided_avg_duration_ms"] = round(avg([r.duration_ms for r in guided]))
        summary["guided_success_rate"] = round(
            sum(1 for r in guided if r.success) / len(guided), 2
        )

    log.info("final_summary", **summary)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the NovaTech demo scenarios."""
    load_dotenv()
    args = parse_args()

    config = load_config()
    init_logging(config.logging)
    log = get_logger("demo_runner")

    log.info(
        "demo_start",
        rounds=args.rounds,
        scenarios=len(SCENARIOS),
        total_workflows=args.rounds * len(SCENARIOS),
        collector_url=args.collector_url,
    )

    mcp_url = os.getenv("MCP_SERVER_URL", config.mcp.server_url)

    reasoning_engine = ReasoningEngine(model=config.llm.model)
    mcp_client = MCPClient(
        server_url=mcp_url,
        timeout=config.mcp.timeout_seconds,
        max_retries=config.mcp.max_retries,
    )

    if not await mcp_client.connect():
        log.error("mcp_connection_failed", url=mcp_url)
        return

    log.info("mcp_connected", url=mcp_url)

    optimizer = WorkflowOptimizer(
        endpoint=args.collector_url,
        agent_name="SupportAgent",
        agent_role="customer_support",
    )

    last_decision = LastDecision()
    tracing_reasoning = TracingReasoningEngine(reasoning_engine, last_decision)
    tracing_mcp = TracingMCPClient(mcp_client, last_decision, config.llm.model)

    try:
        async with optimizer:
            all_results: list[ScenarioResult] = []

            for round_num in range(1, args.rounds + 1):
                results = await run_round(
                    round_num, args.rounds, SCENARIOS,
                    tracing_mcp, tracing_reasoning, optimizer, config,
                )
                all_results.extend(results)
                log_round_summary(round_num, results)

            log_final_summary(all_results)
    finally:
        await mcp_client.close()
        log.info("demo_complete")


if __name__ == "__main__":
    asyncio.run(main())

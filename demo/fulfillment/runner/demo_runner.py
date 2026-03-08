"""Demo runner for order fulfillment scenarios with deterministic verification."""

import argparse
import asyncio
import logging
import random
import sys
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Add agent-runtime to path so we can reuse its components
AGENT_RUNTIME_DIR = Path(__file__).resolve().parents[2] / "agent-runtime"
sys.path.insert(0, str(AGENT_RUNTIME_DIR))

from agent.agent import Agent  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from mcp.client import MCPClient  # noqa: E402
from reasoning.engine import ReasoningEngine  # noqa: E402
from utils.config import LoggingConfig  # noqa: E402
from utils.exceptions import LoopDetectedError, MCPToolError  # noqa: E402
from utils.logger import get_logger, init_logging  # noqa: E402
from workflow_optimizer import OptimalPathResponse, WorkflowOptimizer  # noqa: E402
from workflow_optimizer.trace import TraceContext  # noqa: E402

from runner.composite_client import CompositeMCPClient  # noqa: E402

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """A single scenario: fulfillment, return, or exchange."""

    order_id: str
    workflow_type: str
    task_description: str
    expected_status: str
    expected_total: float | None = None
    expected_delivery_days: int | None = None
    replacement_order_id: str | None = None
    expected_replacement_status: str | None = None
    expected_replacement_total: float | None = None
    expected_replacement_days: int | None = None


@dataclass
class LastDecision:
    """Shared state: reasoning engine writes, tracing MCP client reads."""

    reasoning: str = ""
    llm_prompt: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class VerificationResult:
    """Result of checking the DB state after a scenario."""

    order_id: str
    passed: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    """Metrics from a single scenario execution."""

    scenario: Scenario
    round_number: int
    mode: str
    success: bool
    verified: bool
    steps: int
    duration_ms: float
    tool_sequence: list[str]
    workflow_id: str
    confidence: float | None
    verification: VerificationResult | None = None
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0


# ---------------------------------------------------------------------------
# Scenario definitions — 43 scenarios across 6 MCP servers
# ---------------------------------------------------------------------------
# Vagueness levels:
#   VAGUE    — intent keywords but no instructions, agent discovers everything
#   MEDIUM   — states the goal, not the steps
#   DETAILED — step-by-step instructions (original style)
#
# Pre-computed expected outcomes from seed.sql:
#
# FULFILLMENT (10 incl. 1 backorder + 1 blocked)
#
# ORD-201: P-101 $45, 1.2kg → C-301(east,std) → WH-1 $52.40 / 2d
# ORD-202: P-102 $29, 0.3kg → C-302(west,vip) → WH-2 $31.70 / 2d
# ORD-203: P-103 → C-303(central,gold) → all out of stock → BACKORDERED
# ORD-204: P-104 $35×3, 2.4kg → C-304(west,vip) → WH-3 $108.70 / 3d
# ORD-205: P-105 $299, 25kg → C-305(east,std) → WH-1 $354.00 / 2d + risk
# ORD-206: P-105 $299 → C-303(FLAGGED) → risk 0.7 → BLOCKED
# ORD-207: P-105 $299 → C-302(west,vip) → risk review → override → $324.10/2d
# ORD-208: P-101 $45 → C-303(gold) → wallet $0 fails → debit → $53.35/3d
# ORD-209: P-104 $35 → C-301(east,std) → WH-1 $41.60/2d + SMS notify
# ORD-210: P-102 $29 → C-301(east,std) → WH-3 $36.90/3d
# ORD-211: P-104 $35×2 → C-302(west,vip) → WH-3 $74.80/3d
# ORD-212: P-101 $45 → C-304(west,vip) → WH-2 $47.90/2d
#
# RETURNS (8 incl. 1 denied)
#
# ORD-301: fulfilled 2026-02-15, P-101 30d → eligible → returned
# ORD-302: fulfilled 2026-01-10, P-102 30d → expired → stays fulfilled
# ORD-303: backordered → auto-eligible → returned (refund $0)
# ORD-304: fulfilled 2026-02-25, P-104 14d → eligible → returned
# ORD-305: fulfilled 2026-02-20, P-102 30d → eligible → returned
# ORD-306: fulfilled 2026-02-18, P-101 30d → eligible → returned
# ORD-307: fulfilled 2026-02-22, P-102 30d → eligible → returned
# ORD-308: fulfilled 2026-02-10, P-102 30d → eligible → returned
#
# EXCHANGES (7)
#
# ORD-401→501: return P-101 + fulfil P-102 for C-304(west,vip) → $31.70/2d
# ORD-402→502: return P-104 + fulfil P-103 for C-305(east,std) → backordered
# ORD-403→503: return P-102 + fulfil P-104 for C-303(gold) → $38.45/1d
# ORD-404→504: return P-104 + fulfil P-105 for C-302(vip) → $324.10/2d+risk
# ORD-405→505: return P-102 + fulfil P-104 for C-301(east,std) → $41.60/2d
# ORD-406→506: return P-101 + fulfil P-102 for C-302(west,vip) → $31.70/2d
# ORD-407→507: return P-104 + fulfil P-101 for C-304(west,vip) → $47.90/2d

SCENARIOS: list[Scenario] = [
    # --- Fulfillment (12: 10 standard + 1 backorder + 1 blocked) ---
    # VAGUE
    Scenario(
        order_id="ORD-201",
        workflow_type="fulfilment",
        task_description="Fulfil order ORD-201 and ship it to the customer.",
        expected_status="fulfilled",
        expected_total=52.40,
        expected_delivery_days=2,
    ),
    # MEDIUM
    Scenario(
        order_id="ORD-202",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-202. "
            "Make sure payment is processed and the customer is notified."
        ),
        expected_status="fulfilled",
        expected_total=31.70,
        expected_delivery_days=2,
    ),
    # VAGUE
    Scenario(
        order_id="ORD-203",
        workflow_type="backorder",
        task_description="Fulfil order ORD-203 and ship it to the customer.",
        expected_status="backordered",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-204",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-204. It's a multi-quantity order "
            "— ship it as cheaply as possible."
        ),
        expected_status="fulfilled",
        expected_total=108.70,
        expected_delivery_days=3,
    ),
    # MEDIUM — high value, mentions risk
    Scenario(
        order_id="ORD-205",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-205. This is a high-value order so "
            "check risk compliance before processing."
        ),
        expected_status="fulfilled",
        expected_total=354.00,
        expected_delivery_days=2,
    ),
    # VAGUE — flagged customer + high value → blocked
    Scenario(
        order_id="ORD-206",
        workflow_type="blocked",
        task_description=(
            "Fulfil order ORD-206 — check "
            "everything is in order before shipping."
        ),
        expected_status="pending",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-210",
        workflow_type="fulfilment",
        task_description="Fulfil order ORD-210 and ship it to the customer.",
        expected_status="fulfilled",
        expected_total=36.90,
        expected_delivery_days=3,
    ),
    # MEDIUM
    Scenario(
        order_id="ORD-211",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-211. "
            "Multi-quantity order — find the cheapest shipping option."
        ),
        expected_status="fulfilled",
        expected_total=74.80,
        expected_delivery_days=3,
    ),
    # VAGUE
    Scenario(
        order_id="ORD-212",
        workflow_type="fulfilment",
        task_description="Fulfil order ORD-212 and ship it to the customer.",
        expected_status="fulfilled",
        expected_total=47.90,
        expected_delivery_days=2,
    ),
    # --- Returns (7) ---
    # VAGUE
    Scenario(
        order_id="ORD-301",
        workflow_type="return",
        task_description="Customer wants to return order ORD-301 and get a refund.",
        expected_status="returned",
    ),
    # MEDIUM
    Scenario(
        order_id="ORD-302",
        workflow_type="return_denied",
        task_description=(
            "Check if order ORD-302 can be returned and process it "
            "if possible. Notify the customer either way."
        ),
        expected_status="fulfilled",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-303",
        workflow_type="return",
        task_description="Customer wants to return order ORD-303.",
        expected_status="returned",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-304",
        workflow_type="return",
        task_description="Customer is requesting a return and refund for order ORD-304.",
        expected_status="returned",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-306",
        workflow_type="return",
        task_description="Customer wants to return order ORD-306 and get a refund.",
        expected_status="returned",
    ),
    # MEDIUM
    Scenario(
        order_id="ORD-307",
        workflow_type="return",
        task_description=(
            "Process a return and refund for order ORD-307. "
            "Check eligibility and notify the customer."
        ),
        expected_status="returned",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-308",
        workflow_type="return",
        task_description="Customer wants to return order ORD-308 for a refund.",
        expected_status="returned",
    ),
    # --- Exchanges (7) ---
    # VAGUE
    Scenario(
        order_id="ORD-401",
        workflow_type="exchange",
        task_description=(
            "Customer wants to exchange order ORD-401 — return the "
            "original and fulfil replacement ORD-501."
        ),
        expected_status="returned",
        replacement_order_id="ORD-501",
        expected_replacement_status="fulfilled",
        expected_replacement_total=31.70,
        expected_replacement_days=2,
    ),
    # MEDIUM
    Scenario(
        order_id="ORD-402",
        workflow_type="exchange",
        task_description=(
            "Exchange ORD-402: return the original, fulfil replacement "
            "ORD-502. Replacement product may be out of stock."
        ),
        expected_status="returned",
        replacement_order_id="ORD-502",
        expected_replacement_status="backordered",
    ),
    # VAGUE
    Scenario(
        order_id="ORD-403",
        workflow_type="exchange",
        task_description=(
            "Customer wants to exchange order ORD-403 for "
            "replacement order ORD-503."
        ),
        expected_status="returned",
        replacement_order_id="ORD-503",
        expected_replacement_status="fulfilled",
        expected_replacement_total=38.45,
        expected_replacement_days=1,
    ),
    # VAGUE — high-value replacement triggers risk
    Scenario(
        order_id="ORD-404",
        workflow_type="exchange",
        task_description="Customer wants to exchange order ORD-404 for replacement order ORD-504.",
        expected_status="returned",
        replacement_order_id="ORD-504",
        expected_replacement_status="fulfilled",
        expected_replacement_total=324.10,
        expected_replacement_days=2,
    ),
    # VAGUE
    Scenario(
        order_id="ORD-405",
        workflow_type="exchange",
        task_description=(
            "Customer wants to exchange order ORD-405 — return it "
            "and fulfil replacement ORD-505."
        ),
        expected_status="returned",
        replacement_order_id="ORD-505",
        expected_replacement_status="fulfilled",
        expected_replacement_total=41.60,
        expected_replacement_days=2,
    ),
    # MEDIUM
    Scenario(
        order_id="ORD-406",
        workflow_type="exchange",
        task_description=(
            "Exchange order ORD-406: return the original item and "
            "fulfil replacement order ORD-506 for the customer."
        ),
        expected_status="returned",
        replacement_order_id="ORD-506",
        expected_replacement_status="fulfilled",
        expected_replacement_total=31.70,
        expected_replacement_days=2,
    ),
    # VAGUE
    Scenario(
        order_id="ORD-407",
        workflow_type="exchange",
        task_description="Customer wants to exchange order ORD-407 for replacement order ORD-507.",
        expected_status="returned",
        replacement_order_id="ORD-507",
        expected_replacement_status="fulfilled",
        expected_replacement_total=47.90,
        expected_replacement_days=2,
    ),
    # --- Additional Fulfillment + Returns (cross-domain complexity) ---
    # VAGUE — VIP + risk review
    Scenario(
        order_id="ORD-207",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-207 and ship it to the customer."
        ),
        expected_status="fulfilled",
        expected_total=324.10,
        expected_delivery_days=2,
    ),
    # VAGUE — payment retry scenario
    Scenario(
        order_id="ORD-208",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-208 and ship it to the customer."
        ),
        expected_status="fulfilled",
        expected_total=53.35,
        expected_delivery_days=3,
    ),
    # VAGUE — return for fulfilled order
    Scenario(
        order_id="ORD-305",
        workflow_type="return",
        task_description="Customer wants to return order ORD-305 and get a refund.",
        expected_status="returned",
    ),
    # MEDIUM — specific notification channel
    Scenario(
        order_id="ORD-209",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-209. The customer called asking to be "
            "notified by SMS only, not email."
        ),
        expected_status="fulfilled",
        expected_total=41.60,
        expected_delivery_days=2,
    ),
    # --- Expanded Fulfillment (10: incl. 1 backorder, 2 risk review) ---
    # VAGUE — agent may waste time checking promotions
    Scenario(
        order_id="ORD-213",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-213 — make sure the customer "
            "gets the best possible deal."
        ),
        expected_status="fulfilled",
        expected_total=47.90,
        expected_delivery_days=2,
    ),
    # MEDIUM — bulk order, agent should check promotions
    Scenario(
        order_id="ORD-214",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-214. This is a bulk order — "
            "check if there are any applicable promotions."
        ),
        expected_status="fulfilled",
        expected_total=109.55,
        expected_delivery_days=2,
    ),
    # VAGUE — high value, risk review, new customer C-308
    Scenario(
        order_id="ORD-215",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-215 and ship it to the customer."
        ),
        expected_status="fulfilled",
        expected_total=324.10,
        expected_delivery_days=2,
    ),
    # VAGUE — simple fulfillment, promotion exists but wrong qty
    Scenario(
        order_id="ORD-216",
        workflow_type="fulfilment",
        task_description="Fulfil order ORD-216 and ship it to the customer.",
        expected_status="fulfilled",
        expected_total=36.90,
        expected_delivery_days=3,
    ),
    # MEDIUM — new customer C-307, new product P-106, 4th warehouse
    Scenario(
        order_id="ORD-217",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-217. New customer — make sure "
            "everything is set up properly."
        ),
        expected_status="fulfilled",
        expected_total=57.00,
        expected_delivery_days=2,
    ),
    # VAGUE — new product P-107, ships from new warehouse WH-4
    Scenario(
        order_id="ORD-218",
        workflow_type="fulfilment",
        task_description="Fulfil order ORD-218 and ship it to the customer.",
        expected_status="fulfilled",
        expected_total=153.05,
        expected_delivery_days=3,
    ),
    # MEDIUM — P-103 still OOS, agent should check restock ETA
    Scenario(
        order_id="ORD-219",
        workflow_type="backorder",
        task_description=(
            "Fulfil order ORD-219. If the product is out of stock, "
            "check when it might be restocked."
        ),
        expected_status="backordered",
    ),
    # VAGUE — high value multi-qty P-108, risk review
    Scenario(
        order_id="ORD-220",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-220 and ship it to the customer."
        ),
        expected_status="fulfilled",
        expected_total=367.60,
        expected_delivery_days=3,
    ),
    # MEDIUM — bulk P-106, new warehouse comparison
    Scenario(
        order_id="ORD-221",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil bulk order ORD-221. Reserve inventory and "
            "find cheapest shipping."
        ),
        expected_status="fulfilled",
        expected_total=127.00,
        expected_delivery_days=5,
    ),
    # VAGUE — flagged customer, risk + payment retry, P-107
    Scenario(
        order_id="ORD-222",
        workflow_type="fulfilment",
        task_description=(
            "Fulfil order ORD-222 and ship it to the customer."
        ),
        expected_status="fulfilled",
        expected_total=150.05,
        expected_delivery_days=2,
    ),
    # --- Expanded Returns (3) ---
    # VAGUE
    Scenario(
        order_id="ORD-309",
        workflow_type="return",
        task_description=(
            "Customer wants to return order ORD-309 and get a refund."
        ),
        expected_status="returned",
    ),
    # VAGUE — P-108 has 14d window, only 3 days ago
    Scenario(
        order_id="ORD-310",
        workflow_type="return",
        task_description=(
            "Customer wants to return order ORD-310 and "
            "get a refund."
        ),
        expected_status="returned",
    ),
    # MEDIUM — C-307, no phone for SMS notification
    Scenario(
        order_id="ORD-311",
        workflow_type="return",
        task_description=(
            "Process return for order ORD-311. Check eligibility "
            "and notify the customer."
        ),
        expected_status="returned",
    ),
    # --- Expanded Exchanges (3) ---
    # VAGUE — C-308 VIP, return P-107, fulfil P-106
    Scenario(
        order_id="ORD-410",
        workflow_type="exchange",
        task_description=(
            "Customer wants to exchange order ORD-410 — return "
            "the original and fulfil replacement ORD-510."
        ),
        expected_status="returned",
        replacement_order_id="ORD-510",
        expected_replacement_status="fulfilled",
        expected_replacement_total=33.40,
        expected_replacement_days=5,
    ),
    # MEDIUM — C-306, return P-108, fulfil P-107
    Scenario(
        order_id="ORD-411",
        workflow_type="exchange",
        task_description=(
            "Exchange ORD-411: return the original item and "
            "fulfil replacement order ORD-511 for the customer."
        ),
        expected_status="returned",
        replacement_order_id="ORD-511",
        expected_replacement_status="fulfilled",
        expected_replacement_total=153.05,
        expected_replacement_days=3,
    ),
    # VAGUE — C-303 flagged, risk + payment retry on replacement
    Scenario(
        order_id="ORD-412",
        workflow_type="exchange",
        task_description=(
            "Customer wants to exchange order ORD-412 for "
            "replacement order ORD-512."
        ),
        expected_status="returned",
        replacement_order_id="ORD-512",
        expected_replacement_status="fulfilled",
        expected_replacement_total=193.65,
        expected_replacement_days=1,
    ),
]


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

async def verify_outcome(
    scenario: Scenario, mcp_client: CompositeMCPClient,
) -> VerificationResult:
    """Check the DB state after a scenario."""
    errors: list[str] = []

    result = await mcp_client.call_tool(
        "get_order", {"order_id": scenario.order_id},
    )
    if not result["success"]:
        return VerificationResult(
            order_id=scenario.order_id,
            passed=False,
            errors=[f"Could not read order: {result.get('error')}"],
        )

    order = result["result"]
    actual_status = order.get("status")

    if actual_status != scenario.expected_status:
        errors.append(
            f"{scenario.order_id} status: expected"
            f" {scenario.expected_status}, got {actual_status}"
        )

    if scenario.expected_total is not None:
        actual_total = order.get("total")
        if actual_total is None:
            errors.append(
                f"{scenario.order_id} total: expected"
                f" {scenario.expected_total}, got None"
            )
        elif abs(actual_total - scenario.expected_total) > 0.02:
            errors.append(
                f"{scenario.order_id} total: expected"
                f" {scenario.expected_total}, got {actual_total}"
            )

    if scenario.expected_delivery_days is not None:
        actual_days = order.get("delivery_days")
        if actual_days != scenario.expected_delivery_days:
            errors.append(
                f"{scenario.order_id} delivery_days: expected"
                f" {scenario.expected_delivery_days}, got {actual_days}"
            )

    # Exchange: also verify the replacement order
    if scenario.replacement_order_id:
        repl = await mcp_client.call_tool(
            "get_order", {"order_id": scenario.replacement_order_id},
        )
        if not repl["success"]:
            errors.append(
                f"Could not read replacement:"
                f" {repl.get('error')}"
            )
        else:
            repl_order = repl["result"]
            repl_status = repl_order.get("status")
            if repl_status != scenario.expected_replacement_status:
                errors.append(
                    f"{scenario.replacement_order_id} status:"
                    f" expected {scenario.expected_replacement_status},"
                    f" got {repl_status}"
                )
            if scenario.expected_replacement_total is not None:
                repl_total = repl_order.get("total")
                if repl_total is None:
                    errors.append(
                        f"{scenario.replacement_order_id} total:"
                        f" expected"
                        f" {scenario.expected_replacement_total},"
                        f" got None"
                    )
                elif abs(
                    repl_total - scenario.expected_replacement_total
                ) > 0.02:
                    errors.append(
                        f"{scenario.replacement_order_id} total:"
                        f" expected"
                        f" {scenario.expected_replacement_total},"
                        f" got {repl_total}"
                    )
            if scenario.expected_replacement_days is not None:
                repl_days = repl_order.get("delivery_days")
                if repl_days != scenario.expected_replacement_days:
                    errors.append(
                        f"{scenario.replacement_order_id}"
                        f" delivery_days: expected"
                        f" {scenario.expected_replacement_days},"
                        f" got {repl_days}"
                    )

    return VerificationResult(
        order_id=scenario.order_id,
        passed=len(errors) == 0,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Tracing wrappers (reused pattern from agent-runtime demo)
# ---------------------------------------------------------------------------

class TracingReasoningEngine:
    """Wraps ReasoningEngine, captures LLM metrics into LastDecision."""

    def __init__(
        self, inner: ReasoningEngine, last_decision: LastDecision,
    ) -> None:
        self._inner = inner
        self._last_decision = last_decision
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
        result = await self._inner.reason(
            task, context, tools_doc, history,
        )
        self._last_decision.reasoning = result.get("reasoning", "")
        self._last_decision.llm_prompt = result.get("llm_prompt", "")
        self._last_decision.prompt_tokens = result.get(
            "prompt_tokens", 0,
        )
        self._last_decision.completion_tokens = result.get(
            "completion_tokens", 0,
        )
        self._last_decision.cost_usd = result.get("cost_usd", 0.0)
        self._total_prompt_tokens += self._last_decision.prompt_tokens
        self._total_completion_tokens += (
            self._last_decision.completion_tokens
        )
        return result


class TracingMCPClient:
    """Transparent proxy: records each tool call as a trace step."""

    def __init__(
        self,
        inner: CompositeMCPClient,
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
        self, tool_name: str, parameters: dict[str, Any],
    ) -> dict[str, Any]:
        if self._trace is None:
            return await self._inner.call_tool(tool_name, parameters)

        with self._trace.step(
            tool_name,
            params=parameters,
            llm_model=self._llm_model,
            llm_prompt_tokens=self._last_decision.prompt_tokens,
            llm_completion_tokens=(
                self._last_decision.completion_tokens
            ),
            llm_reasoning=self._last_decision.reasoning,
            llm_prompt=self._last_decision.llm_prompt,
        ) as step:
            step.set_cost(self._last_decision.cost_usd)
            try:
                result = await self._inner.call_tool(
                    tool_name, parameters,
                )
            except MCPToolError as e:
                step.set_error(str(e))
                return {"success": False, "error": str(e)}
            if result["success"]:
                step.set_response(result.get("result", {}))
            else:
                step.set_error(result.get("error", "unknown error"))
            return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_guided_context(response: OptimalPathResponse) -> str:
    if response.mode != "guided" or not response.path:
        return ""

    numbered = "\n".join(
        f"  {i}. {tool}" for i, tool in enumerate(response.path, 1)
    )
    parts = [
        "RECOMMENDED PATH: This tool sequence has been validated"
        " on similar tasks and is highly likely to succeed:",
        numbered,
    ]
    if (
        response.success_rate is not None
        and response.execution_count is not None
    ):
        parts.append(
            f"This sequence achieved a {response.success_rate:.0%}"
            f" success rate across"
            f" {response.execution_count} previous runs."
        )
    parts.append(
        "Follow this sequence closely. Skip any tool that"
        " already shows [SUCCESS] in your execution history."
        " If a step fails or returns unexpected results,"
        " adapt as needed — but prefer returning to this"
        " sequence once the issue is resolved."
    )
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run order fulfillment demo scenarios",
    )
    parser.add_argument(
        "--rounds", type=int, default=3,
        help="Number of rounds to run (default: 3)",
    )
    parser.add_argument(
        "--collector-url", type=str, default="http://localhost:9000",
        help="Collector service URL (default: http://localhost:9000)",
    )
    parser.add_argument(
        "--mcp-url", type=str, default="http://localhost:8001",
        help="Fulfillment MCP server URL (default: http://localhost:8001)",
    )
    parser.add_argument(
        "--payments-url", type=str, default="http://localhost:8002",
        help="Payments MCP server URL (default: http://localhost:8002)",
    )
    parser.add_argument(
        "--notifications-url", type=str, default="http://localhost:8003",
        help="Notifications MCP server URL (default: http://localhost:8003)",
    )
    parser.add_argument(
        "--risk-url", type=str, default="http://localhost:8004",
        help="Risk MCP server URL (default: http://localhost:8004)",
    )
    parser.add_argument(
        "--promotions-url", type=str, default="http://localhost:8005",
        help="Promotions MCP server URL (default: http://localhost:8005)",
    )
    parser.add_argument(
        "--inventory-url", type=str, default="http://localhost:8006",
        help="Inventory MCP server URL (default: http://localhost:8006)",
    )
    parser.add_argument(
        "--model", type=str, default="gemini/gemini-2.5-flash-lite",
        help="LLM model (default: gemini/gemini-2.5-flash-lite)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

async def run_scenario(
    scenario: Scenario,
    round_number: int,
    mcp_client: CompositeMCPClient,
    reasoning_engine: ReasoningEngine,
    optimizer: WorkflowOptimizer,
    llm_model: str,
) -> ScenarioResult:
    """Run a single scenario with tracing and verification."""
    log = get_logger("fulfillment_runner")
    log.info(
        "scenario_start",
        round=round_number,
        order=scenario.order_id,
        type=scenario.workflow_type,
    )

    last_decision = LastDecision()
    tracing_reasoning = TracingReasoningEngine(
        reasoning_engine, last_decision,
    )
    tracing_mcp = TracingMCPClient(
        mcp_client, last_decision, llm_model,
    )

    guidance = await optimizer.get_optimal_path(
        scenario.task_description,
    )
    mode = guidance.mode
    context = build_guided_context(guidance)

    if mode == "guided":
        log.info(
            "guided_mode",
            order=scenario.order_id,
            path=guidance.path,
        )

    agent = Agent(
        name="FulfilmentAgent",
        role="order_fulfilment",
        reasoning_engine=tracing_reasoning,
        mcp_client=tracing_mcp,
    )

    start = time.perf_counter()

    async with optimizer.trace(
        scenario.task_description,
        agent_name="FulfilmentAgent",
        agent_role="order_fulfilment",
    ) as trace:
        trace.emit_mode(mode)
        tracing_mcp.set_trace(trace)
        try:
            result = await agent.execute(
                scenario.task_description, context=context,
            )
            success = result["success"]
            steps = result.get("steps", 0)
            history = result.get("history", [])
        except LoopDetectedError as e:
            log.warning(
                "loop_detected",
                order=scenario.order_id,
                error=str(e),
            )
            success = False
            steps = len(agent.action_history)
            history = agent.action_history
        finally:
            tracing_mcp.set_trace(None)

        verification = await verify_outcome(scenario, mcp_client)
        if not verification.passed:
            trace.mark_failed(
                "; ".join(verification.errors)
                if verification.errors else "verification failed",
            )

    duration_ms = (time.perf_counter() - start) * 1000
    tool_sequence = [
        h["action"] for h in history if h.get("action")
    ]

    status_str = "PASS" if verification.passed else "FAIL"
    log.info(
        "scenario_complete",
        order=scenario.order_id,
        type=scenario.workflow_type,
        mode=mode,
        agent_success=success,
        verified=status_str,
        steps=steps,
        duration_ms=round(duration_ms),
        tools=" -> ".join(tool_sequence),
        errors=verification.errors if verification.errors else None,
    )

    return ScenarioResult(
        scenario=scenario,
        round_number=round_number,
        mode=mode,
        success=verification.passed,
        verified=verification.passed,
        steps=steps,
        duration_ms=duration_ms,
        tool_sequence=tool_sequence,
        workflow_id=trace.workflow_id,
        confidence=guidance.confidence,
        verification=verification,
        total_prompt_tokens=tracing_reasoning.total_prompt_tokens,
        total_completion_tokens=(
            tracing_reasoning.total_completion_tokens
        ),
    )


async def run_round(
    round_number: int,
    total_rounds: int,
    scenarios: list[Scenario],
    mcp_client: CompositeMCPClient,
    reasoning_engine: ReasoningEngine,
    optimizer: WorkflowOptimizer,
    llm_model: str,
) -> list[ScenarioResult]:
    """Run all scenarios for one round sequentially."""
    log = get_logger("fulfillment_runner")
    log.info(
        "round_start",
        round=round_number,
        total_rounds=total_rounds,
    )

    await mcp_client.reset_state()

    shuffled = list(scenarios)
    random.shuffle(shuffled)

    results: list[ScenarioResult] = []
    for scenario in shuffled:
        result = await run_scenario(
            scenario, round_number, mcp_client,
            reasoning_engine, optimizer, llm_model,
        )
        results.append(result)

    return results


def log_round_summary(
    round_number: int, results: list[ScenarioResult],
) -> None:
    log = get_logger("fulfillment_runner")
    total = len(results)
    if total == 0:
        return

    successes = sum(1 for r in results if r.success)
    verified = sum(1 for r in results if r.verified)
    avg_steps = sum(r.steps for r in results) / total
    guided_count = sum(1 for r in results if r.mode == "guided")

    log.info(
        "round_summary",
        round=round_number,
        agent_success=f"{successes}/{total}",
        verified=f"{verified}/{total}",
        avg_steps=round(avg_steps, 1),
        guided=guided_count,
        exploration=total - guided_count,
    )


def log_final_summary(all_results: list[ScenarioResult]) -> None:
    log = get_logger("fulfillment_runner")
    if not all_results:
        return

    total = len(all_results)
    successes = sum(1 for r in all_results if r.success)
    verified = sum(1 for r in all_results if r.verified)
    guided = sum(1 for r in all_results if r.mode == "guided")

    log.info(
        "final_summary",
        total_workflows=total,
        agent_success=f"{successes}/{total}",
        verified_correct=f"{verified}/{total}",
        guided_count=guided,
        exploration_count=total - guided,
    )

    failed = [r for r in all_results if not r.verified]
    if failed:
        log.warning(
            "verification_failures",
            count=len(failed),
            orders=[r.scenario.order_id for r in failed],
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    load_dotenv()
    args = parse_args()

    init_logging(LoggingConfig())
    log = get_logger("fulfillment_runner")

    log.info(
        "demo_start",
        rounds=args.rounds,
        scenarios=len(SCENARIOS),
        collector_url=args.collector_url,
    )

    reasoning_engine = ReasoningEngine(model=args.model)

    mcp_client = CompositeMCPClient({
        "fulfillment": MCPClient(
            server_url=args.mcp_url, timeout=30, max_retries=2,
        ),
        "payments": MCPClient(
            server_url=args.payments_url, timeout=30, max_retries=2,
        ),
        "notifications": MCPClient(
            server_url=args.notifications_url, timeout=30, max_retries=2,
        ),
        "risk": MCPClient(
            server_url=args.risk_url, timeout=30, max_retries=2,
        ),
        "promotions": MCPClient(
            server_url=args.promotions_url, timeout=30, max_retries=2,
        ),
        "inventory": MCPClient(
            server_url=args.inventory_url, timeout=30, max_retries=2,
        ),
    })

    if not await mcp_client.connect():
        log.error("mcp_connection_failed")
        return

    log.info(
        "mcp_connected",
        total_tools=len(mcp_client.get_tool_names()),
        tools=mcp_client.get_tool_names(),
    )

    optimizer = WorkflowOptimizer(
        endpoint=args.collector_url,
        agent_name="FulfilmentAgent",
        agent_role="order_fulfilment",
    )

    try:
        async with optimizer:
            all_results: list[ScenarioResult] = []

            for round_num in range(1, args.rounds + 1):
                results = await run_round(
                    round_num, args.rounds, SCENARIOS,
                    mcp_client, reasoning_engine,
                    optimizer, args.model,
                )
                all_results.extend(results)
                log_round_summary(round_num, results)

            log_final_summary(all_results)
    finally:
        await mcp_client.close()
        log.info("demo_complete")


if __name__ == "__main__":
    asyncio.run(main())

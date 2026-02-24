"""Tests for demo_runner module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from workflow_optimizer.models import OptimalPathResponse

from demo_runner import (
    SCENARIOS,
    LastDecision,
    ScenarioResult,
    TracingMCPClient,
    TracingReasoningEngine,
    build_guided_context,
    parse_args,
)

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------


class TestScenarioDefinitions:
    def test_ten_scenarios_defined(self) -> None:
        assert len(SCENARIOS) == 10

    def test_all_scenarios_have_required_fields(self) -> None:
        valid_types = {
            "refund_request", "order_inquiry", "complaint",
            "product_support", "warranty_claim", "shipping_inquiry",
            "cancellation",
        }
        for s in SCENARIOS:
            assert s.ticket_id.startswith("T-")
            assert s.order_id.startswith("ORD-")
            assert s.customer_id.startswith("C-")
            assert s.workflow_type in valid_types
            assert len(s.task_description) > 20
            assert s.expected_steps >= 4

    def test_unique_ticket_ids(self) -> None:
        ids = [s.ticket_id for s in SCENARIOS]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# build_guided_context
# ---------------------------------------------------------------------------


class TestBuildGuidedContext:
    def test_exploration_returns_empty(self) -> None:
        response = OptimalPathResponse(mode="exploration")
        assert build_guided_context(response) == ""

    def test_guided_no_path_returns_empty(self) -> None:
        response = OptimalPathResponse(mode="guided", path=None)
        assert build_guided_context(response) == ""

    def test_guided_with_path(self) -> None:
        response = OptimalPathResponse(
            mode="guided",
            path=["check_ticket", "get_order", "process_refund"],
            confidence=0.87,
            success_rate=0.95,
            execution_count=20,
            avg_duration_ms=2500.0,
            avg_steps=3.0,
        )
        result = build_guided_context(response)
        assert "OPTIMIZATION HINT" in result
        assert "1. check_ticket" in result
        assert "2. get_order" in result
        assert "3. process_refund" in result
        assert "95%" in result
        assert "20 previous runs" in result
        assert "Skip any tool" in result

    def test_guided_partial_metrics(self) -> None:
        response = OptimalPathResponse(
            mode="guided",
            path=["tool_a", "tool_b"],
        )
        result = build_guided_context(response)
        assert "OPTIMIZATION HINT" in result
        assert "1. tool_a" in result
        assert "2. tool_b" in result


# ---------------------------------------------------------------------------
# TracingReasoningEngine
# ---------------------------------------------------------------------------


class TestTracingReasoningEngine:
    @pytest.fixture
    def setup(self) -> tuple[AsyncMock, LastDecision, TracingReasoningEngine]:
        inner = AsyncMock()
        inner.reason = AsyncMock(return_value={
            "reasoning": "Check the ticket first",
            "action": "check_ticket",
            "parameters": {"ticket_id": "T-1001"},
            "prompt_tokens": 150,
            "completion_tokens": 40,
        })
        last = LastDecision()
        engine = TracingReasoningEngine(inner, last)
        return inner, last, engine

    @pytest.mark.asyncio
    async def test_delegates_to_inner(self, setup: tuple) -> None:
        inner, _, engine = setup
        result = await engine.reason("task", "ctx", "tools")
        inner.reason.assert_called_once_with("task", "ctx", "tools", None)
        assert result["action"] == "check_ticket"

    @pytest.mark.asyncio
    async def test_updates_last_decision(self, setup: tuple) -> None:
        _, last, engine = setup
        await engine.reason("task", "ctx", "tools")
        assert last.reasoning == "Check the ticket first"
        assert last.prompt_tokens == 150
        assert last.completion_tokens == 40

    @pytest.mark.asyncio
    async def test_accumulates_totals(self, setup: tuple) -> None:
        _, _, engine = setup
        await engine.reason("task1", "", "tools")
        await engine.reason("task2", "", "tools")
        assert engine.total_prompt_tokens == 300
        assert engine.total_completion_tokens == 80

    @pytest.mark.asyncio
    async def test_reset_totals(self, setup: tuple) -> None:
        _, _, engine = setup
        await engine.reason("task", "", "tools")
        engine.reset_totals()
        assert engine.total_prompt_tokens == 0
        assert engine.total_completion_tokens == 0


# ---------------------------------------------------------------------------
# TracingMCPClient
# ---------------------------------------------------------------------------


class TestTracingMCPClient:
    @pytest.fixture
    def setup(self) -> tuple[AsyncMock, LastDecision, TracingMCPClient]:
        inner = AsyncMock()
        inner.connect = AsyncMock(return_value=True)
        inner.close = AsyncMock()
        inner.get_tools_documentation = MagicMock(return_value="tools doc")
        inner.call_tool = AsyncMock(return_value={
            "success": True,
            "result": {"status": "open"},
        })
        last = LastDecision(reasoning="test reasoning", prompt_tokens=10, completion_tokens=5)
        client = TracingMCPClient(inner, last, "gpt-4")
        return inner, last, client

    @pytest.mark.asyncio
    async def test_delegates_connect(self, setup: tuple) -> None:
        inner, _, client = setup
        result = await client.connect()
        assert result is True
        inner.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegates_close(self, setup: tuple) -> None:
        inner, _, client = setup
        await client.close()
        inner.close.assert_called_once()

    def test_delegates_tools_documentation(self, setup: tuple) -> None:
        _, _, client = setup
        assert client.get_tools_documentation() == "tools doc"

    @pytest.mark.asyncio
    async def test_call_tool_no_trace_delegates(self, setup: tuple) -> None:
        inner, _, client = setup
        result = await client.call_tool("check_ticket", {"id": "T-1"})
        inner.call_tool.assert_called_once_with("check_ticket", {"id": "T-1"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_call_tool_with_trace_records_step(self, setup: tuple) -> None:
        inner, _, client = setup

        mock_step = MagicMock()
        mock_step.__enter__ = MagicMock(return_value=mock_step)
        mock_step.__exit__ = MagicMock(return_value=False)

        mock_trace = MagicMock()
        mock_trace.step = MagicMock(return_value=mock_step)

        client.set_trace(mock_trace)
        result = await client.call_tool("check_ticket", {"id": "T-1"})

        mock_trace.step.assert_called_once()
        call_kwargs = mock_trace.step.call_args
        assert call_kwargs[0][0] == "check_ticket"
        assert call_kwargs[1]["llm_model"] == "gpt-4"
        mock_step.set_response.assert_called_once_with({"status": "open"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_call_tool_with_trace_records_error(self, setup: tuple) -> None:
        inner, _, client = setup
        inner.call_tool = AsyncMock(return_value={
            "success": False,
            "error": "tool not found",
        })

        mock_step = MagicMock()
        mock_step.__enter__ = MagicMock(return_value=mock_step)
        mock_step.__exit__ = MagicMock(return_value=False)

        mock_trace = MagicMock()
        mock_trace.step = MagicMock(return_value=mock_step)

        client.set_trace(mock_trace)
        result = await client.call_tool("unknown_tool", {})

        mock_step.set_error.assert_called_once_with("tool not found")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_defaults(self) -> None:
        with patch("sys.argv", ["demo_runner.py"]):
            args = parse_args()
        assert args.rounds == 3
        assert args.collector_url == "http://localhost:9000"

    def test_custom_values(self) -> None:
        with patch("sys.argv", ["demo_runner.py", "--rounds", "5", "--collector-url", "http://example:9000"]):
            args = parse_args()
        assert args.rounds == 5
        assert args.collector_url == "http://example:9000"


# ---------------------------------------------------------------------------
# ScenarioResult
# ---------------------------------------------------------------------------


class TestScenarioResult:
    def test_creation(self) -> None:
        result = ScenarioResult(
            scenario=SCENARIOS[0],
            round_number=1,
            mode="exploration",
            success=True,
            steps=6,
            duration_ms=3000.0,
            tool_sequence=["check_ticket", "get_order"],
            workflow_id="abc-123",
            confidence=None,
        )
        assert result.mode == "exploration"
        assert result.success is True
        assert result.total_prompt_tokens == 0
        assert result.total_completion_tokens == 0

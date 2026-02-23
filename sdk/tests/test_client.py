"""Tests for the WorkflowOptimizer client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from workflow_optimizer.client import WorkflowOptimizer
from workflow_optimizer.models import OptimalPathResponse
from workflow_optimizer.trace import TraceContext


class TestClientLifecycle:
    async def test_context_manager_opens_and_closes(self) -> None:
        with patch.object(
            WorkflowOptimizer, "open", new_callable=AsyncMock
        ) as mock_open, patch.object(
            WorkflowOptimizer, "close", new_callable=AsyncMock
        ) as mock_close:
            async with WorkflowOptimizer() as _optimizer:
                mock_open.assert_called_once()
            mock_close.assert_called_once()

    async def test_explicit_open_close(self) -> None:
        optimizer = WorkflowOptimizer()
        with patch.object(
            optimizer._transport, "open", new_callable=AsyncMock
        ) as mock_open, patch.object(
            optimizer._transport, "close", new_callable=AsyncMock
        ) as mock_close:
            await optimizer.open()
            mock_open.assert_called_once()
            await optimizer.close()
            mock_close.assert_called_once()


class TestTraceCreation:
    async def test_trace_returns_trace_context(self) -> None:
        optimizer = WorkflowOptimizer()
        optimizer._transport._opened = True
        trace = optimizer.trace("Handle refund")
        assert isinstance(trace, TraceContext)

    async def test_agent_defaults_cascade(self) -> None:
        optimizer = WorkflowOptimizer(agent_name="main-agent", agent_role="worker")
        optimizer._transport._opened = True
        trace = optimizer.trace("Handle refund")
        assert trace._agent_name == "main-agent"
        assert trace._agent_role == "worker"

    async def test_trace_override_agent(self) -> None:
        optimizer = WorkflowOptimizer(agent_name="main-agent")
        optimizer._transport._opened = True
        trace = optimizer.trace("Handle refund", agent_name="override-agent")
        assert trace._agent_name == "override-agent"

    async def test_agent_properties(self) -> None:
        optimizer = WorkflowOptimizer(agent_name="test", agent_role="tester")
        assert optimizer.agent_name == "test"
        assert optimizer.agent_role == "tester"


class TestOptimalPath:
    async def test_get_optimal_path_auto_opens(self) -> None:
        optimizer = WorkflowOptimizer()
        with patch.object(
            optimizer._transport, "open", new_callable=AsyncMock
        ) as mock_open, patch.object(
            optimizer._transport,
            "get_optimal_path",
            new_callable=AsyncMock,
            return_value=OptimalPathResponse(mode="exploration"),
        ):
            result = await optimizer.get_optimal_path("Handle refund")
            mock_open.assert_called_once()
            assert result.mode == "exploration"

    async def test_get_optimal_path_delegates(self) -> None:
        optimizer = WorkflowOptimizer()
        optimizer._transport._opened = True
        expected = OptimalPathResponse(
            mode="guided",
            path=["check_ticket", "get_order"],
            confidence=0.9,
        )
        with patch.object(
            optimizer._transport,
            "get_optimal_path",
            new_callable=AsyncMock,
            return_value=expected,
        ):
            result = await optimizer.get_optimal_path("Handle refund")
            assert result.mode == "guided"
            assert result.path == ["check_ticket", "get_order"]


class TestDefaultConfig:
    def test_default_endpoint(self) -> None:
        optimizer = WorkflowOptimizer()
        assert optimizer._transport._endpoint == "http://localhost:9000"

    def test_custom_endpoint(self) -> None:
        optimizer = WorkflowOptimizer(endpoint="http://custom:8080/")
        assert optimizer._transport._endpoint == "http://custom:8080"

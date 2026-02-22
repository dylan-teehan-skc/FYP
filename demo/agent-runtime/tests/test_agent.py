"""Tests for Agent class."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent.agent import Agent
from utils.exceptions import LoopDetectedError


class TestAgent:
    """Tests for Agent execution and loop detection."""

    @pytest.fixture
    def agent(
        self, mock_reasoning_engine: AsyncMock, mock_mcp_client: AsyncMock
    ) -> Agent:
        """Create agent with mocked dependencies."""
        return Agent(
            name="TestAgent",
            role="test",
            reasoning_engine=mock_reasoning_engine,
            mcp_client=mock_mcp_client,
            loop_threshold=3,
            loop_window=5,
        )

    @pytest.mark.asyncio
    async def test_execute_simple_task(
        self,
        agent: Agent,
        mock_reasoning_engine: AsyncMock,
        mock_mcp_client: AsyncMock,
        sample_reasoning_response: dict[str, Any],
        complete_reasoning_response: dict[str, Any],
        sample_tool_response: dict[str, Any],
    ) -> None:
        """Test agent completes a simple task."""
        mock_reasoning_engine.reason = AsyncMock(
            side_effect=[sample_reasoning_response, complete_reasoning_response]
        )
        mock_mcp_client.call_tool = AsyncMock(return_value=sample_tool_response)

        result = await agent.execute("Test task")

        assert result["success"] is True
        assert result["steps"] == 2
        assert len(result["history"]) == 1
        mock_mcp_client.call_tool.assert_called_once_with(
            "get_ticket", {"ticket_id": "T-12345"}
        )

    @pytest.mark.asyncio
    async def test_execute_immediate_complete(
        self,
        agent: Agent,
        mock_reasoning_engine: AsyncMock,
        complete_reasoning_response: dict[str, Any],
    ) -> None:
        """Test agent that completes immediately."""
        mock_reasoning_engine.reason = AsyncMock(return_value=complete_reasoning_response)

        result = await agent.execute("Simple task")

        assert result["success"] is True
        assert result["steps"] == 1
        assert len(result["history"]) == 0

    @pytest.mark.asyncio
    async def test_execute_with_tool_error(
        self,
        agent: Agent,
        mock_reasoning_engine: AsyncMock,
        mock_mcp_client: AsyncMock,
        sample_reasoning_response: dict[str, Any],
        complete_reasoning_response: dict[str, Any],
    ) -> None:
        """Test agent handles tool errors gracefully."""
        mock_reasoning_engine.reason = AsyncMock(
            side_effect=[sample_reasoning_response, complete_reasoning_response]
        )
        mock_mcp_client.call_tool = AsyncMock(
            return_value={"success": False, "error": "Tool not found"}
        )

        result = await agent.execute("Test task")

        assert result["success"] is True
        assert result["history"][0]["success"] is False
        assert result["history"][0]["result"] == "Tool not found"

    @pytest.mark.asyncio
    async def test_loop_detection(
        self,
        agent: Agent,
        mock_reasoning_engine: AsyncMock,
        mock_mcp_client: AsyncMock,
        sample_tool_response: dict[str, Any],
    ) -> None:
        """Test agent detects and raises on loops."""
        looping_response = {
            "reasoning": "Keep trying",
            "action": "get_ticket",
            "parameters": {"ticket_id": "T-12345"},
            "prompt_tokens": 50,
            "completion_tokens": 25,
        }
        mock_reasoning_engine.reason = AsyncMock(return_value=looping_response)
        mock_mcp_client.call_tool = AsyncMock(return_value=sample_tool_response)

        with pytest.raises(LoopDetectedError) as exc_info:
            await agent.execute("Looping task")

        assert "stuck in loop" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_on_none_action(
        self,
        agent: Agent,
        mock_reasoning_engine: AsyncMock,
        complete_reasoning_response: dict[str, Any],
    ) -> None:
        """Test agent retries when action is None."""
        none_response = {
            "reasoning": "Thinking...",
            "action": None,
            "parameters": {},
            "prompt_tokens": 50,
            "completion_tokens": 20,
        }
        mock_reasoning_engine.reason = AsyncMock(
            side_effect=[none_response, none_response, complete_reasoning_response]
        )

        result = await agent.execute("Task requiring retries")

        assert result["success"] is True
        assert result["steps"] == 3
        assert mock_reasoning_engine.reason.call_count == 3


class TestLoopDetection:
    """Tests for loop detection algorithm."""

    @pytest.fixture
    def agent(
        self, mock_reasoning_engine: AsyncMock, mock_mcp_client: AsyncMock
    ) -> Agent:
        """Create agent for loop detection tests."""
        return Agent(
            name="LoopTestAgent",
            role="test",
            reasoning_engine=mock_reasoning_engine,
            mcp_client=mock_mcp_client,
            loop_threshold=3,
            loop_window=5,
        )

    def test_no_loop_empty_history(self, agent: Agent) -> None:
        """No loop when history is empty."""
        assert agent._is_looping() is False

    def test_no_loop_varied_actions(self, agent: Agent) -> None:
        """No loop when actions are varied."""
        agent.action_history = [
            {"action": "a", "parameters": {}, "result": None, "success": True},
            {"action": "b", "parameters": {}, "result": None, "success": True},
            {"action": "c", "parameters": {}, "result": None, "success": True},
        ]
        assert agent._is_looping() is False

    def test_loop_detected_same_action(self, agent: Agent) -> None:
        """Loop detected when same action repeated."""
        agent.action_history = [
            {"action": "a", "parameters": {}, "result": None, "success": True},
            {"action": "a", "parameters": {}, "result": None, "success": True},
            {"action": "a", "parameters": {}, "result": None, "success": True},
        ]
        assert agent._is_looping() is True

    def test_loop_window_respected(self, agent: Agent) -> None:
        """Loop detection only looks at recent window."""
        agent.action_history = [
            {"action": "a", "parameters": {}, "result": None, "success": True},
            {"action": "a", "parameters": {}, "result": None, "success": True},
            {"action": "a", "parameters": {}, "result": None, "success": True},
            {"action": "b", "parameters": {}, "result": None, "success": True},
            {"action": "c", "parameters": {}, "result": None, "success": True},
            {"action": "d", "parameters": {}, "result": None, "success": True},
        ]
        # Only last 5 actions are checked, "a" appears only twice in window
        assert agent._is_looping() is False

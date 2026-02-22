"""Pytest fixtures for agent-runtime tests."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from utils.config import AgentConfig, AppConfig, LLMConfig, LoggingConfig, MCPConfig


@pytest.fixture
def sample_config() -> AppConfig:
    """Valid AppConfig for testing."""
    return AppConfig(
        llm=LLMConfig(model="gpt-4"),
        logging=LoggingConfig(level="DEBUG"),
        mcp=MCPConfig(server_url="http://localhost:8000"),
        agent=AgentConfig(loop_detection_threshold=3, loop_detection_window=5),
    )


@pytest.fixture
def mock_mcp_client() -> AsyncMock:
    """Mock MCP client for testing agents."""
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.get_tool_names = lambda: ["get_ticket", "process_refund", "send_notification"]
    client.get_tools_documentation = lambda: """Available tools:
- get_ticket: Retrieve ticket information
    ticket_id: string (required)
- process_refund: Process a refund for a ticket
    ticket_id: string (required)
    amount: number (required)
- send_notification: Send notification to customer
    customer_id: string (required)
    message: string (required)"""
    client.available_tools = [
        {
            "name": "get_ticket",
            "description": "Retrieve ticket information",
            "input_schema": {
                "type": "object",
                "properties": {"ticket_id": {"type": "string"}},
                "required": ["ticket_id"],
            },
        },
        {
            "name": "process_refund",
            "description": "Process a refund",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["ticket_id", "amount"],
            },
        },
    ]
    return client


@pytest.fixture
def mock_reasoning_engine() -> AsyncMock:
    """Mock reasoning engine for testing agents."""
    engine = AsyncMock()
    return engine


@pytest.fixture
def sample_tool_response() -> dict[str, Any]:
    """Sample successful tool response."""
    return {
        "success": True,
        "result": {"ticket_id": "T-12345", "status": "open", "amount": 50.00},
    }


@pytest.fixture
def sample_reasoning_response() -> dict[str, Any]:
    """Sample reasoning engine response."""
    return {
        "reasoning": "I need to get the ticket information first.",
        "action": "get_ticket",
        "parameters": {"ticket_id": "T-12345"},
        "prompt_tokens": 100,
        "completion_tokens": 50,
    }


@pytest.fixture
def complete_reasoning_response() -> dict[str, Any]:
    """Reasoning response indicating task completion."""
    return {
        "reasoning": "The task has been completed successfully.",
        "action": "complete",
        "parameters": {},
        "prompt_tokens": 100,
        "completion_tokens": 30,
    }

"""Tests for MCP client."""

import pytest
from aioresponses import aioresponses

from mcp.client import MCPClient
from utils.exceptions import MCPConnectionError, MCPToolError


class TestMCPClient:
    """Tests for MCPClient HTTP operations."""

    @pytest.fixture
    def client(self) -> MCPClient:
        """Create MCP client for testing."""
        return MCPClient(
            server_url="http://localhost:8000",
            timeout=5,
            max_retries=2,
            retry_delay=0,
        )

    @pytest.mark.asyncio
    async def test_connect_success(self, client: MCPClient) -> None:
        """Test successful connection to MCP server."""
        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8000/tools/list",
                payload={
                    "tools": [
                        {"name": "test_tool", "description": "A test tool"},
                    ]
                },
            )

            result = await client.connect()

            assert result is True
            assert len(client.available_tools) == 1
            assert client.available_tools[0]["name"] == "test_tool"

        await client.close()

    @pytest.mark.asyncio
    async def test_connect_failure(self, client: MCPClient) -> None:
        """Test connection failure handling."""
        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8000/tools/list",
                status=500,
            )

            result = await client.connect()

            assert result is False
            assert len(client.available_tools) == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_call_tool_success(self, client: MCPClient) -> None:
        """Test successful tool call."""
        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8000/tools/list",
                payload={"tools": [{"name": "get_data", "description": "Get data"}]},
            )
            mocked.post(
                "http://localhost:8000/tools/call",
                payload={"data": "test_result"},
            )

            await client.connect()
            result = await client.call_tool("get_data", {"id": "123"})

            assert result["success"] is True
            assert result["result"] == {"data": "test_result"}

        await client.close()

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, client: MCPClient) -> None:
        """Test calling non-existent tool."""
        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8000/tools/list",
                payload={"tools": [{"name": "existing_tool", "description": ""}]},
            )

            await client.connect()

            with pytest.raises(MCPToolError) as exc_info:
                await client.call_tool("nonexistent_tool", {})

            assert "not found" in str(exc_info.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, client: MCPClient) -> None:
        """Test calling tool when not connected."""
        with pytest.raises(MCPConnectionError) as exc_info:
            await client.call_tool("some_tool", {})

        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_retry_on_failure(self, client: MCPClient) -> None:
        """Test tool call retries on transient failures."""
        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8000/tools/list",
                payload={"tools": [{"name": "flaky_tool", "description": ""}]},
            )
            mocked.post("http://localhost:8000/tools/call", status=500)
            mocked.post(
                "http://localhost:8000/tools/call",
                payload={"result": "success"},
            )

            await client.connect()
            result = await client.call_tool("flaky_tool", {})

            assert result["success"] is True

        await client.close()

    @pytest.mark.asyncio
    async def test_call_tool_max_retries_exceeded(self, client: MCPClient) -> None:
        """Test tool call fails after max retries."""
        with aioresponses() as mocked:
            mocked.get(
                "http://localhost:8000/tools/list",
                payload={"tools": [{"name": "failing_tool", "description": ""}]},
            )
            mocked.post("http://localhost:8000/tools/call", status=500)
            mocked.post("http://localhost:8000/tools/call", status=500)

            await client.connect()
            result = await client.call_tool("failing_tool", {})

            assert result["success"] is False
            assert "Failed after" in result["error"]

        await client.close()

    def test_get_tool_names(self, client: MCPClient) -> None:
        """Test getting tool names."""
        client.available_tools = [
            {"name": "tool_a", "description": ""},
            {"name": "tool_b", "description": ""},
        ]

        names = client.get_tool_names()

        assert names == ["tool_a", "tool_b"]

    def test_get_tool_schema_found(self, client: MCPClient) -> None:
        """Test getting schema for existing tool."""
        client.available_tools = [
            {
                "name": "my_tool",
                "description": "Does something",
                "input_schema": {"type": "object"},
            },
        ]

        schema = client.get_tool_schema("my_tool")

        assert schema is not None
        assert schema["name"] == "my_tool"

    def test_get_tool_schema_not_found(self, client: MCPClient) -> None:
        """Test getting schema for non-existent tool."""
        client.available_tools = []

        schema = client.get_tool_schema("unknown")

        assert schema is None

    def test_get_tools_documentation_empty(self, client: MCPClient) -> None:
        """Test documentation when no tools available."""
        client.available_tools = []

        doc = client.get_tools_documentation()

        assert doc == "No tools available."

    def test_get_tools_documentation(self, client: MCPClient) -> None:
        """Test tools documentation formatting."""
        client.available_tools = [
            {
                "name": "search",
                "description": "Search for items",
                "input_schema": {
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
        ]

        doc = client.get_tools_documentation()

        assert "search: Search for items" in doc
        assert "query: string (required)" in doc
        assert "limit: integer" in doc

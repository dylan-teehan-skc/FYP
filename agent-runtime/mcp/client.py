"""MCP client for tool server communication."""

import asyncio
from typing import Any

import aiohttp

from utils.exceptions import MCPConnectionError, MCPToolError
from utils.logger import get_logger


class MCPClient:
    """Async client for communicating with MCP tool servers."""

    def __init__(
        self,
        server_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.available_tools: list[dict[str, Any]] = []
        self._session: aiohttp.ClientSession | None = None
        self.log = get_logger("MCPClient")

    async def connect(self) -> bool:
        """Fetch available tools from the MCP server."""
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        try:
            async with self._session.get(f"{self.server_url}/tools/list") as response:
                response.raise_for_status()
                data = await response.json()
                self.available_tools = data.get("tools", [])
                self.log.info("connected", tool_count=len(self.available_tools))
                return True
        except aiohttp.ClientError as e:
            self.log.error("connection_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    def get_tool_names(self) -> list[str]:
        """Get list of available tool names."""
        return [tool["name"] for tool in self.available_tools]

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Get the schema for a specific tool."""
        for tool in self.available_tools:
            if tool["name"] == tool_name:
                return tool
        return None

    async def call_tool(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        if not self._session:
            raise MCPConnectionError("Not connected to MCP server")

        if tool_name not in self.get_tool_names():
            raise MCPToolError(f"Tool '{tool_name}' not found")

        last_error: str | None = None
        for attempt in range(self.max_retries):
            try:
                async with self._session.post(
                    f"{self.server_url}/tools/call",
                    json={"name": tool_name, "arguments": parameters},
                ) as response:
                    response.raise_for_status()
                    self.log.info("tool_called", tool=tool_name)
                    result = await response.json()
                    return {"success": True, "result": result}
            except aiohttp.ClientError as e:
                last_error = str(e)
                self.log.warning("tool_call_retry", tool=tool_name, attempt=attempt + 1)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        return {"success": False, "error": f"Failed after {self.max_retries} attempts: {last_error}"}

    def get_tools_documentation(self) -> str:
        """Format tools for inclusion in agent prompts."""
        if not self.available_tools:
            return "No tools available."

        lines = ["Available tools:"]
        for tool in self.available_tools:
            lines.append(f"\n- {tool['name']}: {tool.get('description', '')}")
            if "input_schema" in tool:
                props = tool["input_schema"].get("properties", {})
                required = tool["input_schema"].get("required", [])
                for name, schema in props.items():
                    req = " (required)" if name in required else ""
                    lines.append(f"    {name}: {schema.get('type', 'any')}{req}")

        return "\n".join(lines)

"""Composite MCP client that aggregates multiple MCP servers."""

from __future__ import annotations

from typing import Any

from mcp.client import MCPClient
from utils.exceptions import MCPToolError
from utils.logger import get_logger


class CompositeMCPClient:
    """Aggregates multiple MCP servers into a single tool namespace."""

    def __init__(self, clients: dict[str, MCPClient]) -> None:
        self._clients = clients
        self._tool_map: dict[str, MCPClient] = {}
        self._primary_name: str | None = None
        self.available_tools: list[dict[str, Any]] = []
        self.log = get_logger("CompositeMCPClient")

    @property
    def primary(self) -> MCPClient:
        """The primary client (fulfillment server) that owns the shared DB."""
        if self._primary_name and self._primary_name in self._clients:
            return self._clients[self._primary_name]
        return next(iter(self._clients.values()))

    async def connect(self) -> bool:
        for name, client in self._clients.items():
            if not await client.connect():
                self.log.error("connect_failed", server=name)
                return False
            if self._primary_name is None:
                self._primary_name = name
            for tool in client.available_tools:
                self._tool_map[tool["name"]] = client
                self.available_tools.append(tool)
            self.log.info(
                "server_connected",
                server=name,
                tools=[t["name"] for t in client.available_tools],
            )
        self.log.info(
            "all_connected",
            total_tools=len(self._tool_map),
        )
        return True

    async def call_tool(
        self, tool_name: str, parameters: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._tool_map.get(tool_name)
        if not client:
            raise MCPToolError(f"Tool '{tool_name}' not found in any server")
        return await client.call_tool(tool_name, parameters)

    def get_tool_names(self) -> list[str]:
        return list(self._tool_map.keys())

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        for tool in self.available_tools:
            if tool["name"] == tool_name:
                return tool
        return None

    def get_tools_documentation(self) -> str:
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
                    lines.append(
                        f"    {name}: {schema.get('type', 'any')}{req}"
                    )
        return "\n".join(lines)

    async def reset_state(self) -> bool:
        return await self.primary.reset_state()

    async def close(self) -> None:
        for client in self._clients.values():
            await client.close()

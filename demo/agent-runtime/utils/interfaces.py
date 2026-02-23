"""Protocol definitions for agent-runtime components."""

from typing import Any, Protocol


class ReasoningEngineProtocol(Protocol):
    """Protocol for LLM reasoning components."""

    async def reason(
        self,
        task: str,
        context: str,
        tools_doc: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate next action based on task and available tools.

        Args:
            task: The task description to accomplish.
            context: Additional context for the task.
            tools_doc: Documentation of available tools.
            history: Previous actions and results.

        Returns:
            Dict containing reasoning, action, and parameters.
        """
        ...


class MCPClientProtocol(Protocol):
    """Protocol for MCP server communication."""

    async def connect(self) -> bool:
        """Connect to MCP server and fetch available tools.

        Returns:
            True if connection successful, False otherwise.
        """
        ...

    async def call_tool(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            parameters: Tool input parameters.

        Returns:
            Tool execution result.
        """
        ...

    def get_tools_documentation(self) -> str:
        """Get formatted documentation of available tools.

        Returns:
            String documentation of all available tools.
        """
        ...

    async def close(self) -> None:
        """Close the connection to the MCP server."""
        ...


class AgentProtocol(Protocol):
    """Protocol for autonomous agents."""

    name: str
    role: str

    async def execute(self, task: str, context: str = "") -> dict[str, Any]:
        """Execute a task and return the result.

        Args:
            task: Task description to accomplish.
            context: Additional context for task execution.

        Returns:
            Dict containing success status, steps taken, and history.
        """
        ...

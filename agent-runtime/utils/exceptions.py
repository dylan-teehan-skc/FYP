"""Custom exceptions for agent-runtime."""


class AgentRuntimeError(Exception):
    """Base exception for all agent-runtime errors."""


class ConfigurationError(AgentRuntimeError):
    """Configuration loading or validation error."""


class MCPError(AgentRuntimeError):
    """Base exception for MCP-related errors."""


class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""


class MCPToolError(MCPError):
    """Tool execution failed."""


class ReasoningError(AgentRuntimeError):
    """LLM reasoning or response parsing error."""


class LoopDetectedError(AgentRuntimeError):
    """Agent detected stuck in execution loop."""


class PromptLoadError(AgentRuntimeError):
    """Failed to load prompt template."""

"""Custom exceptions for workflow-optimizer-sdk."""


class WorkflowOptimizerError(Exception):
    """Base exception for all SDK errors."""


class TransportError(WorkflowOptimizerError):
    """HTTP transport failure (collector unreachable, timeout, etc.)."""


class EventValidationError(WorkflowOptimizerError):
    """Event data failed Pydantic validation."""


class TraceStateError(WorkflowOptimizerError):
    """Invalid trace lifecycle operation (e.g., step outside active trace)."""

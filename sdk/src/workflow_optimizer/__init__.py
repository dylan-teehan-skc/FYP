"""workflow-optimizer-sdk — lightweight trace capture for AI agent workflows."""

from workflow_optimizer.client import WorkflowOptimizer
from workflow_optimizer.exceptions import (
    EventValidationError,
    TraceStateError,
    TransportError,
    WorkflowOptimizerError,
)
from workflow_optimizer.models import OptimalPathResponse, WorkflowEvent

__all__ = [
    "EventValidationError",
    "OptimalPathResponse",
    "TraceStateError",
    "TransportError",
    "WorkflowEvent",
    "WorkflowOptimizer",
    "WorkflowOptimizerError",
]

__version__ = "0.1.0"

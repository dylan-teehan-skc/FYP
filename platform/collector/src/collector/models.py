"""Pydantic v2 request/response models for the collector API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventIn(BaseModel):
    """Inbound event from the SDK (wire-compatible with SDK's WorkflowEvent)."""

    event_id: str
    workflow_id: str
    timestamp: datetime
    activity: str
    agent_name: str = ""
    agent_role: str = ""
    tool_name: str | None = None
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    tool_response: dict[str, Any] = Field(default_factory=dict)
    llm_model: str = ""
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_reasoning: str = ""
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    status: str = "success"
    error_message: str | None = None
    step_number: int = 0
    parent_event_id: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"success", "failure", "timeout", "loop_detected"}
        if v not in allowed:
            msg = f"status must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v


class BatchEventsIn(BaseModel):
    """Batch of events from SDK's POST /events/batch."""

    events: list[EventIn]


class WorkflowCompleteIn(BaseModel):
    """Request from SDK's POST /workflows/complete."""

    workflow_id: str
    task_description: str
    total_steps: int
    total_duration_ms: float
    status: str = "success"


class OptimizePathIn(BaseModel):
    """Request body for POST /optimize/path."""

    task_description: str


class OptimalPathOut(BaseModel):
    """Response for POST /optimize/path (wire-compatible with SDK's OptimalPathResponse)."""

    mode: str
    path: list[str] | None = None
    confidence: float | None = None
    avg_duration_ms: float | None = None
    avg_steps: float | None = None
    success_rate: float | None = None
    execution_count: int | None = None


class EventOut(BaseModel):
    """Event returned in trace queries."""

    event_id: str
    workflow_id: str
    timestamp: datetime
    activity: str
    agent_name: str
    agent_role: str
    tool_name: str | None
    tool_parameters: dict[str, Any]
    tool_response: dict[str, Any]
    llm_model: str
    llm_prompt_tokens: int
    llm_completion_tokens: int
    llm_reasoning: str
    duration_ms: float
    cost_usd: float
    status: str
    error_message: str | None
    step_number: int
    parent_event_id: str | None


class TraceOut(BaseModel):
    """Full workflow trace response."""

    workflow_id: str
    events: list[EventOut]
    total_events: int


class ToolStat(BaseModel):
    """Per-tool aggregate statistics."""

    tool_name: str
    call_count: int
    avg_duration_ms: float


class AnalyticsSummary(BaseModel):
    """Aggregate metrics response for GET /analytics/summary."""

    total_workflows: int
    total_events: int
    avg_duration_ms: float | None = None
    avg_steps: float | None = None
    success_rate: float | None = None
    top_tools: list[ToolStat] = Field(default_factory=list)

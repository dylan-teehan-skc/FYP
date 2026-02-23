"""Pydantic v2 event and response models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WorkflowEvent(BaseModel):
    """A single workflow execution event sent to the collector."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    activity: str

    # Multi-agent tracking
    agent_name: str = ""
    agent_role: str = ""

    # Tool call details
    tool_name: str | None = None
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    tool_response: dict[str, Any] = Field(default_factory=dict)

    # LLM metrics (optional)
    llm_model: str = ""
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_reasoning: str = ""

    # Performance metrics
    duration_ms: float = 0.0
    cost_usd: float = 0.0

    # Outcome
    status: str = "success"
    error_message: str | None = None

    # Workflow context
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

    @field_validator("activity")
    @classmethod
    def validate_activity_not_empty(cls, v: str) -> str:
        if not v.strip():
            msg = "activity must not be empty"
            raise ValueError(msg)
        return v


class OptimalPathResponse(BaseModel):
    """Response from the collector's POST /optimize/path endpoint."""

    mode: str
    path: list[str] | None = None
    confidence: float | None = None
    avg_duration_ms: float | None = None
    avg_steps: float | None = None
    success_rate: float | None = None
    execution_count: int | None = None


class WorkflowCompleteRequest(BaseModel):
    """Request body for POST /workflows/complete."""

    workflow_id: str
    task_description: str
    total_steps: int
    total_duration_ms: float
    status: str = "success"

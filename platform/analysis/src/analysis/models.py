"""Pydantic v2 domain models for the analysis engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventRecord(BaseModel):
    """A single event from the event_logs table, typed for analysis."""

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


class WorkflowTrace(BaseModel):
    """A fully reconstructed workflow trace: ordered events for one workflow_id."""

    workflow_id: str
    task_description: str = ""
    events: list[EventRecord] = Field(default_factory=list)
    tool_sequence: list[str] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    total_cost_usd: float = 0.0
    total_steps: int = 0
    success: bool = False


class GraphEdge(BaseModel):
    """A weighted edge in the execution graph."""

    source: str
    target: str
    weight: float = 0.0
    frequency: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    avg_cost_usd: float = 0.0


class ExecutionGraph(BaseModel):
    """Serializable representation of the weighted DAG."""

    task_cluster: str
    nodes: list[str] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    total_traces: int = 0


class ProcessMetrics(BaseModel):
    """PM4Py process model quality metrics."""

    fitness: float = 0.0
    precision: float = 0.0


class PatternAnomaly(BaseModel):
    """A detected anti-pattern in workflow execution."""

    pattern_type: str
    description: str
    tool_name: str = ""
    severity: str = "medium"
    evidence: dict[str, Any] = Field(default_factory=dict)


class OptimalPath(BaseModel):
    """A discovered optimal path ready to upsert into the optimal_paths table."""

    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_cluster: str
    tool_sequence: list[str] = Field(default_factory=list)
    avg_duration_ms: float = 0.0
    avg_cost_usd: float = 0.0
    avg_steps: float = 0.0
    success_rate: float = 0.0
    execution_count: int = 0
    pareto_rank: int = 0
    embedding: list[float] | None = None


class Suggestion(BaseModel):
    """A human-readable optimization recommendation."""

    suggestion_type: str
    message: str
    priority: str = "medium"
    affected_tools: list[str] = Field(default_factory=list)
    estimated_saving_ms: float = 0.0


class AnalysisResult(BaseModel):
    """Complete output of the analysis pipeline for one task cluster."""

    task_cluster: str
    traces_analyzed: int = 0
    execution_graph: ExecutionGraph | None = None
    process_metrics: ProcessMetrics | None = None
    patterns: list[PatternAnomaly] = Field(default_factory=list)
    pareto_paths: list[OptimalPath] = Field(default_factory=list)
    optimal_path: OptimalPath | None = None
    suggestions: list[Suggestion] = Field(default_factory=list)

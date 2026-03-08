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
    llm_prompt: str = ""
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
    agent_name: str = ""
    agent_role: str = ""
    tool_name: str | None = None
    tool_parameters: dict[str, Any] = {}
    tool_response: dict[str, Any] = {}
    llm_model: str = ""
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_reasoning: str = ""
    llm_prompt: str = ""
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    status: str = "success"
    error_message: str | None = None
    step_number: int = 0
    parent_event_id: str | None = None


class TraceOut(BaseModel):
    """Full workflow trace response."""

    workflow_id: str
    task_description: str | None = None
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


# === Dashboard models ===


class WorkflowSummary(BaseModel):
    """Per-workflow summary for GET /workflows."""

    workflow_id: str
    task_description: str | None
    status: str
    duration_ms: float | None
    steps: int | None
    mode: str
    timestamp: datetime


class WorkflowListOut(BaseModel):
    """Paginated workflow list response."""

    workflows: list[WorkflowSummary]
    total: int


class OptimalPathRow(BaseModel):
    """Single row from the optimal_paths table."""

    task_cluster: str | None
    tool_sequence: list[str]
    avg_duration_ms: float | None
    avg_steps: float | None
    success_rate: float | None
    execution_count: int
    updated_at: datetime | None


class OptimalPathsOut(BaseModel):
    """Response for GET /optimal-paths."""

    paths: list[OptimalPathRow]


class ModeDistributionOut(BaseModel):
    """Mode distribution counts for GET /analytics/mode-distribution."""

    exploration: int
    guided: int
    total: int


class ModeStats(BaseModel):
    """Aggregate stats for a single execution mode."""

    avg_duration_ms: float | None
    avg_steps: float | None
    success_rate: float | None
    count: int
    avg_cost_usd: float | None = None


class ComparisonOut(BaseModel):
    """Exploration vs guided aggregate stats for GET /analytics/comparison."""

    exploration: ModeStats
    guided: ModeStats


class TimelinePoint(BaseModel):
    """Single date bucket for GET /analytics/timeline."""

    date: str
    workflows: int
    avg_duration_ms: float | None
    success_rate: float | None
    guided_pct: float | None


class TimelineOut(BaseModel):
    """Time-series metrics response."""

    points: list[TimelinePoint]


class GraphNode(BaseModel):
    """Tool node for the execution graph."""

    id: str
    label: str
    avg_duration_ms: float | None
    call_count: int


class GraphEdge(BaseModel):
    """Directed tool-to-tool transition edge."""

    source: str
    target: str
    weight: int


class ExecutionGraphOut(BaseModel):
    """Tool transition graph for GET /analytics/execution-graph."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]


class BottleneckTool(BaseModel):
    """Per-tool performance stats for GET /analytics/bottlenecks."""

    tool_name: str
    call_count: int
    avg_duration_ms: float | None
    total_cost_usd: float
    avg_calls_per_workflow: float


class BottlenecksOut(BaseModel):
    """Tool bottleneck stats response."""

    tools: list[BottleneckTool]


class SavingsOut(BaseModel):
    """Cumulative savings for GET /analytics/savings."""

    time_saved_ms: float
    cost_saved_usd: float
    pct_duration_improvement: float
    pct_steps_improvement: float
    pct_success_improvement: float
    guided_count: int


# === Task Cluster models ===


class TaskClusterSummary(BaseModel):
    """Summary row for GET /task-clusters."""

    path_id: str
    task_cluster: str
    tool_sequence: list[str]
    avg_duration_ms: float | None
    avg_steps: float | None
    success_rate: float | None
    execution_count: int
    workflow_count: int
    updated_at: datetime | None
    task_description: str | None = None


class TaskClustersOut(BaseModel):
    """Response for GET /task-clusters."""

    clusters: list[TaskClusterSummary]


class ClusterGroup(BaseModel):
    """A Level-1 cluster group with nested sub-clusters."""

    name: str
    subclusters: list[TaskClusterSummary]
    total_workflows: int


class ClusterGroupsOut(BaseModel):
    """Response for GET /task-clusters/grouped."""

    groups: list[ClusterGroup]


class ClusterWorkflow(BaseModel):
    """Single workflow run within a task cluster."""

    workflow_id: str
    task_description: str | None
    similarity: float
    status: str
    duration_ms: float | None
    steps: int | None
    mode: str
    timestamp: datetime
    cost_usd: float | None


class ClusterModeStats(BaseModel):
    """Exploration vs guided stats scoped to a single cluster."""

    exploration: ModeStats
    guided: ModeStats


class ClusterDetailOut(BaseModel):
    """Response for GET /task-clusters/{path_id}/workflows."""

    path_id: str
    task_cluster: str
    tool_sequence: list[str]
    avg_duration_ms: float | None
    avg_steps: float | None
    success_rate: float | None
    execution_count: int
    updated_at: datetime | None
    workflows: list[ClusterWorkflow]
    mode_stats: ClusterModeStats
    avg_conformance: float | None = None


class DistinctPath(BaseModel):
    """A unique tool sequence observed in a cluster group."""

    tool_sequence: list[str]
    workflow_count: int


class ClusterGroupDetailOut(BaseModel):
    """Response for GET /task-clusters/group/{name}/detail."""

    name: str
    subclusters: list[TaskClusterSummary]
    total_workflows: int
    avg_duration_ms: float | None
    avg_steps: float | None
    success_rate: float | None
    workflows: list[ClusterWorkflow]
    mode_stats: ClusterModeStats
    avg_conformance: float | None = None
    optimal_sequence: list[str] = []
    distinct_paths: list[DistinctPath] = []

"""Dashboard endpoints: workflows, optimal paths, and analytics aggregates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from collector.logger import get_logger
from collector.models import (
    BottlenecksOut,
    ComparisonOut,
    ExecutionGraphOut,
    ModeDistributionOut,
    ModeStats,
    OptimalPathRow,
    OptimalPathsOut,
    SavingsOut,
    TimelineOut,
    TimelinePoint,
    WorkflowListOut,
    WorkflowSummary,
)

log = get_logger("collector.routes.dashboard")
router = APIRouter()


def _fopt(value: Any, default: float | None = None) -> float | None:
    """Return float(value) when value is not None, else default."""
    return float(value) if value is not None else default


@router.get("/workflows")
async def list_workflows(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> WorkflowListOut:
    """Return a paginated list of completed workflows with basic stats."""
    db = request.app.state.db
    data = await db.list_workflows(limit=limit, offset=offset)
    workflows = [
        WorkflowSummary(
            workflow_id=row["workflow_id"],
            task_description=row.get("task_description"),
            status=row["status"],
            duration_ms=_fopt(row.get("duration_ms")),
            steps=row.get("steps"),
            mode="guided" if row.get("is_guided") else "exploration",
            timestamp=row["timestamp"],
        )
        for row in data["workflows"]
    ]
    log.info("list_workflows", count=len(workflows), total=data["total"])
    return WorkflowListOut(workflows=workflows, total=data["total"])


@router.get("/optimal-paths")
async def list_optimal_paths(request: Request) -> OptimalPathsOut:
    """Return all rows from the optimal_paths table."""
    db = request.app.state.db
    rows = await db.list_optimal_paths()
    paths = [
        OptimalPathRow(
            task_cluster=row.get("task_cluster"),
            tool_sequence=list(row["tool_sequence"]),
            avg_duration_ms=_fopt(row.get("avg_duration_ms")),
            avg_steps=_fopt(row.get("avg_steps")),
            success_rate=_fopt(row.get("success_rate")),
            execution_count=row["execution_count"],
            updated_at=row.get("updated_at"),
        )
        for row in rows
    ]
    log.info("list_optimal_paths", count=len(paths))
    return OptimalPathsOut(paths=paths)


@router.get("/analytics/mode-distribution")
async def get_mode_distribution(request: Request) -> ModeDistributionOut:
    """Count guided vs exploration workflow executions."""
    db = request.app.state.db
    data = await db.get_mode_distribution()
    log.info("mode_distribution", **data)
    return ModeDistributionOut(**data)


@router.get("/analytics/comparison")
async def get_comparison(request: Request) -> ComparisonOut:
    """Aggregate performance stats split by guided vs exploration mode."""
    db = request.app.state.db
    data = await db.get_mode_comparison()
    log.info("mode_comparison")
    return ComparisonOut(
        exploration=ModeStats(**data["exploration"]),
        guided=ModeStats(**data["guided"]),
    )


@router.get("/analytics/timeline")
async def get_timeline(request: Request) -> TimelineOut:
    """Daily time-series aggregates of workflow executions."""
    db = request.app.state.db
    rows = await db.get_timeline()
    points = [
        TimelinePoint(
            date=str(row["date"]),
            workflows=row["workflows"],
            avg_duration_ms=_fopt(row.get("avg_duration_ms")),
            success_rate=_fopt(row.get("success_rate")),
            guided_pct=_fopt(row.get("guided_pct")),
        )
        for row in rows
    ]
    log.info("timeline", points=len(points))
    return TimelineOut(points=points)


@router.get("/analytics/execution-graph")
async def get_execution_graph(request: Request) -> ExecutionGraphOut:
    """Tool-to-tool transition graph built from workflow event sequences."""
    db = request.app.state.db
    data = await db.get_execution_graph()
    log.info("execution_graph", nodes=len(data["nodes"]), edges=len(data["edges"]))
    return ExecutionGraphOut(**data)


@router.get("/analytics/bottlenecks")
async def get_bottlenecks(request: Request) -> BottlenecksOut:
    """Per-tool aggregate stats ordered by average duration."""
    db = request.app.state.db
    rows = await db.get_bottlenecks()
    tools = [
        {
            "tool_name": row["tool_name"],
            "call_count": row["call_count"],
            "avg_duration_ms": _fopt(row.get("avg_duration_ms")),
            "total_cost_usd": _fopt(row.get("total_cost_usd"), default=0.0) or 0.0,
            "avg_calls_per_workflow": (
                _fopt(row.get("avg_calls_per_workflow"), default=0.0) or 0.0
            ),
        }
        for row in rows
    ]
    log.info("bottlenecks", count=len(tools))
    return BottlenecksOut(tools=tools)


@router.get("/analytics/savings")
async def get_savings(request: Request) -> SavingsOut:
    """Cumulative time and cost savings from guided vs exploration workflows."""
    db = request.app.state.db
    data = await db.get_savings()
    log.info(
        "savings",
        time_saved_ms=data["time_saved_ms"],
        cost_saved_usd=data["cost_saved_usd"],
    )
    return SavingsOut(**data)

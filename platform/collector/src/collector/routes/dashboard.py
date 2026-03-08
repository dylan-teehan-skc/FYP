"""Dashboard endpoints: workflows, optimal paths, and analytics aggregates."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from collector.logger import get_logger
from collector.models import (
    BottlenecksOut,
    ClusterDetailOut,
    ClusterGroup,
    ClusterGroupDetailOut,
    ClusterGroupsOut,
    ClusterModeStats,
    ClusterWorkflow,
    ComparisonOut,
    DistinctPath,
    ExecutionGraphOut,
    ModeDistributionOut,
    ModeStats,
    OptimalPathRow,
    OptimalPathsOut,
    SavingsOut,
    TaskClustersOut,
    TaskClusterSummary,
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


@router.get("/task-clusters/grouped")
async def list_task_clusters_grouped(request: Request) -> ClusterGroupsOut:
    """Return task clusters grouped by Level-1 parent cluster."""
    db = request.app.state.db
    settings = request.app.state.settings
    rows = await db.list_task_clusters(settings.similarity_threshold)

    clusters = [
        TaskClusterSummary(
            path_id=row["path_id"],
            task_cluster=row["task_cluster"],
            tool_sequence=list(row["tool_sequence"]),
            avg_duration_ms=_fopt(row.get("avg_duration_ms")),
            avg_steps=_fopt(row.get("avg_steps")),
            success_rate=_fopt(row.get("success_rate")),
            execution_count=row["execution_count"],
            workflow_count=row["workflow_count"],
            updated_at=row.get("updated_at"),
            task_description=row.get("task_description"),
        )
        for row in rows
    ]

    subcluster_re = re.compile(r"^(.+?)\s*\(subcluster_\d+\)$")
    groups_map: dict[str, list[TaskClusterSummary]] = {}
    group_level: dict[str, TaskClusterSummary] = {}
    for c in clusters:
        m = subcluster_re.match(c.task_cluster)
        if m:
            parent = m.group(1).strip()
            groups_map.setdefault(parent, []).append(c)
        else:
            parent = c.task_cluster
            group_level[parent] = c
            groups_map.setdefault(parent, []).append(c)

    groups = []
    for name, subs in groups_map.items():
        if name in group_level:
            total = group_level[name].workflow_count
        else:
            total = sum(s.workflow_count for s in subs)
        groups.append(ClusterGroup(
            name=name, subclusters=subs, total_workflows=total,
        ))
    groups.sort(key=lambda g: g.total_workflows, reverse=True)

    log.info("list_task_clusters_grouped", groups=len(groups))
    return ClusterGroupsOut(groups=groups)


@router.get("/task-clusters/group/{name}/detail")
async def get_cluster_group_detail(
    name: str, request: Request
) -> ClusterGroupDetailOut:
    """Return aggregate detail for a cluster group (all variants combined)."""
    db = request.app.state.db
    settings = request.app.state.settings
    group_name = name

    # Get all path_ids and cluster summaries for this group
    path_ids = await db.get_group_path_ids(group_name)
    if not path_ids:
        raise HTTPException(status_code=404, detail="Cluster group not found")

    # Get cluster summaries for subclusters
    all_rows = await db.list_task_clusters(settings.similarity_threshold)
    subclusters = [
        TaskClusterSummary(
            path_id=row["path_id"],
            task_cluster=row["task_cluster"],
            tool_sequence=list(row["tool_sequence"]),
            avg_duration_ms=_fopt(row.get("avg_duration_ms")),
            avg_steps=_fopt(row.get("avg_steps")),
            success_rate=_fopt(row.get("success_rate")),
            execution_count=row["execution_count"],
            workflow_count=row["workflow_count"],
            updated_at=row.get("updated_at"),
            task_description=row.get("task_description"),
        )
        for row in all_rows
        if row["path_id"] in path_ids
    ]

    # Get combined workflows and stats
    data = await db.get_group_workflows(path_ids, settings.similarity_threshold)
    workflows = [
        ClusterWorkflow(
            workflow_id=row["workflow_id"],
            task_description=row.get("task_description"),
            similarity=round(float(row["similarity"]), 4),
            status=row["status"],
            duration_ms=_fopt(row.get("duration_ms")),
            steps=row.get("steps"),
            mode="guided" if row.get("is_guided") else "exploration",
            timestamp=row["timestamp"],
            cost_usd=_fopt(row.get("total_cost_usd")),
        )
        for row in data["workflows"]
    ]

    ms = data.get("mode_stats") or {}
    mode_stats = ClusterModeStats(
        exploration=ModeStats(
            avg_duration_ms=_fopt(ms.get("exp_avg_duration")),
            avg_steps=_fopt(ms.get("exp_avg_steps")),
            success_rate=_fopt(ms.get("exp_success_rate")),
            count=ms.get("exp_count") or 0,
            avg_cost_usd=_fopt(ms.get("exp_avg_cost")),
        ),
        guided=ModeStats(
            avg_duration_ms=_fopt(ms.get("gui_avg_duration")),
            avg_steps=_fopt(ms.get("gui_avg_steps")),
            success_rate=_fopt(ms.get("gui_success_rate")),
            count=ms.get("gui_count") or 0,
            avg_cost_usd=_fopt(ms.get("gui_avg_cost")),
        ),
    )

    total_workflows = sum(s.workflow_count for s in subclusters)

    # Compute weighted averages from subclusters
    with_dur = [s for s in subclusters if s.avg_duration_ms is not None]
    dur_wf = sum(s.execution_count for s in with_dur)
    avg_duration = (
        sum((s.avg_duration_ms or 0) * s.execution_count for s in with_dur) / dur_wf
        if dur_wf > 0 else None
    )

    with_steps = [s for s in subclusters if s.avg_steps is not None]
    steps_wf = sum(s.execution_count for s in with_steps)
    avg_steps = (
        sum((s.avg_steps or 0) * s.execution_count for s in with_steps) / steps_wf
        if steps_wf > 0 else None
    )

    with_rate = [s for s in subclusters if s.success_rate is not None]
    rate_wf = sum(s.execution_count for s in with_rate)
    success_rate = (
        sum((s.success_rate or 0) * s.execution_count for s in with_rate) / rate_wf
        if rate_wf > 0 else None
    )

    # Find group-level optimal path (exact match, no subcluster suffix)
    group_path = next(
        (r for r in all_rows if r["task_cluster"] == group_name),
        None,
    )
    if group_path:
        optimal_sequence = list(group_path["tool_sequence"])
    else:
        # No group-level path stored (skip_upsert=True in analysis pipeline).
        # Fall back to the best-performing variant's tool sequence.
        best = max(
            (s for s in subclusters if s.tool_sequence),
            key=lambda s: (s.success_rate or 0, s.execution_count),
            default=None,
        )
        optimal_sequence = list(best.tool_sequence) if best else []

    # Filter subclusters to only include subcluster variants (not the group-level path)
    subclusters = [s for s in subclusters if s.task_cluster != group_name]

    # Get all distinct tool sequences observed across workflows in this group
    distinct_rows = await db.get_group_distinct_paths(path_ids, settings.similarity_threshold)
    distinct_paths = [
        DistinctPath(
            tool_sequence=r["tool_sequence"],
            workflow_count=r["workflow_count"],
        )
        for r in distinct_rows
    ]

    log.info("cluster_group_detail", group=group_name, workflows=len(workflows))
    return ClusterGroupDetailOut(
        name=group_name,
        subclusters=subclusters,
        total_workflows=total_workflows,
        avg_duration_ms=avg_duration,
        avg_steps=avg_steps,
        success_rate=success_rate,
        workflows=workflows,
        mode_stats=mode_stats,
        avg_conformance=_fopt(data.get("avg_conformance")),
        optimal_sequence=optimal_sequence,
        distinct_paths=distinct_paths,
    )


@router.get("/task-clusters/group/{name}/execution-graph")
async def get_cluster_group_execution_graph(
    name: str, request: Request
) -> ExecutionGraphOut:
    """Tool-to-tool transition graph for a cluster group."""
    db = request.app.state.db
    settings = request.app.state.settings
    path_ids = await db.get_group_path_ids(name)
    if not path_ids:
        raise HTTPException(status_code=404, detail="Cluster group not found")

    data = await db.get_group_execution_graph(path_ids, settings.similarity_threshold)
    log.info(
        "cluster_group_execution_graph",
        group=name,
        nodes=len(data["nodes"]),
        edges=len(data["edges"]),
    )
    return ExecutionGraphOut(**data)


@router.get("/task-clusters/group/{name}/bottlenecks")
async def get_cluster_group_bottlenecks(
    name: str, request: Request
) -> BottlenecksOut:
    """Per-tool aggregate stats for a cluster group."""
    db = request.app.state.db
    settings = request.app.state.settings
    path_ids = await db.get_group_path_ids(name)
    if not path_ids:
        raise HTTPException(status_code=404, detail="Cluster group not found")

    rows = await db.get_group_bottlenecks(path_ids, settings.similarity_threshold)
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
    log.info("cluster_group_bottlenecks", group=name, count=len(tools))
    return BottlenecksOut(tools=tools)


@router.get("/task-clusters/{path_id}/execution-graph")
async def get_cluster_execution_graph(
    path_id: str, request: Request
) -> ExecutionGraphOut:
    """Tool-to-tool transition graph scoped to a single task cluster."""
    db = request.app.state.db
    settings = request.app.state.settings
    data = await db.get_cluster_execution_graph(path_id, settings.similarity_threshold)
    log.info(
        "cluster_execution_graph",
        path_id=path_id,
        nodes=len(data["nodes"]),
        edges=len(data["edges"]),
    )
    return ExecutionGraphOut(**data)


@router.get("/task-clusters/{path_id}/bottlenecks")
async def get_cluster_bottlenecks(
    path_id: str, request: Request
) -> BottlenecksOut:
    """Per-tool aggregate stats scoped to a single task cluster."""
    db = request.app.state.db
    settings = request.app.state.settings
    rows = await db.get_cluster_bottlenecks(path_id, settings.similarity_threshold)
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
    log.info("cluster_bottlenecks", path_id=path_id, count=len(tools))
    return BottlenecksOut(tools=tools)


@router.get("/task-clusters")
async def list_task_clusters(request: Request) -> TaskClustersOut:
    """Return all discovered task clusters with summary stats."""
    db = request.app.state.db
    settings = request.app.state.settings
    rows = await db.list_task_clusters(settings.similarity_threshold)
    clusters = [
        TaskClusterSummary(
            path_id=row["path_id"],
            task_cluster=row["task_cluster"],
            tool_sequence=list(row["tool_sequence"]),
            avg_duration_ms=_fopt(row.get("avg_duration_ms")),
            avg_steps=_fopt(row.get("avg_steps")),
            success_rate=_fopt(row.get("success_rate")),
            execution_count=row["execution_count"],
            workflow_count=row["workflow_count"],
            updated_at=row.get("updated_at"),
            task_description=row.get("task_description"),
        )
        for row in rows
    ]
    log.info("list_task_clusters", count=len(clusters))
    return TaskClustersOut(clusters=clusters)


@router.get("/task-clusters/{path_id}/workflows")
async def get_cluster_detail(path_id: str, request: Request) -> ClusterDetailOut:
    """Return the optimal path and all matching workflows for a cluster."""
    db = request.app.state.db
    settings = request.app.state.settings
    data = await db.get_cluster_workflows(path_id, settings.similarity_threshold)

    if data["path"] is None:
        raise HTTPException(status_code=404, detail="Task cluster not found")

    path = data["path"]
    workflows = [
        ClusterWorkflow(
            workflow_id=row["workflow_id"],
            task_description=row.get("task_description"),
            similarity=round(float(row["similarity"]), 4),
            status=row["status"],
            duration_ms=_fopt(row.get("duration_ms")),
            steps=row.get("steps"),
            mode="guided" if row.get("is_guided") else "exploration",
            timestamp=row["timestamp"],
            cost_usd=_fopt(row.get("total_cost_usd")),
        )
        for row in data["workflows"]
    ]

    ms = data.get("mode_stats") or {}
    mode_stats = ClusterModeStats(
        exploration=ModeStats(
            avg_duration_ms=_fopt(ms.get("exp_avg_duration")),
            avg_steps=_fopt(ms.get("exp_avg_steps")),
            success_rate=_fopt(ms.get("exp_success_rate")),
            count=ms.get("exp_count") or 0,
            avg_cost_usd=_fopt(ms.get("exp_avg_cost")),
        ),
        guided=ModeStats(
            avg_duration_ms=_fopt(ms.get("gui_avg_duration")),
            avg_steps=_fopt(ms.get("gui_avg_steps")),
            success_rate=_fopt(ms.get("gui_success_rate")),
            count=ms.get("gui_count") or 0,
            avg_cost_usd=_fopt(ms.get("gui_avg_cost")),
        ),
    )

    log.info("cluster_detail", path_id=path_id, workflows=len(workflows))
    return ClusterDetailOut(
        path_id=path["path_id"],
        task_cluster=path["task_cluster"],
        tool_sequence=list(path["tool_sequence"]),
        avg_duration_ms=_fopt(path.get("avg_duration_ms")),
        avg_steps=_fopt(path.get("avg_steps")),
        success_rate=_fopt(path.get("success_rate")),
        execution_count=path["execution_count"],
        updated_at=path.get("updated_at"),
        workflows=workflows,
        mode_stats=mode_stats,
        avg_conformance=_fopt(data.get("avg_conformance")),
    )

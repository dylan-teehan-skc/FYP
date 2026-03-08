"""Pareto-optimal path discovery via enumeration + non-dominated sorting."""

from __future__ import annotations

import networkx as nx

from analysis.graph import END_NODE, START_NODE
from analysis.logger import get_logger
from analysis.models import OptimalPath, WorkflowTrace

log = get_logger("analysis.optimizer")


def filter_graph_by_success_rate(
    graph: nx.DiGraph,
    min_success_rate: float,
) -> nx.DiGraph:
    """Return a copy of the graph with low-success edges removed."""
    filtered = graph.copy()
    to_remove = [
        (u, v)
        for u, v, data in filtered.edges(data=True)
        if data.get("success_rate", 0.0) < min_success_rate
    ]
    filtered.remove_edges_from(to_remove)
    return filtered


def enumerate_paths(
    graph: nx.DiGraph,
    source: str = START_NODE,
    target: str = END_NODE,
) -> list[list[str]]:
    """Enumerate all simple paths from source to target."""
    try:
        return list(nx.all_simple_paths(graph, source, target))
    except nx.NodeNotFound:
        return []


def compute_path_metrics(
    traces: list[WorkflowTrace],
    path: list[str],
) -> dict[str, float]:
    """Compute aggregate metrics for traces whose tool_sequence matches the path."""
    matching = [t for t in traces if t.tool_sequence == path]

    if not matching:
        # Broaden: traces containing the path as a subsequence, but require
        # the path to cover at least 50% of the trace's tools to prevent
        # short fragments (e.g. ["get_order"]) from matching long traces.
        matching = [
            t for t in traces
            if _is_subsequence(path, t.tool_sequence)
            and len(path) >= len(t.tool_sequence) * 0.5
        ]

    if not matching:
        return {
            "avg_duration_ms": 0.0,
            "avg_cost_usd": 0.0,
            "avg_steps": float(len(path)),
            "success_rate": 0.0,
            "execution_count": 0,
        }

    return {
        "avg_duration_ms": sum(t.total_duration_ms for t in matching) / len(matching),
        "avg_cost_usd": sum(t.total_cost_usd for t in matching) / len(matching),
        "avg_steps": sum(t.total_steps for t in matching) / len(matching),
        "success_rate": sum(1.0 for t in matching if t.success) / len(matching),
        "execution_count": len(matching),
    }


def _is_subsequence(subseq: list[str], seq: list[str]) -> bool:
    """Check if subseq is a subsequence of seq."""
    it = iter(seq)
    return all(item in it for item in subseq)


def compute_pareto_front(
    candidates: list[tuple[list[str], dict[str, float]]],
) -> list[tuple[list[str], dict[str, float]]]:
    """Non-dominated sorting: keep only Pareto-optimal paths.

    Objectives (all minimized): duration, cost, (1 - success_rate).
    """
    if not candidates:
        return []

    def dominates(a: dict[str, float], b: dict[str, float]) -> bool:
        """Check if a dominates b (better/equal on all, strictly better on one)."""
        obj_a = (a["avg_duration_ms"], a["avg_cost_usd"], 1 - a["success_rate"])
        obj_b = (b["avg_duration_ms"], b["avg_cost_usd"], 1 - b["success_rate"])
        better_or_equal = all(x <= y for x, y in zip(obj_a, obj_b))
        strictly_better = any(x < y for x, y in zip(obj_a, obj_b))
        return better_or_equal and strictly_better

    pareto = []
    for path, metrics in candidates:
        dominated = False
        for _, other_metrics in candidates:
            if other_metrics is not metrics and dominates(other_metrics, metrics):
                dominated = True
                break
        if not dominated:
            pareto.append((path, metrics))

    return pareto


def select_knee_point(
    pareto_front: list[tuple[list[str], dict[str, float]]],
) -> tuple[list[str], dict[str, float]] | None:
    """Select the path with the best tradeoff (lowest normalized sum of objectives)."""
    if not pareto_front:
        return None
    if len(pareto_front) == 1:
        return pareto_front[0]

    # Normalize each objective to [0, 1] across the front
    durations = [m["avg_duration_ms"] for _, m in pareto_front]
    costs = [m["avg_cost_usd"] for _, m in pareto_front]
    failures = [1 - m["success_rate"] for _, m in pareto_front]

    def normalize(values: list[float]) -> list[float]:
        lo, hi = min(values), max(values)
        if hi == lo:
            return [0.0] * len(values)
        return [(v - lo) / (hi - lo) for v in values]

    norm_d = normalize(durations)
    norm_c = normalize(costs)
    norm_f = normalize(failures)

    # Pick the path minimizing the sum of normalized objectives
    best_idx = min(
        range(len(pareto_front)),
        key=lambda i: norm_d[i] + norm_c[i] + norm_f[i],
    )
    return pareto_front[best_idx]


def _most_frequent_path(traces: list[WorkflowTrace]) -> list[str]:
    """Fallback: return the tool_sequence that appears most often."""
    from collections import Counter

    seqs = [tuple(t.tool_sequence) for t in traces if t.tool_sequence]
    if not seqs:
        return []
    most_common = Counter(seqs).most_common(1)[0][0]
    return list(most_common)


def find_pareto_paths(
    graph: nx.DiGraph,
    traces: list[WorkflowTrace],
    task_cluster: str,
    min_success_rate: float = 0.85,
) -> list[OptimalPath]:
    """Find Pareto-optimal paths through the execution graph.

    1. Filter edges by success_rate
    2. Enumerate all source-to-sink paths
    3. Score each on (duration, cost, 1-success_rate)
    4. Filter by minimum support (execution_count)
    5. Compute Pareto front + select knee point
    """
    filtered = filter_graph_by_success_rate(graph, min_success_rate)
    raw_paths = enumerate_paths(filtered)

    # Strip sentinels
    tool_paths = [
        [n for n in p if n not in (START_NODE, END_NODE)]
        for p in raw_paths
    ]
    tool_paths = [p for p in tool_paths if p]  # remove empty

    # Filter out fragment paths that are too short relative to actual traces.
    # A path must cover at least 50% of the average trace length.
    if traces and tool_paths:
        avg_trace_len = sum(len(t.tool_sequence) for t in traces) / len(traces)
        min_path_len = max(2, int(avg_trace_len * 0.5))
        long_enough = [p for p in tool_paths if len(p) >= min_path_len]
        if long_enough:
            tool_paths = long_enough
            log.info(
                "path_coverage_filter",
                cluster=task_cluster,
                avg_trace_len=round(avg_trace_len, 1),
                min_path_len=min_path_len,
                paths_remaining=len(tool_paths),
            )

    if not tool_paths:
        # Fallback to most frequent path
        fallback = _most_frequent_path(traces)
        if not fallback:
            return []
        tool_paths = [fallback]
        log.info("optimizer_fallback", reason="no_paths_after_filtering")

    # Score each path
    candidates = [
        (path, compute_path_metrics(traces, path))
        for path in tool_paths
    ]

    # Filter out paths below minimum success rate
    candidates = [
        (p, m) for p, m in candidates if m["success_rate"] >= min_success_rate
    ]
    if not candidates:
        log.info("no_viable_paths", cluster=task_cluster)
        return []

    # Minimum support: path must have been followed by enough traces to be
    # considered reliable. At least 2 traces or 10% of the cluster.
    min_support = max(2, int(len(traces) * 0.10))
    supported = [
        (p, m) for p, m in candidates if m["execution_count"] >= min_support
    ]
    if not supported:
        log.info(
            "no_paths_with_min_support",
            cluster=task_cluster,
            min_support=min_support,
        )
        return []
    candidates = supported

    # Pareto front
    pareto = compute_pareto_front(candidates)

    # Build OptimalPath objects with rank
    results = []
    for rank, (path, metrics) in enumerate(pareto):
        results.append(OptimalPath(
            task_cluster=task_cluster,
            tool_sequence=path,
            avg_duration_ms=metrics["avg_duration_ms"],
            avg_cost_usd=metrics["avg_cost_usd"],
            avg_steps=metrics["avg_steps"],
            success_rate=metrics["success_rate"],
            execution_count=int(metrics["execution_count"]),
            pareto_rank=rank,
        ))

    log.info(
        "pareto_paths_found",
        cluster=task_cluster,
        total_paths=len(tool_paths),
        pareto_size=len(results),
    )
    return results

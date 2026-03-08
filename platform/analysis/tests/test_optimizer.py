"""Tests for Pareto-optimal path discovery."""

from __future__ import annotations

import networkx as nx

from analysis.graph import END_NODE, START_NODE
from analysis.models import WorkflowTrace
from analysis.optimizer import (
    _is_subsequence,
    _most_frequent_path,
    compute_pareto_front,
    compute_path_metrics,
    enumerate_paths,
    filter_graph_by_success_rate,
    find_pareto_paths,
    select_knee_point,
)
from tests.conftest import make_event


def _trace(
    wf_id: str = "wf-1",
    tools: list[str] | None = None,
    duration: float = 1000.0,
    cost: float = 0.006,
    success: bool = True,
) -> WorkflowTrace:
    tools = tools or ["a", "b", "c"]
    events = [
        make_event(workflow_id=wf_id, tool_name=t, step_number=i + 1)
        for i, t in enumerate(tools)
    ]
    return WorkflowTrace(
        workflow_id=wf_id,
        events=events,
        tool_sequence=tools,
        total_duration_ms=duration,
        total_cost_usd=cost,
        total_steps=len(tools),
        success=success,
    )


def _build_graph() -> nx.DiGraph:
    """Simple graph: START -> a -> b -> END."""
    g = nx.DiGraph()
    g.add_edge(START_NODE, "a", success_rate=1.0, weight=100, avg_duration_ms=100,
               avg_cost_usd=0.001, frequency=5)
    g.add_edge("a", "b", success_rate=1.0, weight=200, avg_duration_ms=200,
               avg_cost_usd=0.002, frequency=5)
    g.add_edge("b", END_NODE, success_rate=1.0, weight=0, avg_duration_ms=0,
               avg_cost_usd=0, frequency=5)
    return g


# ── filter_graph_by_success_rate ─────────────────────────────────────

class TestFilterGraph:
    def test_removes_low_success_edges(self) -> None:
        g = nx.DiGraph()
        g.add_edge("a", "b", success_rate=0.5)
        g.add_edge("b", "c", success_rate=0.9)
        filtered = filter_graph_by_success_rate(g, 0.85)
        assert not filtered.has_edge("a", "b")
        assert filtered.has_edge("b", "c")

    def test_keeps_all_when_above_threshold(self) -> None:
        g = _build_graph()
        filtered = filter_graph_by_success_rate(g, 0.85)
        assert len(filtered.edges) == len(g.edges)


# ── enumerate_paths ──────────────────────────────────────────────────

class TestEnumeratePaths:
    def test_finds_all_paths(self) -> None:
        g = _build_graph()
        paths = enumerate_paths(g)
        assert len(paths) == 1
        assert paths[0] == [START_NODE, "a", "b", END_NODE]

    def test_returns_empty_on_missing_node(self) -> None:
        g = nx.DiGraph()
        g.add_edge("x", "y")
        assert enumerate_paths(g) == []

    def test_multiple_paths(self) -> None:
        g = nx.DiGraph()
        g.add_edge(START_NODE, "a")
        g.add_edge(START_NODE, "b")
        g.add_edge("a", END_NODE)
        g.add_edge("b", END_NODE)
        paths = enumerate_paths(g)
        assert len(paths) == 2


# ── compute_path_metrics ─────────────────────────────────────────────

class TestComputePathMetrics:
    def test_exact_match(self) -> None:
        traces = [_trace(tools=["a", "b"], duration=500.0, cost=0.003)]
        m = compute_path_metrics(traces, ["a", "b"])
        assert m["avg_duration_ms"] == 500.0
        assert m["execution_count"] == 1

    def test_subsequence_fallback(self) -> None:
        # Path ["a", "c"] covers 2/3 = 67% of trace — passes 50% threshold
        traces = [_trace(tools=["a", "b", "c"], duration=600.0)]
        m = compute_path_metrics(traces, ["a", "c"])
        assert m["execution_count"] == 1  # found via subsequence

    def test_subsequence_rejects_short_fragments(self) -> None:
        # Path ["a"] covers 1/6 = 17% of trace — below 50% threshold
        traces = [_trace(tools=["a", "b", "c", "d", "e", "f"], duration=600.0)]
        m = compute_path_metrics(traces, ["a"])
        assert m["execution_count"] == 0  # too short to count

    def test_no_match(self) -> None:
        traces = [_trace(tools=["a", "b"])]
        m = compute_path_metrics(traces, ["x", "y"])
        assert m["execution_count"] == 0
        assert m["success_rate"] == 0.0


# ── _is_subsequence ──────────────────────────────────────────────────

class TestIsSubsequence:
    def test_true(self) -> None:
        assert _is_subsequence(["a", "c"], ["a", "b", "c"]) is True

    def test_false(self) -> None:
        assert _is_subsequence(["c", "a"], ["a", "b", "c"]) is False

    def test_empty(self) -> None:
        assert _is_subsequence([], ["a"]) is True


# ── compute_pareto_front ─────────────────────────────────────────────

class TestComputeParetoFront:
    def test_single_candidate(self) -> None:
        candidates = [(["a"], {"avg_duration_ms": 100, "avg_cost_usd": 0.01,
                                "success_rate": 1.0})]
        result = compute_pareto_front(candidates)
        assert len(result) == 1

    def test_dominated_removed(self) -> None:
        c1 = (["a"], {"avg_duration_ms": 100, "avg_cost_usd": 0.01, "success_rate": 1.0})
        c2 = (["b"], {"avg_duration_ms": 200, "avg_cost_usd": 0.02, "success_rate": 0.5})
        result = compute_pareto_front([c1, c2])
        # c1 dominates c2 on all objectives
        assert len(result) == 1
        assert result[0][0] == ["a"]

    def test_non_dominated_both_kept(self) -> None:
        c1 = (["a"], {"avg_duration_ms": 100, "avg_cost_usd": 0.05, "success_rate": 0.9})
        c2 = (["b"], {"avg_duration_ms": 200, "avg_cost_usd": 0.01, "success_rate": 0.9})
        result = compute_pareto_front([c1, c2])
        assert len(result) == 2  # neither dominates the other

    def test_empty(self) -> None:
        assert compute_pareto_front([]) == []


# ── select_knee_point ────────────────────────────────────────────────

class TestSelectKneePoint:
    def test_single_item(self) -> None:
        front = [(["a"], {"avg_duration_ms": 100, "avg_cost_usd": 0.01,
                          "success_rate": 1.0})]
        result = select_knee_point(front)
        assert result is not None
        assert result[0] == ["a"]

    def test_selects_best_tradeoff(self) -> None:
        front = [
            (["fast"], {"avg_duration_ms": 50, "avg_cost_usd": 0.10, "success_rate": 0.8}),
            (["balanced"], {"avg_duration_ms": 100, "avg_cost_usd": 0.05, "success_rate": 0.9}),
            (["cheap"], {"avg_duration_ms": 200, "avg_cost_usd": 0.01, "success_rate": 1.0}),
        ]
        result = select_knee_point(front)
        assert result is not None

    def test_empty(self) -> None:
        assert select_knee_point([]) is None


# ── _most_frequent_path ──────────────────────────────────────────────

class TestMostFrequentPath:
    def test_picks_most_common(self) -> None:
        traces = [
            _trace(wf_id="1", tools=["a", "b"]),
            _trace(wf_id="2", tools=["a", "b"]),
            _trace(wf_id="3", tools=["a", "c"]),
        ]
        assert _most_frequent_path(traces) == ["a", "b"]

    def test_empty(self) -> None:
        assert _most_frequent_path([]) == []


# ── find_pareto_paths (integration) ──────────────────────────────────

class TestFindParetoPaths:
    def test_finds_paths(self) -> None:
        g = _build_graph()
        traces = [
            _trace(wf_id="wf-1", tools=["a", "b"], duration=500.0),
            _trace(wf_id="wf-2", tools=["a", "b"], duration=600.0),
        ]
        results = find_pareto_paths(g, traces, "cluster-1")
        assert len(results) >= 1
        assert results[0].task_cluster == "cluster-1"
        assert results[0].pareto_rank == 0

    def test_fallback_when_no_paths(self) -> None:
        """When filtering removes all edges, fall back to most-frequent."""
        g = nx.DiGraph()
        g.add_edge(START_NODE, "a", success_rate=0.1)
        g.add_edge("a", END_NODE, success_rate=0.1)
        traces = [
            _trace(wf_id="wf-1", tools=["a"], duration=100.0),
            _trace(wf_id="wf-2", tools=["a"], duration=120.0),
        ]
        results = find_pareto_paths(g, traces, "c", min_success_rate=0.99)
        assert len(results) >= 1

    def test_fallback_filtered_by_success_rate(self) -> None:
        """Fallback paths with low success rate are excluded."""
        g = nx.DiGraph()
        g.add_edge(START_NODE, "a", success_rate=0.1)
        g.add_edge("a", END_NODE, success_rate=0.1)
        traces = [
            _trace(wf_id="1", tools=["a"], success=False),
            _trace(wf_id="2", tools=["a"], success=False),
            _trace(wf_id="3", tools=["a"], success=False),
        ]
        results = find_pareto_paths(g, traces, "c", min_success_rate=0.85)
        assert results == []

    def test_min_support_filters_rare_paths(self) -> None:
        """Paths followed by too few traces are filtered out."""
        # Graph has two paths: START->a->b->END and START->a->END
        g = nx.DiGraph()
        g.add_edge(START_NODE, "a", success_rate=1.0, weight=100,
                   avg_duration_ms=100, avg_cost_usd=0.001, frequency=20)
        g.add_edge("a", "b", success_rate=1.0, weight=100,
                   avg_duration_ms=100, avg_cost_usd=0.001, frequency=19)
        g.add_edge("b", END_NODE, success_rate=1.0, weight=0,
                   avg_duration_ms=0, avg_cost_usd=0, frequency=19)
        g.add_edge("a", END_NODE, success_rate=1.0, weight=0,
                   avg_duration_ms=0, avg_cost_usd=0, frequency=1)

        # 19 traces follow [a, b], 1 trace follows [a] (shortcut)
        traces = [
            _trace(wf_id=f"wf-{i}", tools=["a", "b"], duration=500.0)
            for i in range(19)
        ] + [_trace(wf_id="wf-rare", tools=["a"], duration=100.0)]

        results = find_pareto_paths(g, traces, "cluster-test")
        # The rare [a] path should be filtered by min_support
        tool_seqs = [r.tool_sequence for r in results]
        assert ["a", "b"] in tool_seqs
        # [a] alone should NOT survive because it has only 1 execution
        # (min_support = max(2, 20*0.10) = 2)
        assert ["a"] not in tool_seqs

    def test_path_coverage_filters_fragments(self) -> None:
        """Short graph paths are filtered when traces are much longer."""
        # Graph: START->a->END (short) and START->a->b->c->d->END (long)
        g = nx.DiGraph()
        for src, dst, freq in [
            (START_NODE, "a", 10), ("a", "b", 9), ("b", "c", 9),
            ("c", "d", 9), ("d", END_NODE, 9), ("a", END_NODE, 1),
        ]:
            g.add_edge(src, dst, success_rate=1.0, weight=100,
                       avg_duration_ms=100, avg_cost_usd=0.001, frequency=freq)

        # 9 traces with [a,b,c,d], 1 with [a]. avg_trace_len = 3.7
        # min_path_len = max(2, int(3.7*0.5)) = max(2,1) = 2
        # [a] (len=1) filtered, [a,b,c,d] (len=4) kept
        traces = [
            _trace(wf_id=f"wf-{i}", tools=["a", "b", "c", "d"], duration=1000.0)
            for i in range(9)
        ] + [_trace(wf_id="wf-short", tools=["a"], duration=100.0)]

        results = find_pareto_paths(g, traces, "cluster-cov")
        tool_seqs = [r.tool_sequence for r in results]
        assert ["a", "b", "c", "d"] in tool_seqs
        assert ["a"] not in tool_seqs

    def test_no_paths_when_min_support_not_met(self) -> None:
        """Returns empty when no path has enough support (no relaxation)."""
        g = _build_graph()
        # Only 1 trace — min_support = max(2, 0) = 2, but path has count=1
        traces = [_trace(tools=["a", "b"], duration=500.0)]
        results = find_pareto_paths(g, traces, "cluster-1")
        assert results == []

    def test_empty_graph_empty_traces(self) -> None:
        g = nx.DiGraph()
        g.add_node(START_NODE)
        g.add_node(END_NODE)
        results = find_pareto_paths(g, [], "c")
        assert results == []

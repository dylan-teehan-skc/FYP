"""Tests for graph construction and process discovery."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from analysis.graph import (
    END_NODE,
    START_NODE,
    build_execution_graph,
    compute_quality_metrics,
    discover_process_model,
)
from analysis.models import ProcessMetrics, WorkflowTrace
from tests.conftest import make_event

# ── helpers ──────────────────────────────────────────────────────────

def _make_trace(
    wf_id: str = "wf-1",
    tools: list[str] | None = None,
    success: bool = True,
    duration: float = 1000.0,
) -> WorkflowTrace:
    """Quick trace builder for graph tests."""
    tools = tools or ["a", "b", "c"]
    events = [
        make_event(workflow_id=wf_id, tool_name=t, step_number=i + 1,
                   duration_ms=100.0 * (i + 1), cost_usd=0.001)
        for i, t in enumerate(tools)
    ]
    return WorkflowTrace(
        workflow_id=wf_id,
        events=events,
        tool_sequence=tools,
        total_duration_ms=duration,
        total_steps=len(tools),
        success=success,
    )


# ── discover_process_model ───────────────────────────────────────────

class TestDiscoverProcessModel:
    def test_returns_none_when_no_successful_traces(self) -> None:
        traces = [_make_trace(success=False)]
        assert discover_process_model(traces) is None

    def test_returns_none_when_no_traces(self) -> None:
        assert discover_process_model([]) is None

    @patch.dict("sys.modules", {"pm4py": MagicMock()})
    def test_discovery_success(self) -> None:
        import sys

        mock_pm4py = sys.modules["pm4py"]
        mock_net = MagicMock()
        mock_net.transitions = [MagicMock(), MagicMock()]
        mock_pm4py.format_dataframe.return_value = MagicMock(empty=False)
        mock_pm4py.discover_petri_net_inductive.return_value = (
            mock_net, MagicMock(), MagicMock()
        )

        traces = [_make_trace()]
        result = discover_process_model(traces)
        assert result is not None
        assert len(result) == 3

    def test_returns_none_on_exception(self) -> None:
        """When PM4Py raises an error, gracefully return None."""
        with patch.dict("sys.modules", {"pm4py": MagicMock()}) as _:
            import sys

            sys.modules["pm4py"].format_dataframe.side_effect = RuntimeError("boom")
            result = discover_process_model([_make_trace()])
            assert result is None


# ── compute_quality_metrics ──────────────────────────────────────────

class TestComputeQualityMetrics:
    def test_returns_default_on_empty_traces(self) -> None:
        metrics = compute_quality_metrics([], MagicMock(), MagicMock(), MagicMock())
        assert metrics.fitness == 0.0
        assert metrics.precision == 0.0

    @patch.dict("sys.modules", {"pm4py": MagicMock()})
    def test_computes_metrics(self) -> None:
        import sys

        mock_pm4py = sys.modules["pm4py"]
        mock_pm4py.format_dataframe.return_value = MagicMock(empty=False)
        mock_pm4py.fitness_token_based_replay.return_value = {
            "average_trace_fitness": 0.95,
        }
        mock_pm4py.precision_token_based_replay.return_value = 0.88

        traces = [_make_trace()]
        result = compute_quality_metrics(traces, MagicMock(), MagicMock(), MagicMock())
        assert result.fitness == 0.95
        assert result.precision == 0.88

    def test_returns_default_on_exception(self) -> None:
        with patch.dict("sys.modules", {"pm4py": MagicMock()}) as _:
            import sys

            sys.modules["pm4py"].format_dataframe.side_effect = RuntimeError("fail")
            result = compute_quality_metrics(
                [_make_trace()], MagicMock(), MagicMock(), MagicMock()
            )
            assert result == ProcessMetrics()


# ── build_execution_graph ────────────────────────────────────────────

class TestBuildExecutionGraph:
    def test_basic_graph_structure(self) -> None:
        traces = [_make_trace(tools=["a", "b"])]
        g, eg = build_execution_graph(traces, "cluster-1")

        assert START_NODE in g.nodes
        assert END_NODE in g.nodes
        assert "a" in g.nodes
        assert "b" in g.nodes
        assert g.has_edge(START_NODE, "a")
        assert g.has_edge("a", "b")
        assert g.has_edge("b", END_NODE)

    def test_edge_weights(self) -> None:
        traces = [_make_trace(tools=["a", "b"])]
        g, _ = build_execution_graph(traces, "cluster-1")

        edge = g[START_NODE]["a"]
        assert edge["frequency"] == 1
        assert edge["success_rate"] == 1.0
        assert edge["avg_duration_ms"] == 100.0  # first tool, 100 * (0+1)

    def test_multiple_traces_aggregate(self) -> None:
        t1 = _make_trace(wf_id="wf-1", tools=["a", "b"])
        t2 = _make_trace(wf_id="wf-2", tools=["a", "b"])
        g, eg = build_execution_graph([t1, t2], "cluster-1")

        edge = g[START_NODE]["a"]
        assert edge["frequency"] == 2

    def test_divergent_paths(self) -> None:
        t1 = _make_trace(wf_id="wf-1", tools=["a", "b"])
        t2 = _make_trace(wf_id="wf-2", tools=["a", "c"])
        g, _ = build_execution_graph([t1, t2], "cluster-1")

        assert g.has_edge("a", "b")
        assert g.has_edge("a", "c")

    def test_execution_graph_model(self) -> None:
        traces = [_make_trace(tools=["a", "b"])]
        _, eg = build_execution_graph(traces, "my-cluster")

        assert eg.task_cluster == "my-cluster"
        assert eg.total_traces == 1
        assert len(eg.nodes) == 4  # START, a, b, END
        assert len(eg.edges) == 3  # START->a, a->b, b->END

    def test_empty_traces(self) -> None:
        g, eg = build_execution_graph([], "empty")
        assert START_NODE in g.nodes
        assert END_NODE in g.nodes
        assert eg.total_traces == 0

    def test_failed_trace_success_rate(self) -> None:
        t_ok = _make_trace(wf_id="wf-1", tools=["a"], success=True)
        t_fail = _make_trace(wf_id="wf-2", tools=["a"], success=False)
        g, _ = build_execution_graph([t_ok, t_fail], "c")

        edge = g[START_NODE]["a"]
        assert edge["success_rate"] == pytest.approx(0.5)

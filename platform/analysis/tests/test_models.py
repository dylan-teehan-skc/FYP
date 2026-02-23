"""Tests for analysis domain models."""

from __future__ import annotations

from analysis.models import (
    AnalysisResult,
    EventRecord,
    ExecutionGraph,
    GraphEdge,
    OptimalPath,
    PatternAnomaly,
    ProcessMetrics,
    Suggestion,
    WorkflowTrace,
)


class TestEventRecord:
    def test_minimal_construction(self) -> None:
        e = EventRecord(
            event_id="e1",
            workflow_id="wf-1",
            timestamp="2025-02-23T10:00:00Z",
            activity="tool_call:test",
        )
        assert e.tool_name is None
        assert e.duration_ms == 0.0
        assert e.status == "success"

    def test_full_construction(self) -> None:
        e = EventRecord(
            event_id="e1",
            workflow_id="wf-1",
            timestamp="2025-02-23T10:00:00Z",
            activity="tool_call:test",
            tool_name="check_ticket",
            duration_ms=230.0,
            cost_usd=0.002,
            status="failure",
            error_message="timeout",
        )
        assert e.tool_name == "check_ticket"
        assert e.status == "failure"


class TestWorkflowTrace:
    def test_default_values(self) -> None:
        t = WorkflowTrace(workflow_id="wf-1")
        assert t.tool_sequence == []
        assert t.total_duration_ms == 0.0
        assert t.success is False

    def test_with_data(self) -> None:
        t = WorkflowTrace(
            workflow_id="wf-1",
            tool_sequence=["a", "b"],
            total_duration_ms=500.0,
            success=True,
        )
        assert len(t.tool_sequence) == 2
        assert t.success is True


class TestOptimalPath:
    def test_auto_id(self) -> None:
        p = OptimalPath(task_cluster="test")
        assert len(p.path_id) == 36  # UUID format

    def test_pareto_rank(self) -> None:
        p = OptimalPath(task_cluster="test", pareto_rank=2)
        assert p.pareto_rank == 2


class TestOtherModels:
    def test_graph_edge(self) -> None:
        e = GraphEdge(source="a", target="b", weight=100.0, frequency=5)
        assert e.success_rate == 0.0

    def test_execution_graph(self) -> None:
        g = ExecutionGraph(task_cluster="test", total_traces=10)
        assert g.nodes == []

    def test_process_metrics(self) -> None:
        m = ProcessMetrics(fitness=0.95, precision=0.88)
        assert m.fitness == 0.95

    def test_pattern_anomaly(self) -> None:
        p = PatternAnomaly(pattern_type="bottleneck", description="slow tool")
        assert p.severity == "medium"

    def test_suggestion(self) -> None:
        s = Suggestion(suggestion_type="skip_step", message="remove tool X")
        assert s.priority == "medium"
        assert s.estimated_saving_ms == 0.0

    def test_analysis_result(self) -> None:
        r = AnalysisResult(task_cluster="test", traces_analyzed=10)
        assert r.patterns == []
        assert r.optimal_path is None

"""Tests for suggestion generation."""

from __future__ import annotations

from analysis.models import OptimalPath, PatternAnomaly, WorkflowTrace
from analysis.suggestions import (
    _suggest_from_pattern,
    _suggest_reordering,
    _suggest_skip_steps,
    generate_suggestions,
)
from tests.conftest import make_event


def _trace(
    wf_id: str = "wf-1",
    tools: list[str] | None = None,
    duration: float = 1000.0,
) -> WorkflowTrace:
    tools = tools or ["a", "b", "c"]
    events = [
        make_event(workflow_id=wf_id, tool_name=t, step_number=i + 1, duration_ms=200.0)
        for i, t in enumerate(tools)
    ]
    return WorkflowTrace(
        workflow_id=wf_id,
        events=events,
        tool_sequence=tools,
        total_duration_ms=duration,
        total_steps=len(tools),
        success=True,
    )


def _optimal(tools: list[str] | None = None) -> OptimalPath:
    tools = tools or ["a", "b", "c"]
    return OptimalPath(
        task_cluster="test",
        tool_sequence=tools,
        avg_duration_ms=800.0,
        success_rate=0.95,
        execution_count=10,
    )


# ── _suggest_from_pattern ────────────────────────────────────────────

class TestSuggestFromPattern:
    def test_redundant_step(self) -> None:
        p = PatternAnomaly(
            pattern_type="redundant_step",
            description="Tool 'a' called 3 times",
            tool_name="a",
            evidence={"avg_duration_ms": 150.0},
        )
        s = _suggest_from_pattern(p)
        assert s.suggestion_type == "skip_step"
        assert s.priority == "high"
        assert s.estimated_saving_ms == 150.0

    def test_retry_loop(self) -> None:
        p = PatternAnomaly(
            pattern_type="retry_loop",
            description="Tool 'b' retried",
            tool_name="b",
        )
        s = _suggest_from_pattern(p)
        assert s.suggestion_type == "fix_reliability"
        assert s.priority == "high"

    def test_bottleneck(self) -> None:
        p = PatternAnomaly(
            pattern_type="bottleneck",
            description="Tool 'c' is slow",
            tool_name="c",
        )
        s = _suggest_from_pattern(p)
        assert s.suggestion_type == "optimize_step"
        assert s.priority == "medium"

    def test_conformance_deviation(self) -> None:
        p = PatternAnomaly(
            pattern_type="conformance_deviation",
            description="Extra step found",
        )
        s = _suggest_from_pattern(p)
        assert s.suggestion_type == "remove_step"

    def test_unknown_type(self) -> None:
        p = PatternAnomaly(pattern_type="other", description="Something")
        s = _suggest_from_pattern(p)
        assert s.suggestion_type == "general"
        assert s.priority == "low"


# ── _suggest_reordering ──────────────────────────────────────────────

class TestSuggestReordering:
    def test_reorder_when_same_tools_different_order(self) -> None:
        trace = _trace(tools=["b", "a", "c"])
        optimal = _optimal(tools=["a", "b", "c"])
        s = _suggest_reordering(trace, optimal)
        assert s is not None
        assert s.suggestion_type == "reorder"

    def test_no_reorder_when_same_order(self) -> None:
        trace = _trace(tools=["a", "b", "c"])
        optimal = _optimal(tools=["a", "b", "c"])
        assert _suggest_reordering(trace, optimal) is None

    def test_no_reorder_different_tools(self) -> None:
        trace = _trace(tools=["a", "b"])
        optimal = _optimal(tools=["x", "y"])
        assert _suggest_reordering(trace, optimal) is None

    def test_empty_sequences(self) -> None:
        trace = _trace(tools=[])
        trace.tool_sequence = []
        optimal = _optimal(tools=[])
        optimal.tool_sequence = []
        assert _suggest_reordering(trace, optimal) is None


# ── _suggest_skip_steps ──────────────────────────────────────────────

class TestSuggestSkipSteps:
    def test_finds_extra_tools(self) -> None:
        trace = _trace(tools=["a", "b", "c", "d"])
        optimal = _optimal(tools=["a", "b", "c"])
        skips = _suggest_skip_steps(trace, optimal)
        assert len(skips) == 1
        assert skips[0].affected_tools == ["d"]

    def test_no_extras(self) -> None:
        trace = _trace(tools=["a", "b"])
        optimal = _optimal(tools=["a", "b", "c"])
        assert _suggest_skip_steps(trace, optimal) == []


# ── generate_suggestions ─────────────────────────────────────────────

class TestGenerateSuggestions:
    def test_pattern_suggestions(self) -> None:
        patterns = [
            PatternAnomaly(pattern_type="bottleneck", description="slow tool",
                           tool_name="a"),
        ]
        result = generate_suggestions(patterns, None, [])
        assert len(result) == 1
        assert result[0].suggestion_type == "optimize_step"

    def test_with_optimal_path(self) -> None:
        trace = _trace(tools=["a", "b", "c", "extra"])
        optimal = _optimal(tools=["a", "b", "c"])
        result = generate_suggestions([], optimal, [trace])
        types = {s.suggestion_type for s in result}
        assert "skip_step" in types

    def test_empty(self) -> None:
        assert generate_suggestions([], None, []) == []

    def test_deduplicates_skip_suggestions(self) -> None:
        t1 = _trace(wf_id="wf-1", tools=["a", "b", "extra"])
        t2 = _trace(wf_id="wf-2", tools=["a", "b", "extra"])
        optimal = _optimal(tools=["a", "b"])
        result = generate_suggestions([], optimal, [t1, t2])
        skip_tools = [s.affected_tools[0] for s in result if s.suggestion_type == "skip_step"]
        assert skip_tools == ["extra"]  # only one, not duplicated

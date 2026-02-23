"""Tests for pattern detection (conformance + custom detectors)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from analysis.models import WorkflowTrace
from analysis.patterns import (
    check_conformance,
    detect_bottlenecks,
    detect_patterns,
    detect_redundant_steps,
    detect_retry_loops,
)
from tests.conftest import make_event


def _trace(
    wf_id: str = "wf-1",
    tools: list[str] | None = None,
    durations: list[float] | None = None,
    statuses: list[str] | None = None,
    success: bool = True,
) -> WorkflowTrace:
    tools = tools or ["a", "b"]
    durations = durations or [100.0] * len(tools)
    statuses = statuses or ["success"] * len(tools)
    events = [
        make_event(
            workflow_id=wf_id,
            tool_name=t,
            step_number=i + 1,
            duration_ms=durations[i],
            status=statuses[i],
        )
        for i, t in enumerate(tools)
    ]
    return WorkflowTrace(
        workflow_id=wf_id,
        events=events,
        tool_sequence=tools,
        total_duration_ms=sum(durations),
        total_steps=len(tools),
        success=success,
    )


# ── check_conformance ────────────────────────────────────────────────

class TestCheckConformance:
    def test_returns_empty_for_empty_traces(self) -> None:
        assert check_conformance([], MagicMock(), MagicMock(), MagicMock()) == []

    @patch.dict("sys.modules", {"pm4py": MagicMock()})
    def test_detects_deviations(self) -> None:
        import sys

        mock_pm4py = sys.modules["pm4py"]
        mock_pm4py.format_dataframe.return_value = MagicMock(empty=False)
        mock_pm4py.conformance_diagnostics_token_based_replay.return_value = [
            {"missing_tokens": 2, "remaining_tokens": 1},
            {"missing_tokens": 0, "remaining_tokens": 0},  # conforming
        ]

        result = check_conformance(
            [_trace()], MagicMock(), MagicMock(), MagicMock()
        )
        assert len(result) == 1
        assert result[0].pattern_type == "conformance_deviation"
        assert result[0].evidence["missing"] == 2

    def test_returns_empty_on_exception(self) -> None:
        with patch.dict("sys.modules", {"pm4py": MagicMock()}) as _:
            import sys

            sys.modules["pm4py"].format_dataframe.side_effect = RuntimeError("fail")
            assert check_conformance(
                [_trace()], MagicMock(), MagicMock(), MagicMock()
            ) == []


# ── detect_redundant_steps ───────────────────────────────────────────

class TestDetectRedundantSteps:
    def test_finds_redundant_tools(self) -> None:
        t = _trace(tools=["a", "b", "a"])
        result = detect_redundant_steps([t], min_calls=2)
        assert len(result) == 1
        assert result[0].tool_name == "a"
        assert result[0].pattern_type == "redundant_step"

    def test_no_redundancy(self) -> None:
        t = _trace(tools=["a", "b", "c"])
        assert detect_redundant_steps([t]) == []

    def test_deduplicates_across_traces(self) -> None:
        t1 = _trace(wf_id="wf-1", tools=["a", "a"])
        t2 = _trace(wf_id="wf-2", tools=["a", "a"])
        result = detect_redundant_steps([t1, t2])
        assert len(result) == 1  # same tool only reported once


# ── detect_retry_loops ───────────────────────────────────────────────

class TestDetectRetryLoops:
    def test_finds_retry_after_failure(self) -> None:
        t = _trace(
            tools=["a", "a", "b"],
            statuses=["failure", "success", "success"],
            durations=[100.0, 100.0, 100.0],
        )
        result = detect_retry_loops([t])
        assert len(result) == 1
        assert result[0].pattern_type == "retry_loop"
        assert result[0].tool_name == "a"

    def test_no_retry_without_failure(self) -> None:
        t = _trace(tools=["a", "a"], statuses=["success", "success"])
        assert detect_retry_loops([t]) == []

    def test_no_retry_different_tools(self) -> None:
        t = _trace(tools=["a", "b"], statuses=["failure", "success"])
        assert detect_retry_loops([t]) == []


# ── detect_bottlenecks ───────────────────────────────────────────────

class TestDetectBottlenecks:
    def test_finds_bottleneck(self) -> None:
        t = _trace(tools=["a", "b"], durations=[900.0, 100.0])
        result = detect_bottlenecks([t], threshold_pct=0.40)
        assert len(result) == 1
        assert result[0].tool_name == "a"
        assert result[0].pattern_type == "bottleneck"

    def test_no_bottleneck(self) -> None:
        t = _trace(tools=["a", "b", "c"], durations=[100.0, 100.0, 100.0])
        result = detect_bottlenecks([t], threshold_pct=0.40)
        assert result == []

    def test_empty_traces(self) -> None:
        assert detect_bottlenecks([]) == []

    def test_zero_duration_traces(self) -> None:
        t = _trace(tools=["a"], durations=[0.0])
        t.total_duration_ms = 0.0
        assert detect_bottlenecks([t]) == []


# ── detect_patterns (combiner) ───────────────────────────────────────

class TestDetectPatterns:
    def test_combines_all_detectors(self) -> None:
        t = _trace(
            tools=["a", "a", "b"],
            durations=[900.0, 900.0, 100.0],
            statuses=["failure", "success", "success"],
        )
        patterns = detect_patterns([t], None, None, None)
        types = {p.pattern_type for p in patterns}
        assert "redundant_step" in types
        assert "retry_loop" in types
        assert "bottleneck" in types

    def test_no_conformance_without_model(self) -> None:
        t = _trace()
        patterns = detect_patterns([t], None, None, None)
        assert all(p.pattern_type != "conformance_deviation" for p in patterns)

    def test_uses_settings(self) -> None:
        settings = MagicMock()
        settings.redundancy_min_calls = 5
        settings.bottleneck_threshold_pct = 0.99

        t = _trace(tools=["a", "a", "b"], durations=[500.0, 500.0, 100.0])
        patterns = detect_patterns([t], None, None, None, settings=settings)
        # With min_calls=5, "a" (called 2x) should NOT trigger redundancy
        assert all(p.pattern_type != "redundant_step" for p in patterns)

"""Tests for failure warning extraction (ACE-inspired enriched hints)."""

from __future__ import annotations

from analysis.failure_warnings import (
    MAX_WARNINGS,
    _collect_param_values,
    _missing_step_warnings,
    _parameter_divergence_warnings,
    extract_failure_warnings,
)
from analysis.models import OptimalPath, WorkflowTrace

from .conftest import make_event


def _make_trace(
    wf_id: str,
    tool_sequence: list[str],
    success: bool,
    events: list | None = None,
) -> WorkflowTrace:
    """Build a minimal WorkflowTrace."""
    return WorkflowTrace(
        workflow_id=wf_id,
        tool_sequence=tool_sequence,
        success=success,
        events=events or [],
        total_duration_ms=1000.0,
        total_steps=len(tool_sequence),
    )


def _make_optimal_path(tool_sequence: list[str]) -> OptimalPath:
    return OptimalPath(task_cluster="test", tool_sequence=tool_sequence)


# ---------------------------------------------------------------------------
# extract_failure_warnings — top-level
# ---------------------------------------------------------------------------


class TestExtractFailureWarnings:
    def test_returns_empty_when_no_failures(self) -> None:
        traces = [_make_trace("wf-1", ["a", "b"], success=True)]
        path = _make_optimal_path(["a", "b"])
        assert extract_failure_warnings(traces, path) == []

    def test_returns_empty_when_no_successes(self) -> None:
        traces = [_make_trace("wf-1", ["a"], success=False)]
        path = _make_optimal_path(["a", "b"])
        assert extract_failure_warnings(traces, path) == []

    def test_returns_empty_when_all_traces_same(self) -> None:
        """No warnings when failures have the same tools as successes."""
        successes = [_make_trace(f"s-{i}", ["a", "b", "c"], True) for i in range(5)]
        failures = [_make_trace(f"f-{i}", ["a", "b", "c"], False) for i in range(3)]
        path = _make_optimal_path(["a", "b", "c"])
        assert extract_failure_warnings(successes + failures, path) == []

    def test_detects_missing_step(self) -> None:
        """Tool present in successes but absent in most failures → warning."""
        successes = [_make_trace(f"s-{i}", ["a", "b", "c"], True) for i in range(5)]
        failures = [_make_trace(f"f-{i}", ["a", "b"], False) for i in range(4)]
        path = _make_optimal_path(["a", "b", "c"])

        warnings = extract_failure_warnings(successes + failures, path)
        assert len(warnings) == 1
        assert "c" in warnings[0]
        assert "missing" in warnings[0].lower()
        assert "4/4" in warnings[0]

    def test_caps_at_max_warnings(self) -> None:
        """Never returns more than MAX_WARNINGS."""
        successes = [
            _make_trace(f"s-{i}", ["a", "b", "c", "d", "e"], True) for i in range(5)
        ]
        failures = [_make_trace(f"f-{i}", ["a"], False) for i in range(5)]
        path = _make_optimal_path(["a", "b", "c", "d", "e"])

        warnings = extract_failure_warnings(successes + failures, path)
        assert len(warnings) <= MAX_WARNINGS

    def test_mixed_missing_and_param_divergence(self) -> None:
        """Combines both missing-step and parameter divergence warnings."""
        s_events = [
            make_event(tool_name="pick", step_number=1,
                       tool_parameters={"warehouse": "west"}),
        ]
        f_events = [
            make_event(tool_name="pick", step_number=1,
                       tool_parameters={"warehouse": "east"}),
        ]

        successes = [
            WorkflowTrace(
                workflow_id=f"s-{i}", tool_sequence=["pick", "submit"],
                success=True, events=s_events, total_duration_ms=100.0, total_steps=2,
            )
            for i in range(5)
        ]
        failures = [
            WorkflowTrace(
                workflow_id=f"f-{i}", tool_sequence=["pick"],
                success=False, events=f_events, total_duration_ms=100.0, total_steps=1,
            )
            for i in range(5)
        ]
        path = _make_optimal_path(["pick", "submit"])

        warnings = extract_failure_warnings(successes + failures, path)
        assert len(warnings) >= 1
        texts = " ".join(warnings)
        # Should mention submit missing and/or warehouse divergence
        assert "submit" in texts or "warehouse" in texts


# ---------------------------------------------------------------------------
# _missing_step_warnings
# ---------------------------------------------------------------------------


class TestMissingStepWarnings:
    def test_no_warnings_when_all_tools_present(self) -> None:
        successes = [_make_trace(f"s-{i}", ["a", "b"], True) for i in range(5)]
        failures = [_make_trace(f"f-{i}", ["a", "b"], False) for i in range(3)]
        path = _make_optimal_path(["a", "b"])
        assert _missing_step_warnings(successes, failures, path) == []

    def test_warns_when_tool_missing_in_majority_of_failures(self) -> None:
        successes = [_make_trace(f"s-{i}", ["a", "b", "c"], True) for i in range(4)]
        failures = [_make_trace(f"f-{i}", ["a", "b"], False) for i in range(3)]
        path = _make_optimal_path(["a", "b", "c"])

        warnings = _missing_step_warnings(successes, failures, path)
        assert len(warnings) == 1
        assert "c" in warnings[0]
        assert "3/3" in warnings[0]

    def test_no_warning_when_only_one_failure_missing(self) -> None:
        """Threshold requires >=2 failures missing the tool."""
        successes = [_make_trace(f"s-{i}", ["a", "b"], True) for i in range(5)]
        failures = [
            _make_trace("f-0", ["a"], False),
            _make_trace("f-1", ["a", "b"], False),
            _make_trace("f-2", ["a", "b"], False),
        ]
        path = _make_optimal_path(["a", "b"])

        warnings = _missing_step_warnings(successes, failures, path)
        # 1/3 missing < 40% threshold → no warning
        assert len(warnings) == 0

    def test_warns_for_multiple_missing_tools(self) -> None:
        successes = [_make_trace(f"s-{i}", ["a", "b", "c"], True) for i in range(5)]
        failures = [_make_trace(f"f-{i}", ["a"], False) for i in range(5)]
        path = _make_optimal_path(["a", "b", "c"])

        warnings = _missing_step_warnings(successes, failures, path)
        assert len(warnings) == 2
        tools_warned = {w.split(" ")[0] for w in warnings}
        assert tools_warned == {"b", "c"}


# ---------------------------------------------------------------------------
# _parameter_divergence_warnings
# ---------------------------------------------------------------------------


class TestParameterDivergenceWarnings:
    def test_no_warnings_without_events(self) -> None:
        """No events → nothing to compare."""
        successes = [_make_trace("s-0", ["a"], True)]
        failures = [_make_trace("f-0", ["a"], False)]
        path = _make_optimal_path(["a"])
        assert _parameter_divergence_warnings(successes, failures, path) == []

    def test_detects_dominant_value_divergence(self) -> None:
        s_events = [
            make_event(tool_name="route", step_number=1,
                       tool_parameters={"warehouse": "west"}),
        ]
        f_events = [
            make_event(tool_name="route", step_number=1,
                       tool_parameters={"warehouse": "east"}),
        ]
        successes = [
            WorkflowTrace(
                workflow_id=f"s-{i}", tool_sequence=["route"], success=True,
                events=s_events, total_duration_ms=100.0, total_steps=1,
            )
            for i in range(4)
        ]
        failures = [
            WorkflowTrace(
                workflow_id=f"f-{i}", tool_sequence=["route"], success=False,
                events=f_events, total_duration_ms=100.0, total_steps=1,
            )
            for i in range(3)
        ]
        path = _make_optimal_path(["route"])

        warnings = _parameter_divergence_warnings(successes, failures, path)
        assert len(warnings) == 1
        assert "warehouse" in warnings[0]
        assert "west" in warnings[0]
        assert "east" in warnings[0]

    def test_no_warning_when_same_dominant_value(self) -> None:
        events = [
            make_event(tool_name="route", step_number=1,
                       tool_parameters={"warehouse": "west"}),
        ]
        successes = [
            WorkflowTrace(
                workflow_id=f"s-{i}", tool_sequence=["route"], success=True,
                events=events, total_duration_ms=100.0, total_steps=1,
            )
            for i in range(4)
        ]
        failures = [
            WorkflowTrace(
                workflow_id=f"f-{i}", tool_sequence=["route"], success=False,
                events=events, total_duration_ms=100.0, total_steps=1,
            )
            for i in range(3)
        ]
        path = _make_optimal_path(["route"])

        assert _parameter_divergence_warnings(successes, failures, path) == []


# ---------------------------------------------------------------------------
# _collect_param_values
# ---------------------------------------------------------------------------


class TestCollectParamValues:
    def test_empty_traces(self) -> None:
        assert _collect_param_values([], "any_tool") == {}

    def test_collects_matching_tool_params(self) -> None:
        events = [
            make_event(tool_name="pick", step_number=1,
                       tool_parameters={"size": "large", "color": "red"}),
            make_event(tool_name="ship", step_number=2,
                       tool_parameters={"carrier": "ups"}),
        ]
        trace = WorkflowTrace(
            workflow_id="wf-1", tool_sequence=["pick", "ship"],
            success=True, events=events, total_duration_ms=100.0, total_steps=2,
        )
        values = _collect_param_values([trace], "pick")
        assert set(values.keys()) == {"size", "color"}
        assert values["size"] == ["large"]
        assert values["color"] == ["red"]

    def test_ignores_non_matching_tools(self) -> None:
        events = [
            make_event(tool_name="ship", step_number=1,
                       tool_parameters={"carrier": "ups"}),
        ]
        trace = WorkflowTrace(
            workflow_id="wf-1", tool_sequence=["ship"],
            success=True, events=events, total_duration_ms=100.0, total_steps=1,
        )
        assert _collect_param_values([trace], "pick") == {}

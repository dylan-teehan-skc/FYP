"""Tests for decision tree generation from subcluster divergence."""

from __future__ import annotations

from analysis.decision_tree import (
    _dedup_consecutive,
    _dominant_value,
    _find_discriminating_key,
    _get_response_at_tool,
    _humanize,
    _label_from_suffix,
    build_decision_tree,
    find_divergence_point,
)
from analysis.models import WorkflowTrace
from tests.conftest import make_event


def _make_trace(
    wf_id: str,
    tools: list[str],
    *,
    success: bool = True,
    responses: dict[str, dict] | None = None,
) -> WorkflowTrace:
    """Helper to build a WorkflowTrace with optional tool responses."""
    events = []
    for i, tool in enumerate(tools):
        evt = make_event(
            workflow_id=wf_id,
            activity=f"tool_call:{tool}",
            tool_name=tool,
            step_number=i + 1,
        )
        if responses and tool in responses:
            evt.tool_response = responses[tool]
        events.append(evt)
    return WorkflowTrace(
        workflow_id=wf_id,
        events=events,
        tool_sequence=tools,
        total_duration_ms=len(tools) * 200.0,
        total_steps=len(tools),
        success=success,
    )


class TestHumanize:
    def test_basic(self) -> None:
        assert _humanize("check_ticket") == "Check ticket"

    def test_single_word(self) -> None:
        assert _humanize("refund") == "Refund"

    def test_already_clean(self) -> None:
        assert _humanize("Refund") == "Refund"


class TestDedupConsecutive:
    def test_no_duplicates(self) -> None:
        assert _dedup_consecutive(["a", "b", "c"]) == ["a", "b", "c"]

    def test_consecutive_duplicates(self) -> None:
        assert _dedup_consecutive(["a", "a", "b", "b", "c"]) == ["a", "b", "c"]

    def test_non_consecutive_duplicates_kept(self) -> None:
        assert _dedup_consecutive(["a", "b", "a"]) == ["a", "b", "a"]

    def test_empty(self) -> None:
        assert _dedup_consecutive([]) == []

    def test_single(self) -> None:
        assert _dedup_consecutive(["a"]) == ["a"]


class TestFindDivergencePoint:
    def test_common_prefix(self) -> None:
        seqs = [["a", "b", "c"], ["a", "b", "d"]]
        assert find_divergence_point(seqs) == ["a", "b"]

    def test_no_common_prefix(self) -> None:
        seqs = [["a", "b"], ["c", "d"]]
        assert find_divergence_point(seqs) == []

    def test_identical_sequences(self) -> None:
        seqs = [["a", "b"], ["a", "b"]]
        assert find_divergence_point(seqs) == ["a", "b"]

    def test_empty_input(self) -> None:
        assert find_divergence_point([]) == []

    def test_single_sequence(self) -> None:
        assert find_divergence_point([["a", "b"]]) == ["a", "b"]

    def test_three_sequences(self) -> None:
        seqs = [["a", "b", "x"], ["a", "b", "y"], ["a", "b", "z"]]
        assert find_divergence_point(seqs) == ["a", "b"]


class TestGetResponseAtTool:
    def test_extracts_response(self) -> None:
        trace = _make_trace(
            "wf-1", ["get_order", "fulfill"],
            responses={"get_order": {"status": "in_stock"}},
        )
        results = _get_response_at_tool([trace], "get_order")
        assert results == [{"status": "in_stock"}]

    def test_missing_tool(self) -> None:
        trace = _make_trace("wf-1", ["get_order"])
        results = _get_response_at_tool([trace], "nonexistent")
        assert results == []

    def test_no_response(self) -> None:
        trace = _make_trace("wf-1", ["get_order"])
        results = _get_response_at_tool([trace], "get_order")
        assert results == []

    def test_multiple_traces(self) -> None:
        t1 = _make_trace("wf-1", ["a"], responses={"a": {"x": 1}})
        t2 = _make_trace("wf-2", ["a"], responses={"a": {"x": 2}})
        results = _get_response_at_tool([t1, t2], "a")
        assert len(results) == 2


class TestFindDiscriminatingKey:
    def test_finds_separating_key(self) -> None:
        a = [{"status": "in_stock"}, {"status": "in_stock"}]
        b = [{"status": "backordered"}, {"status": "backordered"}]
        assert _find_discriminating_key(a, b) == "status"

    def test_no_separation(self) -> None:
        a = [{"status": "ok"}, {"status": "ok"}]
        b = [{"status": "ok"}, {"status": "ok"}]
        assert _find_discriminating_key(a, b) is None

    def test_empty_a(self) -> None:
        assert _find_discriminating_key([], [{"x": 1}]) is None

    def test_empty_b(self) -> None:
        assert _find_discriminating_key([{"x": 1}], []) is None

    def test_high_cardinality_skipped(self) -> None:
        a = [{"name": f"product_{i}"} for i in range(10)]
        b = [{"name": f"other_{i}"} for i in range(10)]
        assert _find_discriminating_key(a, b) is None

    def test_overlapping_values_skipped(self) -> None:
        a = [{"status": "ok"}, {"status": "fail"}]
        b = [{"status": "ok"}, {"status": "pending"}]
        assert _find_discriminating_key(a, b) is None

    def test_picks_most_consistent(self) -> None:
        a = [{"type": "A", "flag": "yes"}, {"type": "A", "flag": "yes"}]
        b = [{"type": "B", "flag": "no"}, {"type": "B", "flag": "no"}]
        key = _find_discriminating_key(a, b)
        assert key in ("type", "flag")


class TestDominantValue:
    def test_most_common(self) -> None:
        assert _dominant_value(["a", "b", "a"]) == "a"

    def test_empty(self) -> None:
        assert _dominant_value([]) is None

    def test_single(self) -> None:
        assert _dominant_value(["x"]) == "x"

    def test_returns_original_type(self) -> None:
        assert _dominant_value([1, 2, 1]) == 1


class TestLabelFromSuffix:
    def test_unique_tool(self) -> None:
        label = _label_from_suffix(
            ["fulfill", "ship"], [["backorder", "notify"]],
        )
        assert label in ("Fulfill", "Ship")

    def test_no_unique_tool(self) -> None:
        label = _label_from_suffix(["a", "b"], [["a", "b"]])
        assert label == "B"

    def test_empty_suffix(self) -> None:
        assert _label_from_suffix([], [["a"]]) == "Direct completion"


class TestBuildDecisionTree:
    def test_single_subcluster_returns_none(self) -> None:
        traces = [_make_trace("wf-1", ["a", "b"])]
        assert build_decision_tree({"sub_0": traces}) is None

    def test_two_subclusters_with_common_prefix(self) -> None:
        sub_a = [
            _make_trace("wf-1", ["get_order", "fulfill", "ship"]),
            _make_trace("wf-2", ["get_order", "fulfill", "ship"]),
        ]
        sub_b = [
            _make_trace("wf-3", ["get_order", "backorder", "notify"]),
            _make_trace("wf-4", ["get_order", "backorder", "notify"]),
        ]
        tree = build_decision_tree({"sub_a": sub_a, "sub_b": sub_b})
        assert tree is not None
        assert tree["branch_tool"] == "get_order"
        assert len(tree["branches"]) == 2
        assert "common_prefix" in tree
        assert "condition_question" in tree

    def test_no_common_prefix_returns_none(self) -> None:
        sub_a = [_make_trace("wf-1", ["x", "y"])]
        sub_b = [_make_trace("wf-2", ["a", "b"])]
        assert build_decision_tree({"sub_a": sub_a, "sub_b": sub_b}) is None

    def test_filters_zero_success_branches(self) -> None:
        sub_a = [
            _make_trace("wf-1", ["a", "b", "c"]),
            _make_trace("wf-2", ["a", "b", "c"]),
        ]
        sub_b = [
            _make_trace("wf-3", ["a", "b", "d"], success=False),
        ]
        tree = build_decision_tree({"sub_a": sub_a, "sub_b": sub_b})
        if tree:
            for branch in tree["branches"]:
                assert branch["success_rate"] > 0 or branch["execution_count"] >= 5

    def test_branches_sorted_by_execution_count(self) -> None:
        sub_a = [_make_trace(f"wf-{i}", ["a", "b", "c"]) for i in range(5)]
        sub_b = [_make_trace(f"wf-{i+10}", ["a", "b", "d"]) for i in range(2)]
        tree = build_decision_tree({"sub_a": sub_a, "sub_b": sub_b})
        assert tree is not None
        counts = [b["execution_count"] for b in tree["branches"]]
        assert counts == sorted(counts, reverse=True)

    def test_with_condition_key(self) -> None:
        sub_a = [
            _make_trace(
                "wf-1", ["get_order", "fulfill"],
                responses={"get_order": {"status": "in_stock"}},
            ),
            _make_trace(
                "wf-2", ["get_order", "fulfill"],
                responses={"get_order": {"status": "in_stock"}},
            ),
        ]
        sub_b = [
            _make_trace(
                "wf-3", ["get_order", "backorder"],
                responses={"get_order": {"status": "backordered"}},
            ),
            _make_trace(
                "wf-4", ["get_order", "backorder"],
                responses={"get_order": {"status": "backordered"}},
            ),
        ]
        tree = build_decision_tree({"sub_a": sub_a, "sub_b": sub_b})
        assert tree is not None
        assert tree.get("condition_key") == "status"

    def test_three_subclusters(self) -> None:
        sub_a = [_make_trace(f"wf-a{i}", ["a", "b", "c"]) for i in range(3)]
        sub_b = [_make_trace(f"wf-b{i}", ["a", "b", "d"]) for i in range(3)]
        sub_c = [_make_trace(f"wf-c{i}", ["a", "b", "e"]) for i in range(3)]
        tree = build_decision_tree({
            "sub_a": sub_a, "sub_b": sub_b, "sub_c": sub_c,
        })
        assert tree is not None
        assert len(tree["branches"]) == 3

    def test_all_branches_filtered_returns_none(self) -> None:
        sub_a = [_make_trace("wf-1", ["a", "b", "c"], success=False)]
        sub_b = [_make_trace("wf-2", ["a", "b", "d"], success=False)]
        tree = build_decision_tree({"sub_a": sub_a, "sub_b": sub_b})
        assert tree is None

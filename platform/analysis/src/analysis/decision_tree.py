"""Auto-generate decision trees from subcluster divergence analysis."""

from __future__ import annotations

from collections import Counter
from typing import Any

from analysis.logger import get_logger
from analysis.models import WorkflowTrace

log = get_logger("analysis.decision_tree")


def _humanize(tool_name: str) -> str:
    """Convert tool_name to a readable label."""
    return tool_name.replace("_", " ").capitalize()


def _dedup_consecutive(seq: list[str]) -> list[str]:
    """Collapse consecutive duplicate tool calls."""
    return [t for i, t in enumerate(seq) if i == 0 or t != seq[i - 1]]


def find_divergence_point(sequences: list[list[str]]) -> list[str]:
    """Find the longest common prefix across all tool sequences."""
    if not sequences:
        return []
    prefix = []
    for tools_at_pos in zip(*sequences):
        if len(set(tools_at_pos)) == 1:
            prefix.append(tools_at_pos[0])
        else:
            break
    return prefix


def _get_response_at_tool(
    traces: list[WorkflowTrace], tool_name: str,
) -> list[dict[str, Any]]:
    """Extract the tool_response for a specific tool across all traces."""
    responses = []
    for trace in traces:
        for event in trace.events:
            if event.activity == f"tool_call:{tool_name}" and event.tool_response:
                responses.append(event.tool_response)
                break
    return responses


def _find_discriminating_key(
    responses_a: list[dict[str, Any]],
    responses_b: list[dict[str, Any]],
) -> str | None:
    """Find the response key whose value differs most between two groups."""
    if not responses_a or not responses_b:
        return None

    all_keys: set[str] = set()
    for r in responses_a + responses_b:
        all_keys.update(r.keys())

    best_key = None
    best_separation = 0.0

    for key in all_keys:
        vals_a = [r.get(key) for r in responses_a if key in r]
        vals_b = [r.get(key) for r in responses_b if key in r]
        if not vals_a or not vals_b:
            continue

        unique_a = set(str(v) for v in vals_a)
        unique_b = set(str(v) for v in vals_b)

        # Good discriminator: values in A are disjoint from values in B
        if unique_a & unique_b:
            continue

        total_unique = len(unique_a | unique_b)
        if total_unique > 5:
            continue

        # Skip high-cardinality keys (entity identifiers like name, IDs)
        total_values = len(vals_a) + len(vals_b)
        if total_values > 0 and total_unique / total_values > 0.5:
            continue

        # Score: how consistently does this key separate the groups?
        consistency_a = max(Counter(str(v) for v in vals_a).values()) / len(vals_a)
        consistency_b = max(Counter(str(v) for v in vals_b).values()) / len(vals_b)
        separation = (consistency_a + consistency_b) / 2

        if separation > best_separation:
            best_separation = separation
            best_key = key

    return best_key


def _dominant_value(values: list[Any]) -> Any:
    """Return the most common value in a list."""
    if not values:
        return None
    counter = Counter(str(v) for v in values)
    most_common_str = counter.most_common(1)[0][0]
    for v in values:
        if str(v) == most_common_str:
            return v
    return values[0]


def _label_from_suffix(
    suffix: list[str], other_suffixes: list[list[str]],
) -> str:
    """Derive a branch label from the tools in this branch."""
    other_tools = {t for s in other_suffixes for t in s}
    # Prefer a tool unique to this branch
    for tool in reversed(suffix):
        if tool not in other_tools:
            return _humanize(tool)
    # Fall back to the last tool in the suffix
    if suffix:
        return _humanize(suffix[-1])
    return "Direct completion"


def build_decision_tree(
    subclusters: dict[str, list[WorkflowTrace]],
) -> dict[str, Any] | None:
    """Build a decision tree from subclusters that diverge at a branching point."""
    if len(subclusters) < 2:
        return None

    sub_items = list(subclusters.items())
    sequences = []
    for _, traces in sub_items:
        seq_counts: Counter[tuple[str, ...]] = Counter()
        for t in traces:
            seq_counts[tuple(t.tool_sequence)] += 1
        most_common = seq_counts.most_common(1)[0][0]
        sequences.append(list(most_common))

    common_prefix = find_divergence_point(sequences)

    if not common_prefix:
        log.info("no_common_prefix", subclusters=len(subclusters))
        return None

    branch_tool = common_prefix[-1]

    # Try to find the discriminating condition in the branch tool's response
    all_responses_per_sub = []
    for _, traces in sub_items:
        responses = _get_response_at_tool(traces, branch_tool)
        all_responses_per_sub.append(responses)

    condition_key = None
    if len(all_responses_per_sub) == 2:
        condition_key = _find_discriminating_key(
            all_responses_per_sub[0], all_responses_per_sub[1],
        )
    else:
        key_votes: Counter[str] = Counter()
        for i in range(len(all_responses_per_sub)):
            for j in range(i + 1, len(all_responses_per_sub)):
                key = _find_discriminating_key(
                    all_responses_per_sub[i], all_responses_per_sub[j],
                )
                if key:
                    key_votes[key] += 1
        if key_votes:
            condition_key = key_votes.most_common(1)[0][0]

    # Build the branches
    branches = []
    suffixes = []
    for idx, ((sub_label, traces), seq, responses) in enumerate(
        zip(sub_items, sequences, all_responses_per_sub)
    ):
        suffix = _dedup_consecutive(seq[len(common_prefix):])
        suffixes.append(suffix)

        branch: dict[str, Any] = {
            "path": suffix,
            "execution_count": len(traces),
            "success_rate": (
                sum(1 for t in traces if t.success) / len(traces)
                if traces else 0.0
            ),
        }

        if condition_key and responses:
            values = [r.get(condition_key) for r in responses if condition_key in r]
            dominant = _dominant_value(values)
            branch["condition_value"] = dominant
            branch["label"] = f"{condition_key}={dominant}"
        else:
            branch["label"] = f"variant {idx + 1}"

        branches.append(branch)

    # Derive labels from distinguishing tools when no good condition key
    for idx, branch in enumerate(branches):
        other = [s for j, s in enumerate(suffixes) if j != idx]
        branch["label"] = _label_from_suffix(suffixes[idx], other)

    # Filter out 0% success branches (noise) unless they have significant data
    branches = [
        b for b in branches
        if b["success_rate"] > 0 or b["execution_count"] >= 5
    ]

    if not branches:
        return None

    # Sort branches: highest execution count first (primary = most common)
    branches.sort(key=lambda b: b["execution_count"], reverse=True)

    tree: dict[str, Any] = {
        "common_prefix": _dedup_consecutive(common_prefix),
        "branch_tool": branch_tool,
        "condition_question": f"Based on {_humanize(branch_tool)} result?",
        "branches": branches,
    }
    if condition_key:
        tree["condition_key"] = condition_key

    log.info(
        "decision_tree_built",
        branch_tool=branch_tool,
        condition_key=condition_key,
        branches=len(branches),
    )
    return tree

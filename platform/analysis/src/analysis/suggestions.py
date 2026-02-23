"""Human-readable optimization suggestion generation."""

from __future__ import annotations

from analysis.logger import get_logger
from analysis.models import OptimalPath, PatternAnomaly, Suggestion, WorkflowTrace

log = get_logger("analysis.suggestions")


def _suggest_from_pattern(pattern: PatternAnomaly) -> Suggestion:
    """Convert a single PatternAnomaly into a Suggestion."""
    type_map = {
        "redundant_step": ("skip_step", "high"),
        "retry_loop": ("fix_reliability", "high"),
        "bottleneck": ("optimize_step", "medium"),
        "conformance_deviation": ("remove_step", "medium"),
    }
    stype, priority = type_map.get(pattern.pattern_type, ("general", "low"))

    saving = pattern.evidence.get("avg_duration_ms", 0.0)

    return Suggestion(
        suggestion_type=stype,
        message=pattern.description,
        priority=priority,
        affected_tools=[pattern.tool_name] if pattern.tool_name else [],
        estimated_saving_ms=saving,
    )


def _suggest_reordering(
    trace: WorkflowTrace,
    optimal_path: OptimalPath,
) -> Suggestion | None:
    """If trace tools match optimal but in different order, suggest reordering."""
    if not trace.tool_sequence or not optimal_path.tool_sequence:
        return None

    trace_set = set(trace.tool_sequence)
    optimal_set = set(optimal_path.tool_sequence)

    # Same tools, different order
    if trace_set == optimal_set and trace.tool_sequence != optimal_path.tool_sequence:
        return Suggestion(
            suggestion_type="reorder",
            message=(
                f"Reorder tools in workflow {trace.workflow_id}: "
                f"current [{' → '.join(trace.tool_sequence)}] "
                f"→ optimal [{' → '.join(optimal_path.tool_sequence)}]"
            ),
            priority="medium",
            affected_tools=list(trace_set),
            estimated_saving_ms=max(
                0, trace.total_duration_ms - optimal_path.avg_duration_ms
            ),
        )
    return None


def _suggest_skip_steps(
    trace: WorkflowTrace,
    optimal_path: OptimalPath,
) -> list[Suggestion]:
    """If trace has tools not in the optimal path, suggest skipping them."""
    if not trace.tool_sequence or not optimal_path.tool_sequence:
        return []

    extra = set(trace.tool_sequence) - set(optimal_path.tool_sequence)
    suggestions = []
    for tool in extra:
        # Estimate saving from this tool's average duration in the trace
        tool_durations = [
            e.duration_ms for e in trace.events if e.tool_name == tool
        ]
        avg_saving = sum(tool_durations) / len(tool_durations) if tool_durations else 0.0

        suggestions.append(Suggestion(
            suggestion_type="skip_step",
            message=f"Tool '{tool}' not in optimal path — consider removing",
            priority="medium",
            affected_tools=[tool],
            estimated_saving_ms=avg_saving,
        ))
    return suggestions


def generate_suggestions(
    patterns: list[PatternAnomaly],
    optimal_path: OptimalPath | None,
    traces: list[WorkflowTrace],
) -> list[Suggestion]:
    """Generate actionable suggestions from patterns and optimal path comparison."""
    suggestions = []

    # Convert each pattern to a suggestion
    for pattern in patterns:
        suggestions.append(_suggest_from_pattern(pattern))

    # Compare traces against optimal path
    if optimal_path:
        seen_reorder = False
        for trace in traces:
            if not seen_reorder:
                reorder = _suggest_reordering(trace, optimal_path)
                if reorder:
                    suggestions.append(reorder)
                    seen_reorder = True

            skips = _suggest_skip_steps(trace, optimal_path)
            # Only add unique skip suggestions
            existing_tools = {s.affected_tools[0] for s in suggestions
                              if s.suggestion_type == "skip_step" and s.affected_tools}
            for skip in skips:
                if skip.affected_tools and skip.affected_tools[0] not in existing_tools:
                    suggestions.append(skip)
                    existing_tools.add(skip.affected_tools[0])

    log.info("suggestions_generated", count=len(suggestions))
    return suggestions

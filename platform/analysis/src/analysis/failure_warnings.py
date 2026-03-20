"""Extract failure warnings from traces to enrich guided-mode hints."""

from __future__ import annotations

from collections import Counter

from analysis.logger import get_logger
from analysis.models import OptimalPath, WorkflowTrace

log = get_logger("analysis.failure_warnings")

MAX_WARNINGS = 3


def extract_failure_warnings(
    traces: list[WorkflowTrace],
    optimal_path: OptimalPath,
) -> list[str]:
    """Compare successful and failed traces to surface actionable failure patterns.

    Returns up to MAX_WARNINGS concise natural-language warnings that can be
    appended to the guided-mode hint.
    """
    successful = [t for t in traces if t.success]
    failed = [t for t in traces if not t.success]

    if not failed or not successful:
        return []

    warnings: list[str] = []

    # --- 1. Missing-step warnings ---
    # Tools present in the optimal path but frequently absent in failed traces.
    warnings.extend(_missing_step_warnings(successful, failed, optimal_path))

    # --- 2. Parameter divergence warnings ---
    # Tools where successful runs consistently use a different parameter value
    # than failed runs (e.g. warehouse selection).
    warnings.extend(_parameter_divergence_warnings(successful, failed, optimal_path))

    if warnings:
        log.info(
            "failure_warnings_extracted",
            count=len(warnings[:MAX_WARNINGS]),
            total_failed=len(failed),
            total_successful=len(successful),
        )

    return warnings[:MAX_WARNINGS]


def _missing_step_warnings(
    successful: list[WorkflowTrace],
    failed: list[WorkflowTrace],
    optimal_path: OptimalPath,
) -> list[str]:
    """Find optimal-path tools that are present in successes but missing in failures."""
    warnings: list[str] = []
    optimal_tools = set(optimal_path.tool_sequence)

    for tool in optimal_path.tool_sequence:
        success_has = sum(1 for t in successful if tool in t.tool_sequence)
        fail_has = sum(1 for t in failed if tool in t.tool_sequence)
        fail_missing = len(failed) - fail_has

        success_pct = success_has / len(successful) if successful else 0
        fail_missing_pct = fail_missing / len(failed) if failed else 0

        # Tool appears in >70% of successes but is missing in >40% of failures
        if success_pct > 0.70 and fail_missing_pct > 0.40 and fail_missing >= 2:
            warnings.append(
                f"{tool} was missing in {fail_missing}/{len(failed)} failed runs "
                f"but present in {success_has}/{len(successful)} successful runs"
            )

    return warnings


def _parameter_divergence_warnings(
    successful: list[WorkflowTrace],
    failed: list[WorkflowTrace],
    optimal_path: OptimalPath,
) -> list[str]:
    """Find tools where successful runs consistently use a different param value."""
    warnings: list[str] = []

    for tool in optimal_path.tool_sequence:
        success_values = _collect_param_values(successful, tool)
        fail_values = _collect_param_values(failed, tool)

        if not success_values or not fail_values:
            continue

        # For each parameter key, check if there's a dominant value in successes
        # that differs from the dominant value in failures.
        for key in success_values:
            if key not in fail_values:
                continue

            s_counter = Counter(success_values[key])
            f_counter = Counter(fail_values[key])

            if not s_counter or not f_counter:
                continue

            s_top_value, s_top_count = s_counter.most_common(1)[0]
            f_top_value, f_top_count = f_counter.most_common(1)[0]

            s_dominance = s_top_count / sum(s_counter.values())
            f_dominance = f_top_count / sum(f_counter.values())

            # Dominant value in successes (>60%) differs from dominant value in failures
            if (
                s_dominance > 0.60
                and f_dominance > 0.40
                and str(s_top_value) != str(f_top_value)
            ):
                warnings.append(
                    f"at {tool}, successful runs used {key}={s_top_value} "
                    f"({s_top_count}/{sum(s_counter.values())} runs) "
                    f"while failed runs used {key}={f_top_value}"
                )

    return warnings


def _collect_param_values(
    traces: list[WorkflowTrace],
    tool_name: str,
) -> dict[str, list[str]]:
    """Collect parameter values for a specific tool across traces."""
    values: dict[str, list[str]] = {}
    for trace in traces:
        for event in trace.events:
            if event.tool_name == tool_name and event.tool_parameters:
                for key, val in event.tool_parameters.items():
                    values.setdefault(key, []).append(str(val))
    return values

"""Pattern detection: conformance checking + custom detectors."""

from __future__ import annotations

from collections import Counter
from typing import Any

from analysis.logger import get_logger
from analysis.models import PatternAnomaly, WorkflowTrace
from analysis.traces import traces_to_dataframe

log = get_logger("analysis.patterns")


def check_conformance(
    traces: list[WorkflowTrace],
    net: Any,
    im: Any,
    fm: Any,
) -> list[PatternAnomaly]:
    """Run PM4Py conformance checking against the normative model.

    Deviations from successful-run model = detected anti-patterns.
    """
    df = traces_to_dataframe(traces)
    if df.empty:
        return []

    try:
        import pm4py

        df = pm4py.format_dataframe(
            df,
            case_id="case:concept:name",
            activity_key="concept:name",
            timestamp_key="time:timestamp",
        )
        diagnostics = pm4py.conformance_diagnostics_token_based_replay(df, net, im, fm)

        anomalies = []
        for diag in diagnostics:
            missing = diag.get("missing_tokens", 0)
            remaining = diag.get("remaining_tokens", 0)
            if missing > 0 or remaining > 0:
                anomalies.append(PatternAnomaly(
                    pattern_type="conformance_deviation",
                    description=(
                        f"Trace deviates from optimal model: "
                        f"{missing} missing tokens, {remaining} remaining tokens"
                    ),
                    severity="medium",
                    evidence={"missing": missing, "remaining": remaining},
                ))
        return anomalies
    except Exception:
        log.warning("conformance_check_failed", exc_info=True)
        return []


def detect_redundant_steps(
    traces: list[WorkflowTrace],
    min_calls: int = 2,
) -> list[PatternAnomaly]:
    """Find tools called multiple times within the same trace."""
    anomalies = []
    seen_tools: set[str] = set()

    for trace in traces:
        counts = Counter(trace.tool_sequence)
        for tool, count in counts.items():
            if count >= min_calls and tool not in seen_tools:
                seen_tools.add(tool)
                anomalies.append(PatternAnomaly(
                    pattern_type="redundant_step",
                    description=(
                        f"Tool '{tool}' called {count} times in workflow "
                        f"{trace.workflow_id} (expected 1)"
                    ),
                    tool_name=tool,
                    severity="medium",
                    evidence={
                        "count": count,
                        "workflow_id": trace.workflow_id,
                    },
                ))
    return anomalies


def detect_retry_loops(traces: list[WorkflowTrace]) -> list[PatternAnomaly]:
    """Find tool retries: same tool called again after a failure status."""
    anomalies = []
    seen: set[str] = set()

    for trace in traces:
        events = sorted(trace.events, key=lambda e: (e.step_number, e.timestamp))
        for i in range(len(events) - 1):
            curr = events[i]
            nxt = events[i + 1]
            if (
                curr.tool_name is not None
                and curr.tool_name == nxt.tool_name
                and curr.status == "failure"
                and curr.tool_name not in seen
            ):
                seen.add(curr.tool_name)
                anomalies.append(PatternAnomaly(
                    pattern_type="retry_loop",
                    description=(
                        f"Tool '{curr.tool_name}' retried after failure "
                        f"in workflow {trace.workflow_id}"
                    ),
                    tool_name=curr.tool_name,
                    severity="high",
                    evidence={
                        "failure_step": curr.step_number,
                        "retry_step": nxt.step_number,
                        "workflow_id": trace.workflow_id,
                    },
                ))
    return anomalies


def detect_bottlenecks(
    traces: list[WorkflowTrace],
    threshold_pct: float = 0.40,
) -> list[PatternAnomaly]:
    """Find tools whose avg duration exceeds threshold_pct of total workflow duration."""
    if not traces:
        return []

    # Aggregate per-tool durations across all traces
    tool_durations: dict[str, list[float]] = {}
    total_durations: list[float] = []

    for trace in traces:
        if trace.total_duration_ms <= 0:
            continue
        total_durations.append(trace.total_duration_ms)
        for event in trace.events:
            if event.tool_name is not None:
                tool_durations.setdefault(event.tool_name, []).append(event.duration_ms)

    if not total_durations:
        return []

    avg_total = sum(total_durations) / len(total_durations)
    anomalies = []

    for tool, durations in tool_durations.items():
        avg_dur = sum(durations) / len(durations)
        pct = avg_dur / avg_total if avg_total > 0 else 0

        if pct >= threshold_pct:
            anomalies.append(PatternAnomaly(
                pattern_type="bottleneck",
                description=(
                    f"Tool '{tool}' avg {avg_dur:.0f}ms "
                    f"({pct:.0%} of total {avg_total:.0f}ms)"
                ),
                tool_name=tool,
                severity="high",
                evidence={
                    "avg_duration_ms": round(avg_dur, 1),
                    "pct_of_total": round(pct, 3),
                    "avg_total_ms": round(avg_total, 1),
                },
            ))

    return anomalies


def detect_patterns(
    traces: list[WorkflowTrace],
    net: Any | None,
    im: Any | None,
    fm: Any | None,
    settings: Any | None = None,
) -> list[PatternAnomaly]:
    """Run all pattern detectors and return combined results."""
    min_calls = getattr(settings, "redundancy_min_calls", 2)
    threshold_pct = getattr(settings, "bottleneck_threshold_pct", 0.40)

    patterns: list[PatternAnomaly] = []

    # PM4Py conformance checking (if model available)
    if net is not None and im is not None and fm is not None:
        patterns.extend(check_conformance(traces, net, im, fm))

    # Custom detectors
    patterns.extend(detect_redundant_steps(traces, min_calls=min_calls))
    patterns.extend(detect_retry_loops(traces))
    patterns.extend(detect_bottlenecks(traces, threshold_pct=threshold_pct))

    log.info("patterns_detected", count=len(patterns))
    return patterns

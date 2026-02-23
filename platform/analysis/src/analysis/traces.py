"""Trace reconstruction from event_logs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from analysis.logger import get_logger
from analysis.models import EventRecord, WorkflowTrace

if TYPE_CHECKING:
    from analysis.database import Database

log = get_logger("analysis.traces")


def extract_tool_sequence(events: list[EventRecord]) -> list[str]:
    """Extract the ordered list of tool names from events.

    Filters to events where tool_name is not None, ordered by step_number.
    """
    return [
        e.tool_name
        for e in sorted(events, key=lambda e: (e.step_number, e.timestamp))
        if e.tool_name is not None
    ]


def compute_trace_success(events: list[EventRecord]) -> bool:
    """A trace is successful if it has a workflow:complete event with status=success."""
    for e in events:
        if e.activity == "workflow:complete" and e.status == "success":
            return True
    return False


def compute_total_duration(events: list[EventRecord]) -> float:
    """Compute total duration from the workflow:complete event or sum of tool durations."""
    for e in events:
        if e.activity == "workflow:complete" and e.duration_ms > 0:
            return e.duration_ms
    return sum(e.duration_ms for e in events if e.tool_name is not None)


def compute_total_cost(events: list[EventRecord]) -> float:
    """Sum cost_usd across all events."""
    return sum(e.cost_usd for e in events)


async def reconstruct_trace(db: Database, workflow_id: str) -> WorkflowTrace:
    """Fetch events for one workflow and build a WorkflowTrace."""
    rows = await db.fetch_workflow_events(workflow_id)
    override_keys = {"event_id", "workflow_id", "parent_event_id", "cost_usd"}
    events = [
        EventRecord(
            **{k: v for k, v in dict(r).items() if k not in override_keys},
            event_id=str(r["event_id"]),
            workflow_id=str(r["workflow_id"]),
            parent_event_id=(
                str(r["parent_event_id"]) if r.get("parent_event_id") else None
            ),
            cost_usd=float(r.get("cost_usd", 0.0)),
        )
        for r in rows
    ]

    tool_seq = extract_tool_sequence(events)
    return WorkflowTrace(
        workflow_id=workflow_id,
        events=events,
        tool_sequence=tool_seq,
        total_duration_ms=compute_total_duration(events),
        total_cost_usd=compute_total_cost(events),
        total_steps=len(tool_seq),
        success=compute_trace_success(events),
    )


async def reconstruct_all_traces(db: Database) -> list[WorkflowTrace]:
    """Reconstruct traces for every workflow_id in the database."""
    workflow_ids = await db.fetch_all_workflow_ids()
    traces = []
    for wf_id in workflow_ids:
        trace = await reconstruct_trace(db, wf_id)
        traces.append(trace)
    log.info("traces_reconstructed", count=len(traces))
    return traces


def traces_to_dataframe(traces: list[WorkflowTrace]) -> pd.DataFrame:
    """Convert traces to a PM4Py-compatible DataFrame.

    Columns: case:concept:name, concept:name, time:timestamp
    """
    rows = []
    for trace in traces:
        for event in trace.events:
            if event.tool_name is not None:
                rows.append({
                    "case:concept:name": trace.workflow_id,
                    "concept:name": event.tool_name,
                    "time:timestamp": event.timestamp,
                })
    if not rows:
        return pd.DataFrame(
            columns=["case:concept:name", "concept:name", "time:timestamp"]
        )
    return pd.DataFrame(rows)

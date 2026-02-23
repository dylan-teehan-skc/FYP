"""Process discovery (PM4Py Inductive Miner) + networkx execution graph."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx

from analysis.logger import get_logger
from analysis.models import (
    ExecutionGraph,
    GraphEdge,
    ProcessMetrics,
    WorkflowTrace,
)
from analysis.traces import traces_to_dataframe

log = get_logger("analysis.graph")

START_NODE = "__START__"
END_NODE = "__END__"


def discover_process_model(traces: list[WorkflowTrace]) -> tuple[Any, Any, Any] | None:
    """Discover a Petri net using PM4Py's Inductive Miner.

    Uses only successful traces for the normative model.
    Returns (net, initial_marking, final_marking) or None on failure.
    """
    successful = [t for t in traces if t.success]
    if not successful:
        return None

    df = traces_to_dataframe(successful)
    if df.empty:
        return None

    try:
        import pm4py

        df = pm4py.format_dataframe(
            df,
            case_id="case:concept:name",
            activity_key="concept:name",
            timestamp_key="time:timestamp",
        )
        net, im, fm = pm4py.discover_petri_net_inductive(df)
        log.info("process_model_discovered", transitions=len(net.transitions))
        return net, im, fm
    except Exception:
        log.warning("process_discovery_failed", exc_info=True)
        return None


def compute_quality_metrics(
    traces: list[WorkflowTrace],
    net: Any,
    im: Any,
    fm: Any,
) -> ProcessMetrics:
    """Compute fitness and precision via PM4Py token-based replay."""
    df = traces_to_dataframe(traces)
    if df.empty:
        return ProcessMetrics()

    try:
        import pm4py

        df = pm4py.format_dataframe(
            df,
            case_id="case:concept:name",
            activity_key="concept:name",
            timestamp_key="time:timestamp",
        )
        fitness = pm4py.fitness_token_based_replay(df, net, im, fm)
        precision = pm4py.precision_token_based_replay(df, net, im, fm)
        return ProcessMetrics(
            fitness=fitness.get("average_trace_fitness", 0.0),
            precision=precision if isinstance(precision, float) else 0.0,
        )
    except Exception:
        log.warning("quality_metrics_failed", exc_info=True)
        return ProcessMetrics()


def build_execution_graph(
    traces: list[WorkflowTrace],
    task_cluster: str,
) -> tuple[nx.DiGraph, ExecutionGraph]:
    """Build a weighted DAG from traces using Directly-Follows Graph construction.

    Nodes: tool names + __START__ and __END__ sentinel nodes.
    Edges: transitions between consecutive tools with aggregated weights.
    """
    g = nx.DiGraph()
    g.add_node(START_NODE)
    g.add_node(END_NODE)

    edge_data: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: {"durations": [], "costs": [], "successes": []}
    )

    for trace in traces:
        seq = trace.tool_sequence
        if not seq:
            continue

        # Gather per-tool duration/cost from events
        tool_metrics: dict[str, dict[str, float]] = {}
        for event in trace.events:
            if event.tool_name is not None:
                tool_metrics[event.tool_name] = {
                    "duration_ms": event.duration_ms,
                    "cost_usd": event.cost_usd,
                }

        success_val = 1.0 if trace.success else 0.0

        # __START__ -> first tool
        first = seq[0]
        g.add_node(first)
        metrics = tool_metrics.get(first, {"duration_ms": 0.0, "cost_usd": 0.0})
        edge_data[(START_NODE, first)]["durations"].append(metrics["duration_ms"])
        edge_data[(START_NODE, first)]["costs"].append(metrics["cost_usd"])
        edge_data[(START_NODE, first)]["successes"].append(success_val)

        # Consecutive tool transitions
        for i in range(len(seq) - 1):
            src, tgt = seq[i], seq[i + 1]
            g.add_node(tgt)
            metrics = tool_metrics.get(tgt, {"duration_ms": 0.0, "cost_usd": 0.0})
            edge_data[(src, tgt)]["durations"].append(metrics["duration_ms"])
            edge_data[(src, tgt)]["costs"].append(metrics["cost_usd"])
            edge_data[(src, tgt)]["successes"].append(success_val)

        # Last tool -> __END__
        last = seq[-1]
        edge_data[(last, END_NODE)]["durations"].append(0.0)
        edge_data[(last, END_NODE)]["costs"].append(0.0)
        edge_data[(last, END_NODE)]["successes"].append(success_val)

    # Aggregate edge weights
    serializable_edges = []
    for (src, tgt), data in edge_data.items():
        freq = len(data["durations"])
        avg_dur = sum(data["durations"]) / freq if freq else 0.0
        avg_cost = sum(data["costs"]) / freq if freq else 0.0
        succ_rate = sum(data["successes"]) / freq if freq else 0.0

        g.add_edge(
            src, tgt,
            weight=avg_dur,
            frequency=freq,
            success_rate=succ_rate,
            avg_duration_ms=avg_dur,
            avg_cost_usd=avg_cost,
        )
        serializable_edges.append(GraphEdge(
            source=src,
            target=tgt,
            weight=avg_dur,
            frequency=freq,
            success_rate=succ_rate,
            avg_duration_ms=avg_dur,
            avg_cost_usd=avg_cost,
        ))

    exec_graph = ExecutionGraph(
        task_cluster=task_cluster,
        nodes=list(g.nodes),
        edges=serializable_edges,
        total_traces=len(traces),
    )

    log.info(
        "execution_graph_built",
        cluster=task_cluster,
        nodes=len(g.nodes),
        edges=len(g.edges),
        traces=len(traces),
    )
    return g, exec_graph

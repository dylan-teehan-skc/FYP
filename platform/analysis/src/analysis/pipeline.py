"""Top-level pipeline orchestrator + CLI entry point."""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=False)

from analysis.clustering import cluster_by_embedding, subcluster_by_trace
from analysis.config import Settings, get_settings
from analysis.database import Database
from analysis.graph import (
    build_execution_graph,
    compute_quality_metrics,
    discover_process_model,
)
from analysis.logger import get_logger, init_logging
from analysis.models import AnalysisResult
from analysis.naming import generate_cluster_name
from analysis.optimizer import find_pareto_paths, select_knee_point
from analysis.patterns import detect_patterns
from analysis.suggestions import generate_suggestions
from analysis.traces import reconstruct_trace

log = get_logger("analysis.pipeline")


async def run_analysis_for_cluster(
    db: Database,
    task_cluster: str,
    workflow_ids: list[str],
    settings: Settings,
    *,
    skip_upsert: bool = False,
) -> AnalysisResult:
    """Run the full analysis pipeline for a single cluster."""
    # 1. Reconstruct traces
    traces = []
    for wf_id in workflow_ids:
        trace = await reconstruct_trace(db, wf_id)
        traces.append(trace)

    if not traces:
        return AnalysisResult(task_cluster=task_cluster)

    # 2. Discover process model (PM4Py)
    model_result = discover_process_model(traces)
    net, im, fm = model_result if model_result else (None, None, None)

    # 3. Compute quality metrics
    process_metrics = None
    if net is not None:
        process_metrics = compute_quality_metrics(traces, net, im, fm)

    # 4. Build networkx execution graph
    nx_graph, exec_graph = build_execution_graph(traces, task_cluster)

    # 5. Detect patterns
    patterns = detect_patterns(traces, net, im, fm, settings=settings)

    # 6. Find Pareto-optimal paths
    pareto_paths = find_pareto_paths(
        nx_graph, traces, task_cluster,
        min_success_rate=settings.min_success_rate,
    )

    # 7. Select knee point as the primary optimal path
    optimal_path = None
    if pareto_paths:
        knee = select_knee_point(
            [(p.tool_sequence, {
                "avg_duration_ms": p.avg_duration_ms,
                "avg_cost_usd": p.avg_cost_usd,
                "success_rate": p.success_rate,
            }) for p in pareto_paths]
        )
        if knee:
            # Find the matching OptimalPath object
            for p in pareto_paths:
                if p.tool_sequence == knee[0]:
                    optimal_path = p
                    break

    # 8. Generate suggestions
    suggestions = generate_suggestions(patterns, optimal_path, traces)

    # 9. Upsert optimal path to DB (attach embedding from cluster for similarity search)
    #    skip_upsert=True for group-level clusters that mix different workflow types —
    #    only subclusters (separated by NED) should produce paths for the optimizer.
    if optimal_path and not skip_upsert:
        if not optimal_path.embedding and workflow_ids:
            optimal_path.embedding = await db.fetch_centroid_embedding(workflow_ids)
        mode_rates = await db.fetch_mode_success_rates(workflow_ids)
        await db.upsert_optimal_path({
            "path_id": optimal_path.path_id,
            "task_cluster": task_cluster,
            "tool_sequence": optimal_path.tool_sequence,
            "avg_duration_ms": optimal_path.avg_duration_ms,
            "avg_steps": optimal_path.avg_steps,
            "success_rate": optimal_path.success_rate,
            "execution_count": len(traces),  # cluster size, not exact-match count
            "embedding": optimal_path.embedding,
            "guided_success_rate": mode_rates["guided"],
            "exploration_success_rate": mode_rates["exploration"],
        })

    log.info(
        "cluster_analysis_complete",
        cluster=task_cluster,
        traces=len(traces),
        patterns=len(patterns),
        pareto_paths=len(pareto_paths),
        suggestions=len(suggestions),
    )

    return AnalysisResult(
        task_cluster=task_cluster,
        traces_analyzed=len(traces),
        execution_graph=exec_graph,
        process_metrics=process_metrics,
        patterns=patterns,
        pareto_paths=pareto_paths,
        optimal_path=optimal_path,
        suggestions=suggestions,
    )


async def run_analysis(
    db: Database,
    settings: Settings | None = None,
) -> list[AnalysisResult]:
    """Run the full analysis pipeline across all workflow clusters."""
    if settings is None:
        settings = get_settings()

    # Level 1: Semantic clustering
    clusters = await cluster_by_embedding(
        db,
        similarity_threshold=settings.similarity_threshold,
        min_executions=settings.min_executions,
    )

    if not clusters:
        log.info("no_clusters_found")
        return []

    # Clear stale optimal paths from previous runs — cluster names may change
    # between runs (LLM-generated), so per-cluster upserts alone can leave orphans.
    await db.clear_optimal_paths()

    results = []
    for idx, (cluster_label, cluster_result) in enumerate(clusters.items()):
        # Level 2: Trace sub-clustering
        traces = []
        for wf_id in cluster_result.workflow_ids:
            trace = await reconstruct_trace(db, wf_id)
            traces.append(trace)

        # Rate-limit: space out LLM calls to avoid 429s on free-tier APIs
        if idx > 0:
            await asyncio.sleep(10)

        # Generate LLM cluster name from task descriptions
        cluster_name = await generate_cluster_name(
            cluster_result.descriptions, settings.llm_model,
        )

        subclusters = subcluster_by_trace(
            traces, ned_threshold=settings.ned_threshold
        )

        for sub_label, sub_traces in subclusters.items():
            sub_wf_ids = [t.workflow_id for t in sub_traces]
            full_label = cluster_name
            if len(subclusters) > 1:
                full_label = f"{cluster_name} ({sub_label})"

            result = await run_analysis_for_cluster(
                db, full_label, sub_wf_ids, settings
            )
            results.append(result)

        # Group-level analysis for dashboard metrics (no optimal path upsert —
        # parent clusters mix different workflow types and produce wrong paths).
        all_wf_ids = [str(wf) for wf in cluster_result.workflow_ids]
        group_result = await run_analysis_for_cluster(
            db, cluster_name, all_wf_ids, settings, skip_upsert=True,
        )
        results.append(group_result)

    log.info("analysis_complete", clusters=len(results))
    return results


def run_cli() -> None:
    """CLI entry point: connect to DB, run analysis, print results."""
    settings = get_settings()
    init_logging(settings.log_level)

    async def _main() -> None:
        db = Database(
            dsn=settings.database_url,
            min_size=settings.database_pool_min,
            max_size=settings.database_pool_max,
        )
        await db.connect()
        try:
            results = await run_analysis(db, settings)
            for result in results:
                print(f"\n{'=' * 60}")
                print(f"Cluster: {result.task_cluster}")
                print(f"Traces analyzed: {result.traces_analyzed}")
                if result.process_metrics:
                    print(
                        f"Model quality: fitness={result.process_metrics.fitness:.2f}, "
                        f"precision={result.process_metrics.precision:.2f}"
                    )
                if result.optimal_path:
                    print(f"Optimal path: {' → '.join(result.optimal_path.tool_sequence)}")
                    print(
                        f"  Duration: {result.optimal_path.avg_duration_ms:.0f}ms, "
                        f"Success: {result.optimal_path.success_rate:.0%}"
                    )
                print(f"Patterns: {len(result.patterns)}")
                print(f"Suggestions: {len(result.suggestions)}")
                for s in result.suggestions:
                    print(f"  [{s.priority}] {s.message}")
        finally:
            await db.disconnect()

    asyncio.run(_main())


if __name__ == "__main__":
    run_cli()

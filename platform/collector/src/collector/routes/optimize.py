"""Optimization endpoint: POST /optimize/path."""

from __future__ import annotations

from fastapi import APIRouter, Request

from collector.logger import get_logger
from collector.models import OptimalPathOut, OptimizePathIn

log = get_logger("collector.routes.optimize")
router = APIRouter()


@router.post("/optimize/path")
async def optimize_path(body: OptimizePathIn, request: Request) -> OptimalPathOut:
    """Semantic search for the optimal execution path.

    1. Generate embedding for the task description
    2. pgvector similarity search against optimal_paths
    3. Return guided mode if match found, else exploration mode
    """
    db = request.app.state.db
    embedding_service = request.app.state.embedding_service
    threshold = request.app.state.settings.similarity_threshold

    embedding = await embedding_service.generate(body.task_description)
    if not embedding:
        log.info("optimize_exploration", reason="embedding_failed")
        return OptimalPathOut(mode="exploration")

    match = await db.find_similar_paths(
        embedding,
        min_executions=request.app.state.settings.min_executions,
    )
    if not match:
        log.info("optimize_exploration", reason="no_matching_paths")
        return OptimalPathOut(mode="exploration")

    similarity = match["similarity"]
    if similarity < threshold:
        log.info(
            "optimize_exploration",
            reason="below_threshold",
            similarity=round(similarity, 4),
        )
        return OptimalPathOut(mode="exploration")

    # Regression check: if guided mode is performing worse than exploration
    # for this cluster, fall back to exploration until the next analysis run.
    guided_rate = match["guided_success_rate"]
    exploration_rate = match["exploration_success_rate"]
    margin = request.app.state.settings.regression_margin
    if (
        guided_rate is not None
        and exploration_rate is not None
        and guided_rate < exploration_rate - margin
    ):
        log.info(
            "optimize_exploration",
            reason="regression_detected",
            guided_success_rate=round(guided_rate, 4),
            exploration_success_rate=round(exploration_rate, 4),
            margin=margin,
        )
        return OptimalPathOut(mode="exploration")

    log.info(
        "optimize_guided",
        similarity=round(similarity, 4),
        execution_count=match["execution_count"],
    )
    return OptimalPathOut(
        mode="guided",
        path=match["tool_sequence"],
        confidence=round(similarity, 4),
        avg_duration_ms=match["avg_duration_ms"],
        avg_steps=match["avg_steps"],
        success_rate=match["success_rate"],
        execution_count=match["execution_count"],
        failure_warnings=match["failure_warnings"] or None,
        alternative_paths=match["alternative_paths"] or None,
        decision_tree=match["decision_tree"] or None,
    )

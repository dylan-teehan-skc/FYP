"""Workflow endpoints: POST /workflows/complete and GET /workflows/{id}/trace."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request

from collector.logger import get_logger
from collector.models import EventOut, TraceOut, WorkflowCompleteIn

log = get_logger("collector.routes.workflows")
router = APIRouter()


@router.post("/workflows/complete")
async def complete_workflow(body: WorkflowCompleteIn, request: Request) -> dict:
    """Mark a workflow as complete and trigger embedding generation.

    Embedding generation runs as a background task so the SDK is not blocked.
    """
    db = request.app.state.db
    embedding_service = request.app.state.embedding_service

    asyncio.create_task(
        _generate_embedding(db, embedding_service, body.workflow_id, body.task_description)
    )
    log.info(
        "workflow_complete",
        workflow_id=body.workflow_id,
        status=body.status,
        total_steps=body.total_steps,
    )
    return {"status": "ok", "workflow_id": body.workflow_id}


async def _generate_embedding(
    db: object,
    embedding_service: object,
    workflow_id: str,
    task_description: str,
) -> None:
    """Background task: generate and store embedding for completed workflow."""
    embedding = await embedding_service.generate(task_description)  # type: ignore[attr-defined]
    if embedding:
        await db.upsert_embedding(  # type: ignore[attr-defined]
            workflow_id, task_description, embedding, embedding_service._model  # type: ignore[attr-defined]
        )
        log.info("embedding_stored", workflow_id=workflow_id)


@router.get("/workflows/{workflow_id}/trace")
async def get_trace(workflow_id: str, request: Request) -> TraceOut:
    """Return the full event trace for a workflow."""
    db = request.app.state.db
    rows = await db.get_workflow_trace(workflow_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No events found for workflow {workflow_id}")
    events = [EventOut(**dict(row)) for row in rows]
    return TraceOut(workflow_id=workflow_id, events=events, total_events=len(events))

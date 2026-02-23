"""Event ingestion endpoints: POST /events and POST /events/batch."""

from __future__ import annotations

from fastapi import APIRouter, Request

from collector.logger import get_logger
from collector.models import BatchEventsIn, EventIn

log = get_logger("collector.routes.events")
router = APIRouter()


@router.post("/events")
async def receive_event(event: EventIn, request: Request) -> dict:
    """Receive a single workflow event from the SDK."""
    db = request.app.state.db
    await db.insert_event(event.model_dump())
    log.info("event_received", event_id=event.event_id, workflow_id=event.workflow_id)
    return {"status": "ok"}


@router.post("/events/batch")
async def receive_batch(batch: BatchEventsIn, request: Request) -> dict:
    """Receive a batch of workflow events from the SDK."""
    db = request.app.state.db
    events_data = [e.model_dump() for e in batch.events]
    await db.insert_events_batch(events_data)
    log.info("batch_received", count=len(events_data))
    return {"status": "ok", "count": len(events_data)}

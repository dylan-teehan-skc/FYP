"""Analytics endpoint: GET /analytics/summary."""

from __future__ import annotations

from fastapi import APIRouter, Request

from collector.models import AnalyticsSummary

router = APIRouter()


@router.get("/analytics/summary")
async def get_summary(request: Request) -> AnalyticsSummary:
    """Return aggregate metrics across all workflows."""
    db = request.app.state.db
    data = await db.get_analytics_summary()
    return AnalyticsSummary(**data)

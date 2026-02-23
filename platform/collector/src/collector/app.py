"""FastAPI application for the workflow collector service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from collector.config import Settings, get_settings
from collector.database import Database
from collector.embeddings import EmbeddingService
from collector.logger import get_logger, init_logging
from collector.routes import analytics, events, optimize, workflows


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage database connection pool lifecycle."""
    settings = get_settings()
    db = Database(
        dsn=settings.database_url,
        min_size=settings.database_pool_min,
        max_size=settings.database_pool_max,
    )
    embedding_service = EmbeddingService(model=settings.embedding_model)
    await db.connect()
    app.state.settings = settings
    app.state.db = db
    app.state.embedding_service = embedding_service
    yield
    await db.disconnect()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory."""
    if settings is None:
        settings = get_settings()
    init_logging(settings.log_level)

    app = FastAPI(
        title="Workflow Collector",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(events.router)
    app.include_router(workflows.router)
    app.include_router(optimize.router)
    app.include_router(analytics.router)
    return app


log = get_logger("collector.app")


def run() -> None:
    """Entry point for the collector service."""
    settings = get_settings()
    init_logging(settings.log_level)
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)

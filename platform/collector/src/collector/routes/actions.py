"""Action endpoints for triggering analysis and demo runs from the dashboard."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from collector.logger import get_logger

log = get_logger("collector.routes.actions")
router = APIRouter(prefix="/actions")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
ANALYSIS_PYTHON = PROJECT_ROOT / "platform" / "analysis" / ".venv" / "bin" / "python3"
ANALYSIS_DIR = PROJECT_ROOT / "platform" / "analysis"
DEMO_PYTHON = PROJECT_ROOT / "demo" / "agent-runtime" / ".venv" / "bin" / "python3"
DEMO_DIR = PROJECT_ROOT / "demo" / "agent-runtime"
DEMO_SCRIPT = DEMO_DIR / "demo_runner.py"

_running_tasks: dict[str, asyncio.Task[Any]] = {}


class RunDemoIn(BaseModel):
    rounds: int = 1


class ActionOut(BaseModel):
    status: str
    message: str
    total_scenarios: int = 0


class StatusOut(BaseModel):
    demo_running: bool = False
    analysis_running: bool = False
    message: str = ""


async def _run_subprocess(label: str, *args: str, cwd: Path | None = None) -> str:
    """Run a subprocess and return stdout. Raises on failure."""
    log.info(f"{label}_start", args=args)
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip()[-500:]
        log.error(f"{label}_failed", returncode=proc.returncode, stderr=err)
        raise RuntimeError(f"{label} failed (exit {proc.returncode}): {err}")
    log.info(f"{label}_complete")
    return stdout.decode()


async def _run_analysis_task() -> None:
    try:
        await _run_subprocess(
            "analysis",
            str(ANALYSIS_PYTHON), "-m", "analysis.pipeline",
            cwd=ANALYSIS_DIR,
        )
    finally:
        _running_tasks.pop("analysis", None)


async def _run_demo_task(rounds: int) -> None:
    try:
        await _run_subprocess(
            "demo",
            str(DEMO_PYTHON), str(DEMO_SCRIPT),
            "--rounds", str(rounds),
            cwd=DEMO_DIR,
        )
    finally:
        _running_tasks.pop("demo", None)


@router.post("/run-analysis")
async def run_analysis(request: Request) -> ActionOut:
    """Trigger the analysis pipeline as a background task."""
    if "analysis" in _running_tasks and not _running_tasks["analysis"].done():
        return ActionOut(status="already_running", message="Analysis is already running")

    task = asyncio.create_task(_run_analysis_task())
    _running_tasks["analysis"] = task
    return ActionOut(status="started", message="Analysis pipeline started")


@router.post("/run-demo")
async def run_demo(body: RunDemoIn) -> ActionOut:
    """Trigger demo scenario runs as a background task."""
    if "demo" in _running_tasks and not _running_tasks["demo"].done():
        return ActionOut(
            status="already_running",
            message="Demo is already running",
        )

    rounds = max(1, min(body.rounds, 10))
    total = rounds * 5
    task = asyncio.create_task(_run_demo_task(rounds))
    _running_tasks["demo"] = task
    return ActionOut(
        status="started",
        message=f"Running {rounds} round(s) — {total} scenarios",
        total_scenarios=total,
    )


@router.get("/status")
async def get_status() -> StatusOut:
    """Check if any background tasks are running."""
    demo_running = "demo" in _running_tasks and not _running_tasks["demo"].done()
    analysis_running = "analysis" in _running_tasks and not _running_tasks["analysis"].done()

    parts = []
    if demo_running:
        parts.append("Demo running")
    if analysis_running:
        parts.append("Analysis running")

    return StatusOut(
        demo_running=demo_running,
        analysis_running=analysis_running,
        message=" | ".join(parts) if parts else "Idle",
    )

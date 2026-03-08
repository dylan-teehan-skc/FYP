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
LANGCHAIN_PYTHON = PROJECT_ROOT / "demo" / "langchain" / ".venv" / "bin" / "python3"
LANGCHAIN_DIR = PROJECT_ROOT / "demo" / "langchain"

_running_tasks: dict[str, asyncio.Task[Any]] = {}
_task_errors: dict[str, str] = {}


class RunDemoIn(BaseModel):
    rounds: int = 1


class ActionOut(BaseModel):
    status: str
    message: str
    total_scenarios: int = 0


class StatusOut(BaseModel):
    demo_running: bool = False
    analysis_running: bool = False
    langchain_single_running: bool = False
    langchain_multi_running: bool = False
    message: str = ""
    last_error: str = ""


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
        _task_errors.pop("analysis", None)
        await _run_subprocess(
            "analysis",
            str(ANALYSIS_PYTHON), "-m", "analysis.pipeline",
            cwd=ANALYSIS_DIR,
        )
    except Exception as e:
        _task_errors["analysis"] = str(e)
    finally:
        _running_tasks.pop("analysis", None)


async def _run_demo_task(rounds: int) -> None:
    try:
        _task_errors.pop("demo", None)
        for _ in range(rounds):
            await _run_subprocess(
                "demo",
                str(DEMO_PYTHON), str(DEMO_SCRIPT),
                "--rounds", "1",
                cwd=DEMO_DIR,
            )
            await _run_subprocess(
                "analysis",
                str(ANALYSIS_PYTHON), "-m", "analysis.pipeline",
                cwd=ANALYSIS_DIR,
            )
    except Exception as e:
        _task_errors["demo"] = str(e)
    finally:
        _running_tasks.pop("demo", None)


async def _run_langchain_single_task(rounds: int) -> None:
    try:
        _task_errors.pop("langchain_single", None)
        for _ in range(rounds):
            await _run_subprocess(
                "langchain_single",
                str(LANGCHAIN_PYTHON), "-m", "single_agent.main",
                "--rounds", "1",
                cwd=LANGCHAIN_DIR,
            )
            await _run_subprocess(
                "analysis",
                str(ANALYSIS_PYTHON), "-m", "analysis.pipeline",
                cwd=ANALYSIS_DIR,
            )
    except Exception as e:
        _task_errors["langchain_single"] = str(e)
    finally:
        _running_tasks.pop("langchain_single", None)


async def _run_langchain_multi_task(rounds: int) -> None:
    try:
        _task_errors.pop("langchain_multi", None)
        for _ in range(rounds):
            await _run_subprocess(
                "langchain_multi",
                str(LANGCHAIN_PYTHON), "-m", "multi_agent.main",
                "--rounds", "1",
                cwd=LANGCHAIN_DIR,
            )
            await _run_subprocess(
                "analysis",
                str(ANALYSIS_PYTHON), "-m", "analysis.pipeline",
                cwd=ANALYSIS_DIR,
            )
    except Exception as e:
        _task_errors["langchain_multi"] = str(e)
    finally:
        _running_tasks.pop("langchain_multi", None)


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
    total = rounds * 15
    task = asyncio.create_task(_run_demo_task(rounds))
    _running_tasks["demo"] = task
    return ActionOut(
        status="started",
        message=f"Running {rounds} round(s) — {total} scenarios",
        total_scenarios=total,
    )


@router.post("/run-langchain-single")
async def run_langchain_single(body: RunDemoIn) -> ActionOut:
    """Trigger LangChain single-agent demo as a background task."""
    if "langchain_single" in _running_tasks and not _running_tasks["langchain_single"].done():
        return ActionOut(
            status="already_running",
            message="LangChain single-agent demo is already running",
        )

    rounds = max(1, min(body.rounds, 10))
    total = rounds * 7
    task = asyncio.create_task(_run_langchain_single_task(rounds))
    _running_tasks["langchain_single"] = task
    return ActionOut(
        status="started",
        message=f"Running {rounds} round(s) — {total} scenarios",
        total_scenarios=total,
    )


@router.post("/run-langchain-multi")
async def run_langchain_multi(body: RunDemoIn) -> ActionOut:
    """Trigger LangChain multi-agent demo as a background task."""
    if "langchain_multi" in _running_tasks and not _running_tasks["langchain_multi"].done():
        return ActionOut(
            status="already_running",
            message="LangChain multi-agent demo is already running",
        )

    rounds = max(1, min(body.rounds, 10))
    total = rounds * 7
    task = asyncio.create_task(_run_langchain_multi_task(rounds))
    _running_tasks["langchain_multi"] = task
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
    lc_single = (
        "langchain_single" in _running_tasks
        and not _running_tasks["langchain_single"].done()
    )
    lc_multi = (
        "langchain_multi" in _running_tasks
        and not _running_tasks["langchain_multi"].done()
    )

    parts = []
    if demo_running:
        parts.append("Demo running")
    if lc_single:
        parts.append("LangChain single-agent running")
    if lc_multi:
        parts.append("LangChain multi-agent running")
    if analysis_running:
        parts.append("Analysis running")

    errors = list(_task_errors.values())
    last_error = errors[-1] if errors else ""

    return StatusOut(
        demo_running=demo_running,
        analysis_running=analysis_running,
        langchain_single_running=lc_single,
        langchain_multi_running=lc_multi,
        message=" | ".join(parts) if parts else "Idle",
        last_error=last_error,
    )

"""Shared fixtures for LangChain demo tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_trace() -> MagicMock:
    """Mock TraceContext with step() that returns mock StepContext."""
    trace = MagicMock()
    trace._active = True
    trace._step_counter = 0

    def make_step(*args: Any, **kwargs: Any) -> MagicMock:
        step = MagicMock()
        step._tool_name = kwargs.get("tool_name", args[0] if args else "unknown")
        step.__enter__ = MagicMock(return_value=step)
        step.__exit__ = MagicMock(return_value=False)
        return step

    trace.step = MagicMock(side_effect=make_step)
    return trace

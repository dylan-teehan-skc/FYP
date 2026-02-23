"""Shared fixtures for MCP tool server tests."""

import sys
from pathlib import Path

import pytest

# Ensure the server root is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state import StateManager  # noqa: E402


@pytest.fixture
def state():
    """Fresh StateManager for each test."""
    return StateManager()

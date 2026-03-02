"""Structured logging using structlog."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog

TIME_KEY = "@timestamp"


def _supports_colour() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if sys.platform == "win32" and os.getenv("TERM") != "xterm":
        return False
    return sys.stdout.isatty()


def init_logging(level: str = "INFO") -> None:
    root_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO", key=TIME_KEY),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if _supports_colour():
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True, timestamp_key=TIME_KEY)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False, timestamp_key=TIME_KEY)

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO", key=TIME_KEY),
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(root_level)
    handler.setFormatter(formatter)
    logging.basicConfig(level=root_level, handlers=[handler], force=True)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

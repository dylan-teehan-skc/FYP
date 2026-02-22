"""Structured logging using structlog."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from config import FileConfig, LoggingConfig

TIME_KEY = "@timestamp"


def _supports_colour() -> bool:
    """True if stdout seems to handle ANSI colour codes."""
    if os.getenv("NO_COLOR"):
        return False
    if sys.platform == "win32" and os.getenv("TERM") != "xterm":
        return False
    return sys.stdout.isatty()


def _pre_chain() -> list:
    """Processors to normalize stdlib LogRecord into structlog shape before rendering."""
    return [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO", key=TIME_KEY),
    ]


def _build_console_handler(level: int, renderer: str) -> logging.Handler:
    """Build a console handler with either pretty or JSON rendering."""
    processors: list[Any]
    if renderer == "json":
        processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.EventRenamer(to="message"),
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=_supports_colour(), timestamp_key=TIME_KEY),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_pre_chain(),
        processors=processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def _build_file_handler(file_cfg: FileConfig) -> logging.Handler:
    """Build a file handler with pretty text rendering and optional rotation."""
    path = Path(file_cfg.path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if file_cfg.rotation.enabled:
        handler: logging.Handler = RotatingFileHandler(
            path,
            maxBytes=file_cfg.rotation.max_bytes,
            backupCount=file_cfg.rotation.backup_count,
        )
    else:
        handler = logging.FileHandler(path)

    handler.setLevel(getattr(logging, file_cfg.level.upper(), logging.DEBUG))
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_pre_chain(),
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=False, timestamp_key=TIME_KEY),
        ],
    )
    handler.setFormatter(formatter)
    return handler


def init_logging(config: LoggingConfig) -> None:
    """Initialize structured logging with console and file handlers."""
    root_level = getattr(logging, config.level.upper(), logging.INFO)

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

    handlers: list[logging.Handler] = []

    # Console handler
    if config.console.enabled:
        renderer = config.console.renderer.strip().lower()
        handlers.append(_build_console_handler(root_level, renderer))

    # File handler
    if config.file.enabled:
        handlers.append(_build_file_handler(config.file))

    logging.basicConfig(level=logging.DEBUG, handlers=handlers, force=True)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to all subsequent log messages."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()

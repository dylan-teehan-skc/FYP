"""Tests for structured logging setup."""

from __future__ import annotations

from unittest.mock import patch

from analysis.logger import _supports_colour, get_logger, init_logging


class TestSupportsColour:
    @patch.dict("os.environ", {"NO_COLOR": "1"})
    def test_no_color_env(self) -> None:
        assert _supports_colour() is False

    @patch("sys.platform", "win32")
    @patch.dict("os.environ", {}, clear=True)
    def test_windows_without_xterm(self) -> None:
        assert _supports_colour() is False

    @patch("sys.platform", "win32")
    @patch.dict("os.environ", {"TERM": "xterm"}, clear=True)
    @patch("sys.stdout")
    def test_windows_with_xterm_checks_tty(self, mock_stdout) -> None:
        mock_stdout.isatty.return_value = True
        assert _supports_colour() is True

    @patch("sys.platform", "darwin")
    @patch.dict("os.environ", {}, clear=True)
    @patch("sys.stdout")
    def test_non_tty(self, mock_stdout) -> None:
        mock_stdout.isatty.return_value = False
        assert _supports_colour() is False


class TestInitLogging:
    def test_configures_structlog(self) -> None:
        init_logging("DEBUG")
        logger = get_logger("test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")

    def test_default_level(self) -> None:
        init_logging()
        logger = get_logger("test.default")
        assert hasattr(logger, "info")


class TestGetLogger:
    def test_returns_logger(self) -> None:
        logger = get_logger("analysis.test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

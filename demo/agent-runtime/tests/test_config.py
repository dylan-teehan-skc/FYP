"""Tests for configuration validation."""

import pytest
from pydantic import ValidationError

from utils.config import AgentConfig, AppConfig, LLMConfig, LoggingConfig, MCPConfig


class TestLLMConfig:
    """Tests for LLMConfig validation."""

    def test_valid_model(self) -> None:
        config = LLMConfig(model="gpt-4")
        assert config.model == "gpt-4"

    def test_litellm_model_format(self) -> None:
        config = LLMConfig(model="gemini/gemini-2.5-flash-lite")
        assert config.model == "gemini/gemini-2.5-flash-lite"


class TestMCPConfig:
    """Tests for MCPConfig validation."""

    def test_valid_http_url(self) -> None:
        config = MCPConfig(server_url="http://localhost:8000")
        assert config.server_url == "http://localhost:8000"

    def test_valid_https_url(self) -> None:
        config = MCPConfig(server_url="https://api.example.com")
        assert config.server_url == "https://api.example.com"

    def test_invalid_url_scheme(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            MCPConfig(server_url="ftp://localhost:8000")
        assert "server_url must start with http://" in str(exc_info.value)

    def test_default_timeout(self) -> None:
        config = MCPConfig(server_url="http://localhost:8000")
        assert config.timeout_seconds == 30

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValidationError):
            MCPConfig(server_url="http://localhost:8000", timeout_seconds=0)

    def test_custom_retries(self) -> None:
        config = MCPConfig(server_url="http://localhost:8000", max_retries=5)
        assert config.max_retries == 5


class TestLoggingConfig:
    """Tests for LoggingConfig validation."""

    def test_defaults(self) -> None:
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.console.enabled is True
        assert config.file.enabled is False

    def test_valid_levels(self) -> None:
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_console_config(self) -> None:
        config = LoggingConfig(console={"enabled": True, "renderer": "json"})
        assert config.console.renderer == "json"

    def test_file_config(self) -> None:
        config = LoggingConfig(file={"enabled": True, "path": "custom.log"})
        assert config.file.enabled is True
        assert config.file.path == "custom.log"


class TestAgentConfig:
    """Tests for AgentConfig validation."""

    def test_defaults(self) -> None:
        config = AgentConfig()
        assert config.loop_detection_threshold == 4
        assert config.loop_detection_window == 6

    def test_custom_values(self) -> None:
        config = AgentConfig(loop_detection_threshold=5, loop_detection_window=10)
        assert config.loop_detection_threshold == 5
        assert config.loop_detection_window == 10

    def test_invalid_threshold(self) -> None:
        with pytest.raises(ValidationError):
            AgentConfig(loop_detection_threshold=0)


class TestAppConfig:
    """Tests for AppConfig validation."""

    def test_minimal_config(self) -> None:
        config = AppConfig(
            llm=LLMConfig(model="gpt-4"),
            mcp=MCPConfig(server_url="http://localhost:8000"),
        )
        assert config.llm.model == "gpt-4"
        assert config.mcp.server_url == "http://localhost:8000"
        assert config.logging.level == "INFO"
        assert config.agent.loop_detection_threshold == 4

    def test_full_config(self, sample_config: AppConfig) -> None:
        assert sample_config.llm.model == "gpt-4"
        assert sample_config.logging.level == "DEBUG"
        assert sample_config.mcp.server_url == "http://localhost:8000"

    def test_from_json(self, tmp_path) -> None:
        config_json = """{
            "llm": {"model": "gpt-4"},
            "mcp": {"server_url": "http://localhost:8000"}
        }"""
        config_file = tmp_path / "config.json"
        config_file.write_text(config_json)

        config = AppConfig.model_validate_json(config_file.read_text())
        assert config.llm.model == "gpt-4"

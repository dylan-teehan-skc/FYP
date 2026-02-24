"""Pydantic configuration models for agent-runtime."""

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    model: str = Field(description="LiteLLM model identifier (e.g., gemini/gemini-2.5-flash-lite)")


class ConsoleConfig(BaseModel):
    """Console logging configuration."""

    enabled: bool = True
    renderer: str = "pretty"


class RotationConfig(BaseModel):
    """Log file rotation configuration."""

    enabled: bool = True
    max_bytes: int = Field(default=10_485_760, gt=0)
    backup_count: int = Field(default=5, ge=0)


class FileConfig(BaseModel):
    """File logging configuration."""

    enabled: bool = False
    level: str = "DEBUG"
    path: str = "logs/agent_runtime.log"
    rotation: RotationConfig = Field(default_factory=RotationConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    console: ConsoleConfig = Field(default_factory=ConsoleConfig)
    file: FileConfig = Field(default_factory=FileConfig)


class AgentConfig(BaseModel):
    """Agent behavior configuration."""

    loop_detection_window: int = Field(default=6, ge=1)
    loop_detection_threshold: int = Field(default=4, ge=1)


class MCPConfig(BaseModel):
    """MCP server connection configuration."""

    server_url: str
    timeout_seconds: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_delay_seconds: int = Field(default=2, ge=0)

    @field_validator("server_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate server URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("server_url must start with http:// or https://")
        return v


class ModeSelectorConfig(BaseModel):
    """Mode selector configuration for guided vs exploration mode."""

    similarity_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    min_executions: int = Field(default=10, ge=1)
    min_success_rate: float = Field(default=0.85, ge=0.0, le=1.0)


class AppConfig(BaseModel):
    """Root application configuration."""

    llm: LLMConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    mcp: MCPConfig
    mode_selector: ModeSelectorConfig = Field(default_factory=ModeSelectorConfig)

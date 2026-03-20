"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Collector service settings, loaded from environment or .env file."""

    database_url: str = "postgresql://collector:collector_dev@localhost:5432/workflow_optimizer"
    database_pool_min: int = 2
    database_pool_max: int = 10
    embedding_model: str = "gemini/gemini-embedding-001"
    log_level: str = "INFO"
    similarity_threshold: float = 0.85
    min_executions: int = 30
    regression_margin: float = 0.10
    host: str = "0.0.0.0"
    port: int = 9000

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    """Create settings instance (reads from environment)."""
    return Settings()

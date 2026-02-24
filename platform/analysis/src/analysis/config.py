"""Analysis engine configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Analysis engine settings, loaded from environment or .env file."""

    database_url: str = "postgresql://collector:collector_dev@localhost:5432/workflow_optimizer"
    database_pool_min: int = 2
    database_pool_max: int = 10
    embedding_model: str = "gemini/gemini-embedding-001"
    log_level: str = "INFO"

    # Analysis tuning
    similarity_threshold: float = 0.85
    min_success_rate: float = 0.85
    min_executions: int = 3
    bottleneck_threshold_pct: float = 0.40
    redundancy_min_calls: int = 2
    ned_threshold: float = 0.55

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    """Create settings instance (reads from environment)."""
    return Settings()

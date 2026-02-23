"""Tests for analysis engine configuration."""

from __future__ import annotations

from analysis.config import Settings, get_settings


class TestSettings:
    def test_default_values(self) -> None:
        s = Settings()
        assert s.database_pool_min == 2
        assert s.database_pool_max == 10
        assert s.embedding_model == "text-embedding-3-small"
        assert s.log_level == "INFO"

    def test_analysis_defaults(self) -> None:
        s = Settings()
        assert s.similarity_threshold == 0.60
        assert s.min_success_rate == 0.85
        assert s.min_executions == 3
        assert s.bottleneck_threshold_pct == 0.40
        assert s.redundancy_min_calls == 2
        assert s.edit_distance_threshold == 2

    def test_custom_values(self) -> None:
        s = Settings(
            database_url="postgresql://custom:custom@db/test",
            min_success_rate=0.70,
            min_executions=5,
        )
        assert s.database_url == "postgresql://custom:custom@db/test"
        assert s.min_success_rate == 0.70
        assert s.min_executions == 5

    def test_get_settings_factory(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

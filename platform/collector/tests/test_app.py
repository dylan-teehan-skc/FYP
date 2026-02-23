"""Tests for FastAPI app factory."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from collector.app import create_app, lifespan
from collector.config import Settings


class TestCreateApp:
    def test_factory_creates_app(self) -> None:
        settings = Settings(database_url="postgresql://test:test@localhost/test")
        app = create_app(settings)
        assert app.title == "Workflow Collector"
        assert app.version == "0.1.0"

    def test_routes_registered(self) -> None:
        settings = Settings(database_url="postgresql://test:test@localhost/test")
        app = create_app(settings)
        paths = [route.path for route in app.routes]
        assert "/events" in paths
        assert "/events/batch" in paths
        assert "/workflows/complete" in paths
        assert "/optimize/path" in paths
        assert "/analytics/summary" in paths

    def test_default_settings(self) -> None:
        settings = Settings()
        assert settings.port == 9000
        assert settings.host == "0.0.0.0"
        assert settings.database_pool_min == 2
        assert settings.database_pool_max == 10

    def test_factory_with_no_settings(self) -> None:
        app = create_app()
        assert app.title == "Workflow Collector"


class TestLifespan:
    @patch("collector.app.EmbeddingService")
    @patch("collector.app.Database")
    @patch("collector.app.get_settings")
    async def test_lifespan_connects_and_disconnects(
        self,
        mock_get_settings: AsyncMock,
        mock_db_cls: AsyncMock,
        mock_embed_cls: AsyncMock,
    ) -> None:
        mock_settings = Settings(database_url="postgresql://test:test@localhost/test")
        mock_get_settings.return_value = mock_settings

        mock_db = AsyncMock()
        mock_db_cls.return_value = mock_db
        mock_embed = AsyncMock()
        mock_embed_cls.return_value = mock_embed

        app = create_app(mock_settings)
        async with lifespan(app):
            assert app.state.db is mock_db
            assert app.state.embedding_service is mock_embed

        mock_db.connect.assert_called_once()
        mock_db.disconnect.assert_called_once()

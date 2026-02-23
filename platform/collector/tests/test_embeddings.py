"""Tests for embedding generation service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from collector.embeddings import EmbeddingService


class TestEmbeddingService:
    async def test_successful_generation(self) -> None:
        service = EmbeddingService(model="test-model")
        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.5] * 1536}]

        with patch.dict("sys.modules", {"litellm": MagicMock()}) as _:
            import litellm

            litellm.aembedding = AsyncMock(return_value=mock_response)
            result = await service.generate("Handle refund")

        assert result is not None
        assert len(result) == 1536
        assert result[0] == 0.5

    async def test_returns_none_on_error(self) -> None:
        service = EmbeddingService(model="test-model")

        with patch.dict("sys.modules", {"litellm": MagicMock()}) as _:
            import litellm

            litellm.aembedding = AsyncMock(side_effect=Exception("API error"))
            result = await service.generate("Handle refund")

        assert result is None

    async def test_returns_none_on_import_error(self) -> None:
        service = EmbeddingService(model="test-model")

        with patch.dict("sys.modules", {"litellm": None}):
            result = await service.generate("Handle refund")

        assert result is None

    async def test_model_name_stored(self) -> None:
        service = EmbeddingService(model="custom-model")
        assert service._model == "custom-model"

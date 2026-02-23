"""Embedding generation via LiteLLM with graceful degradation."""

from __future__ import annotations

from collector.logger import get_logger

log = get_logger("collector.embeddings")


class EmbeddingService:
    """Generates vector embeddings for task descriptions."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self._model = model

    async def generate(self, text: str) -> list[float] | None:
        """Generate a 768-dim embedding vector. Returns None on failure."""
        try:
            import litellm

            response = await litellm.aembedding(
                model=self._model,
                input=[text],
                dimensions=768,
            )
            embedding: list[float] = response.data[0]["embedding"]
            log.info("embedding_generated", model=self._model, dimensions=len(embedding))
            return embedding
        except Exception:
            log.warning("embedding_generation_failed", model=self._model, exc_info=True)
            return None

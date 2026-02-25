"""Tests for LLM-based cluster naming."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from analysis.naming import generate_cluster_name


class TestGenerateClusterName:
    @patch("analysis.naming.litellm.acompletion", new_callable=AsyncMock)
    async def test_returns_name(self, mock_completion: AsyncMock) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Refund Processing"
        mock_completion.return_value = mock_response

        result = await generate_cluster_name(
            ["process refund for order", "handle refund request"],
            model="test-model",
        )
        assert result == "Refund Processing"
        mock_completion.assert_called_once()

    @patch("analysis.naming.litellm.acompletion", new_callable=AsyncMock)
    async def test_strips_quotes_and_newlines(self, mock_completion: AsyncMock) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '"Refund Processing"\nExtra line'
        mock_completion.return_value = mock_response

        result = await generate_cluster_name(["refund"], model="test-model")
        assert result == "Refund Processing"

    @patch("analysis.naming.litellm.acompletion", new_callable=AsyncMock)
    async def test_truncates_long_name(self, mock_completion: AsyncMock) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "A" * 100
        mock_completion.return_value = mock_response

        result = await generate_cluster_name(["desc"], model="test-model")
        assert len(result) <= 50

    async def test_empty_descriptions(self) -> None:
        result = await generate_cluster_name([], model="test-model")
        assert result == "Unknown Cluster"

    @patch("analysis.naming.asyncio.sleep", new_callable=AsyncMock)
    @patch("analysis.naming.litellm.acompletion", new_callable=AsyncMock)
    async def test_retries_on_error_then_fallback(
        self, mock_completion: AsyncMock, mock_sleep: AsyncMock
    ) -> None:
        mock_completion.side_effect = RuntimeError("API error")

        result = await generate_cluster_name(
            ["short desc", "a longer description here"],
            model="test-model",
        )
        assert result == "short desc"
        assert mock_completion.call_count == 4  # _MAX_RETRIES

    @patch("analysis.naming.litellm.acompletion", new_callable=AsyncMock)
    async def test_deduplicates_descriptions(self, mock_completion: AsyncMock) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Refund"
        mock_completion.return_value = mock_response

        await generate_cluster_name(
            ["same desc", "same desc", "same desc"],
            model="test-model",
        )
        call_args = mock_completion.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert prompt.count("same desc") == 1

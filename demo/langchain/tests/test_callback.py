"""Tests for WorkflowOptimizerCallbackHandler."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from langchain_core.outputs import LLMResult

from callback import WorkflowOptimizerCallbackHandler


@pytest.fixture
def handler(mock_trace: MagicMock) -> WorkflowOptimizerCallbackHandler:
    return WorkflowOptimizerCallbackHandler(trace=mock_trace, llm_model="gemini-test")


def _serialized(name: str = "check_ticket_status") -> dict[str, Any]:
    return {"name": name, "description": "test tool"}


def _llm_result(prompt_tokens: int = 10, completion_tokens: int = 20) -> LLMResult:
    return LLMResult(
        generations=[[]],
        llm_output={"token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }},
    )


class TestOnToolStart:
    def test_creates_step(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(_serialized(), '{"ticket_id": "T-1001"}', run_id=run_id)

        mock_trace.step.assert_called_once_with(
            "check_ticket_status",
            params={"ticket_id": "T-1001"},
            llm_model="gemini-test",
            llm_prompt_tokens=0,
            llm_completion_tokens=0,
        )
        step = handler._active_steps[run_id]
        step.__enter__.assert_called_once()

    def test_uses_inputs_dict_over_input_str(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(
            _serialized(),
            "raw_string",
            run_id=run_id,
            inputs={"ticket_id": "T-1001"},
        )

        call_kwargs = mock_trace.step.call_args[1]
        assert call_kwargs["params"] == {"ticket_id": "T-1001"}

    def test_non_json_input_wrapped(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(_serialized(), "plain text", run_id=run_id)

        call_kwargs = mock_trace.step.call_args[1]
        assert call_kwargs["params"] == {"input": "plain text"}


class TestOnToolEnd:
    def test_success_response(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(_serialized(), "{}", run_id=run_id)
        step = handler._active_steps[run_id]

        handler.on_tool_end(json.dumps({"status": "ok"}), run_id=run_id)

        step.set_response.assert_called_once_with({"status": "ok"})
        step.__exit__.assert_called_once_with(None, None, None)

    def test_error_response_detected(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(_serialized(), "{}", run_id=run_id)
        step = handler._active_steps[run_id]

        handler.on_tool_end(json.dumps({"error": "Ticket T-9999 not found"}), run_id=run_id)

        step.set_error.assert_called_once_with("Ticket T-9999 not found")
        step.set_response.assert_not_called()
        step.__exit__.assert_called_once_with(None, None, None)

    def test_unknown_run_id_ignored(
        self, handler: WorkflowOptimizerCallbackHandler
    ) -> None:
        handler.on_tool_end("output", run_id=uuid4())

    def test_non_json_output(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(_serialized(), "{}", run_id=run_id)
        step = handler._active_steps[run_id]

        handler.on_tool_end("plain text output", run_id=run_id)

        step.set_response.assert_called_once_with({"output": "plain text output"})


class TestOnToolError:
    def test_records_error(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        run_id = uuid4()
        handler.on_tool_start(_serialized(), "{}", run_id=run_id)
        step = handler._active_steps[run_id]

        error = RuntimeError("connection timeout")
        handler.on_tool_error(error, run_id=run_id)

        step.set_error.assert_called_once_with("connection timeout")
        step.__exit__.assert_called_once_with(RuntimeError, error, error.__traceback__)

    def test_unknown_run_id_ignored(
        self, handler: WorkflowOptimizerCallbackHandler
    ) -> None:
        handler.on_tool_error(RuntimeError("err"), run_id=uuid4())


class TestLLMTokenTracking:
    def test_tokens_captured(
        self, handler: WorkflowOptimizerCallbackHandler
    ) -> None:
        handler.on_llm_end(_llm_result(15, 25), run_id=uuid4())

        assert handler.total_prompt_tokens == 15
        assert handler.total_completion_tokens == 25

    def test_tokens_attributed_to_next_tool(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        handler.on_llm_end(_llm_result(10, 20), run_id=uuid4())
        handler.on_tool_start(_serialized(), "{}", run_id=uuid4())

        call_kwargs = mock_trace.step.call_args[1]
        assert call_kwargs["llm_prompt_tokens"] == 10
        assert call_kwargs["llm_completion_tokens"] == 20

    def test_tokens_reset_after_attribution(
        self, handler: WorkflowOptimizerCallbackHandler, mock_trace: MagicMock
    ) -> None:
        handler.on_llm_end(_llm_result(10, 20), run_id=uuid4())
        handler.on_tool_start(_serialized("tool_a"), "{}", run_id=uuid4())

        handler.on_tool_start(_serialized("tool_b"), "{}", run_id=uuid4())
        call_kwargs = mock_trace.step.call_args[1]
        assert call_kwargs["llm_prompt_tokens"] == 0
        assert call_kwargs["llm_completion_tokens"] == 0

    def test_total_tokens_accumulated(
        self, handler: WorkflowOptimizerCallbackHandler
    ) -> None:
        handler.on_llm_end(_llm_result(10, 20), run_id=uuid4())
        handler.on_llm_end(_llm_result(30, 40), run_id=uuid4())

        assert handler.total_prompt_tokens == 40
        assert handler.total_completion_tokens == 60

    def test_no_token_usage(
        self, handler: WorkflowOptimizerCallbackHandler
    ) -> None:
        result = LLMResult(generations=[[]], llm_output=None)
        handler.on_llm_end(result, run_id=uuid4())

        assert handler.total_prompt_tokens == 0
        assert handler.total_completion_tokens == 0

    def test_usage_key_fallback(
        self, handler: WorkflowOptimizerCallbackHandler
    ) -> None:
        result = LLMResult(
            generations=[[]],
            llm_output={"usage": {"prompt_tokens": 5, "completion_tokens": 7}},
        )
        handler.on_llm_end(result, run_id=uuid4())

        assert handler.total_prompt_tokens == 5
        assert handler.total_completion_tokens == 7

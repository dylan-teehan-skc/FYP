"""LangChain callback handler that bridges to the workflow-optimizer SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from logger import get_logger

log = get_logger("langchain_demo.callback")


@dataclass
class _LLMTokens:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class WorkflowOptimizerCallbackHandler(BaseCallbackHandler):
    """Captures LangChain agent tool calls as SDK trace steps."""

    def __init__(self, trace: Any, llm_model: str = "") -> None:
        super().__init__()
        self._trace = trace
        self._llm_model = llm_model
        self._active_steps: dict[UUID, Any] = {}
        self._last_llm: _LLMTokens = _LLMTokens()
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0

    @property
    def total_prompt_tokens(self) -> int:
        return self._total_prompt_tokens

    @property
    def total_completion_tokens(self) -> int:
        return self._total_completion_tokens

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        usage = {}
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            if not usage:
                usage = response.llm_output.get("usage", {})

        prompt = usage.get("prompt_tokens", 0) or 0
        completion = usage.get("completion_tokens", 0) or 0

        self._last_llm = _LLMTokens(
            prompt_tokens=prompt,
            completion_tokens=completion,
            model=self._llm_model,
        )
        self._total_prompt_tokens += prompt
        self._total_completion_tokens += completion

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")

        params: dict[str, Any] = {}
        if inputs:
            params = dict(inputs)
        elif input_str:
            try:
                parsed = json.loads(input_str)
                if isinstance(parsed, dict):
                    params = parsed
            except (json.JSONDecodeError, TypeError):
                params = {"input": input_str}

        step = self._trace.step(
            tool_name,
            params=params,
            llm_model=self._last_llm.model or self._llm_model,
            llm_prompt_tokens=self._last_llm.prompt_tokens,
            llm_completion_tokens=self._last_llm.completion_tokens,
        )
        step.__enter__()
        self._active_steps[run_id] = step

        self._last_llm = _LLMTokens()

        log.info("tool_start", tool=tool_name, run_id=str(run_id)[:8])

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        step = self._active_steps.pop(run_id, None)
        if step is None:
            return

        output_str = str(output) if output is not None else ""
        tool_name = step._tool_name

        try:
            parsed = json.loads(output_str)
        except (json.JSONDecodeError, TypeError):
            parsed = {"output": output_str}

        if isinstance(parsed, dict) and "error" in parsed:
            step.set_error(parsed["error"])
            log.error("tool_error_response", tool=tool_name, error=parsed["error"])
        else:
            step.set_response(parsed if isinstance(parsed, dict) else {"output": output_str})
            log.info("tool_end", tool=tool_name, run_id=str(run_id)[:8])

        step.__exit__(None, None, None)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        step = self._active_steps.pop(run_id, None)
        if step is None:
            return

        step.set_error(str(error))
        log.error("tool_exception", tool=step._tool_name, error=str(error)[:200])
        step.__exit__(type(error), error, error.__traceback__)

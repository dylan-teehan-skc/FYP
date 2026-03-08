"""LLM integration for agent reasoning."""

import json
from typing import Any

import litellm

from prompts.templates import AgentPrompts
from utils.exceptions import ReasoningError
from utils.logger import get_logger


class ReasoningEngine:
    """Async LLM-based reasoning using LiteLLM."""

    _MAX_JSON_RETRIES: int = 3

    def __init__(self, model: str) -> None:
        self.model = model
        self.log = get_logger("ReasoningEngine")

    async def reason(
        self,
        task: str,
        context: str,
        tools_doc: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate next action based on task and available tools."""
        prompt = AgentPrompts.build_reasoning_prompt(task, context, tools_doc, history)

        self.log.debug(f"prompt_to_llm\n{'─'*60}\n{prompt}\n{'─'*60}")

        for attempt in range(1, self._MAX_JSON_RETRIES + 1):
            try:
                response = await litellm.acompletion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                text: str = response.choices[0].message.content.strip()

                self.log.debug(f"raw_llm_response\n{'─'*60}\n{text}\n{'─'*60}")

                result = self._parse_response(text)

                if result["action"] is not None or attempt == self._MAX_JSON_RETRIES:
                    result["llm_prompt"] = prompt
                    result["prompt_tokens"] = response.usage.prompt_tokens
                    result["completion_tokens"] = response.usage.completion_tokens
                    try:
                        result["cost_usd"] = litellm.completion_cost(
                            completion_response=response
                        )
                    except Exception:
                        result["cost_usd"] = 0.0
                    return result

                self.log.warning(
                    "json_retry",
                    attempt=attempt,
                    max_attempts=self._MAX_JSON_RETRIES,
                    text=text[:100],
                )
            except litellm.exceptions.APIError as e:
                self.log.error("llm_api_error", error=str(e))
                raise ReasoningError(f"LLM API error: {e}") from e
            except Exception as e:
                self.log.error("reasoning_failed", error=str(e))
                return {
                    "reasoning": f"Error: {e}",
                    "action": None,
                    "parameters": {},
                    "llm_prompt": prompt,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                }

        return {
            "reasoning": "",
            "action": None,
            "parameters": {},
            "llm_prompt": prompt,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
        }

    def _parse_response(self, text: str) -> dict[str, Any]:
        """Parse LLM response into structured format."""
        text = self._clean_json(text)

        try:
            data = json.loads(text)
            return {
                "reasoning": data.get("reasoning", ""),
                "action": data.get("action"),
                "parameters": data.get("parameters", {}),
            }
        except json.JSONDecodeError:
            self.log.warning("json_parse_failed", text=text[:100])
            return {"reasoning": text, "action": None, "parameters": {}}

    def _clean_json(self, text: str) -> str:
        """Extract JSON object from LLM response, handling code blocks and embedded braces."""
        text = text.strip()

        # Try to extract from markdown code block first
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
            return text.strip()
        if "```" in text:
            text = text.split("```")[1].split("```")[0]
            return text.strip()

        # Find JSON object with string-aware brace matching
        start = text.find("{")
        if start == -1:
            return text

        depth = 0
        in_string = False
        escape_next = False
        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return text

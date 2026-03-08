"""Prompt template loader."""

from pathlib import Path
from typing import Any


class AgentPrompts:
    """Loads and formats prompt templates from .txt files."""

    _prompts_dir = Path(__file__).parent

    @classmethod
    def _load(cls, name: str) -> str:
        """Load a prompt template from file."""
        path = cls._prompts_dir / f"{name}.txt"
        return path.read_text()

    @staticmethod
    def format_history(history: list[dict[str, Any]] | None) -> str:
        """Format action history for prompt."""
        if not history:
            return "No previous actions."

        lines = []
        for i, h in enumerate(history[-15:], 1):
            action = h.get("action", "unknown")
            status = "SUCCESS" if h.get("success", False) else "FAILED"
            params = h.get("parameters", {})
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            result = str(h.get("result", ""))
            lines.append(f"{i}. [{status}] {action}({params_str}): {result}")
        return "\n".join(lines)

    @classmethod
    def build_reasoning_prompt(
        cls,
        task: str,
        context: str,
        tools_doc: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build complete reasoning prompt."""
        template = cls._load("reasoning")
        return template.format(
            task=task,
            context=context,
            history=cls.format_history(history),
            tools=tools_doc,
        )

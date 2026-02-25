"""LLM-based cluster naming using litellm."""

from __future__ import annotations

import asyncio
from pathlib import Path

import litellm

from analysis.logger import get_logger

log = get_logger("analysis.naming")

PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "cluster_name.txt"

_MAX_RETRIES = 4
_BASE_DELAY = 5.0


async def generate_cluster_name(
    descriptions: list[str],
    model: str,
) -> str:
    """Generate a short LLM category name from a sample of task descriptions."""
    unique = list(dict.fromkeys(descriptions))
    sample = [d[:100] for d in unique[:5]]

    if not sample:
        return "Unknown Cluster"

    template = PROMPT_PATH.read_text()
    prompt = template.format(descriptions="\n".join(f"- {d}" for d in sample))

    for attempt in range(_MAX_RETRIES):
        try:
            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=30,
                temperature=0.0,
            )

            name = response.choices[0].message.content.strip()
            name = name.split("\n")[0].strip().strip('"').strip("'")
            name = name[:50]

            if name:
                log.info("cluster_named", name=name, sample_size=len(sample))
                return name
        except Exception as exc:
            delay = _BASE_DELAY * (2 ** attempt)
            log.warning(
                "cluster_naming_retry",
                attempt=attempt + 1,
                delay=delay,
                error=str(exc)[:200],
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(delay)

    log.warning("cluster_naming_failed", fallback="shortest_description")
    return min(descriptions, key=len)[:60] if descriptions else "Unknown Cluster"

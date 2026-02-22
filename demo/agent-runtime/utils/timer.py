"""ASCII block timer for workflow profiling."""

import time
from dataclasses import dataclass


@dataclass
class TimingBlock:
    """A single timed operation."""

    name: str
    duration_ms: float


class BlockTimer:
    """Records operations and displays them as ASCII blocks."""

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        self.blocks: list[TimingBlock] = []
        self._current_name: str | None = None
        self._start_time: float | None = None

    def start(self, name: str) -> None:
        """Start timing an operation."""
        self._current_name = name
        self._start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop timing and record the block. Returns duration in ms."""
        if self._start_time is None or self._current_name is None:
            return 0.0

        duration_ms = (time.perf_counter() - self._start_time) * 1000
        self.blocks.append(TimingBlock(name=self._current_name, duration_ms=duration_ms))
        self._current_name = None
        self._start_time = None
        return duration_ms

    def record(self, name: str, duration_ms: float) -> None:
        """Manually record a timing block."""
        self.blocks.append(TimingBlock(name=name, duration_ms=duration_ms))

    def total_ms(self) -> float:
        """Get total duration of all blocks."""
        return sum(b.duration_ms for b in self.blocks)

    def render(self, width: int = 60) -> str:
        """Render timing blocks as ASCII art."""
        if not self.blocks:
            return ""

        max_duration = max(b.duration_ms for b in self.blocks)
        max_name_len = max(len(b.name) for b in self.blocks)
        bar_width = width - max_name_len - 15

        lines = []
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append(f"| WORKFLOW TIMING: {self.workflow_id:<{width - 22}} |")
        lines.append("+" + "-" * (width - 2) + "+")

        for block in self.blocks:
            bar_len = int((block.duration_ms / max_duration) * bar_width) if max_duration > 0 else 0
            bar = "█" * bar_len
            duration_str = f"{block.duration_ms:.0f}ms"
            line = f"| {block.name:<{max_name_len}}  {bar:<{bar_width}} {duration_str:>6} |"
            lines.append(line)

        lines.append("+" + "-" * (width - 2) + "+")
        total_str = f"{self.total_ms():.0f}ms"
        lines.append(f"| {'TOTAL':<{max_name_len}}  {'':<{bar_width}} {total_str:>6} |")
        lines.append("+" + "-" * (width - 2) + "+")

        return "\n".join(lines)

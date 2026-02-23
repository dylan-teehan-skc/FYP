"""Mode selector for exploration vs guided execution."""

from dataclasses import dataclass
from typing import Any

from utils.logger import get_logger


@dataclass
class OptimalPath:
    """Represents an optimal workflow path."""

    workflow_type: str
    steps: list[str]
    avg_duration_ms: float
    success_rate: float


class ModeSelector:
    """Decides between exploration and guided execution modes."""

    def __init__(
        self,
        similarity_threshold: float = 0.60,
        min_executions: int = 10,
        min_success_rate: float = 0.85,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.min_executions = min_executions
        self.min_success_rate = min_success_rate
        self.log = get_logger("ModeSelector")

    def select_mode(self, task: str) -> tuple[str, OptimalPath | None]:
        """
        Select execution mode based on task similarity to past workflows.

        Returns ("exploration", None) or ("guided", OptimalPath).
        """
        # TODO: Implement semantic search against analytics-db
        # For now, always return exploration mode
        self.log.info("mode_selected", mode="exploration", task=task[:50])
        return ("exploration", None)

    def _find_similar_workflows(self, task: str) -> list[dict[str, Any]]:
        """Search for similar past workflows."""
        # TODO: Query analytics-db with pgvector semantic search
        return []

    def _get_optimal_path(self, workflow_type: str) -> OptimalPath | None:
        """Retrieve optimal path for a workflow type."""
        # TODO: Query workflow_graphs table
        return None

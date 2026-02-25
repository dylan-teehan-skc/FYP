"""Tests for the pipeline orchestrator."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

from analysis.clustering import ClusterResult
from analysis.config import Settings
from analysis.models import WorkflowTrace
from analysis.pipeline import run_analysis, run_analysis_for_cluster
from tests.conftest import MockAnalysisDatabase, make_event


def _sample_events() -> list[dict]:
    """Raw DB-style event dicts (asyncpg Records are dict-like)."""
    from datetime import datetime

    return [
        {
            "event_id": "evt-1",
            "workflow_id": "wf-1",
            "timestamp": datetime(2025, 2, 23, 10, 0, 1, tzinfo=UTC),
            "activity": "tool_call:check_ticket",
            "agent_name": "agent",
            "agent_role": "triage",
            "tool_name": "check_ticket",
            "tool_parameters": {},
            "tool_response": {},
            "llm_model": "",
            "llm_prompt_tokens": 0,
            "llm_completion_tokens": 0,
            "llm_reasoning": "",
            "duration_ms": 200.0,
            "cost_usd": 0.001,
            "status": "success",
            "error_message": None,
            "step_number": 1,
            "parent_event_id": None,
        },
        {
            "event_id": "evt-2",
            "workflow_id": "wf-1",
            "timestamp": datetime(2025, 2, 23, 10, 0, 2, tzinfo=UTC),
            "activity": "workflow:complete",
            "agent_name": "agent",
            "agent_role": "triage",
            "tool_name": None,
            "tool_parameters": {},
            "tool_response": {},
            "llm_model": "",
            "llm_prompt_tokens": 0,
            "llm_completion_tokens": 0,
            "llm_reasoning": "",
            "duration_ms": 400.0,
            "cost_usd": 0.001,
            "status": "success",
            "error_message": None,
            "step_number": 2,
            "parent_event_id": None,
        },
    ]


class TestRunAnalysisForCluster:
    async def test_returns_result(self) -> None:
        mock_db = MockAnalysisDatabase()
        mock_db.fetch_workflow_events = AsyncMock(return_value=_sample_events())

        settings = Settings(
            database_url="postgresql://test:test@localhost/test",
        )
        result = await run_analysis_for_cluster(
            mock_db, "refund", ["wf-1"], settings
        )
        assert result.task_cluster == "refund"
        assert result.traces_analyzed == 1

    async def test_empty_workflow_ids(self) -> None:
        mock_db = MockAnalysisDatabase()
        settings = Settings(
            database_url="postgresql://test:test@localhost/test",
        )
        result = await run_analysis_for_cluster(mock_db, "empty", [], settings)
        assert result.task_cluster == "empty"
        assert result.traces_analyzed == 0

    async def test_upserts_optimal_path(self) -> None:
        mock_db = MockAnalysisDatabase()
        mock_db.fetch_workflow_events = AsyncMock(return_value=_sample_events())

        settings = Settings(
            database_url="postgresql://test:test@localhost/test",
        )

        # Run with enough traces to potentially generate a path
        result = await run_analysis_for_cluster(
            mock_db, "refund", ["wf-1"], settings
        )
        # If an optimal path was found, verify upsert was called
        if result.optimal_path:
            mock_db.upsert_optimal_path.assert_called_once()


class TestRunAnalysis:
    @patch("analysis.pipeline.generate_cluster_name")
    @patch("analysis.pipeline.cluster_by_embedding")
    @patch("analysis.pipeline.reconstruct_trace")
    @patch("analysis.pipeline.subcluster_by_trace")
    async def test_runs_full_pipeline(
        self,
        mock_subcluster: MagicMock,
        mock_reconstruct: AsyncMock,
        mock_cluster: AsyncMock,
        mock_naming: AsyncMock,
    ) -> None:
        mock_db = MockAnalysisDatabase()
        settings = Settings(
            database_url="postgresql://test:test@localhost/test",
        )

        # Set up clustering to return one cluster with one workflow
        mock_cluster.return_value = {
            "refund": ClusterResult(["wf-1"], ["process refund"]),
        }
        mock_naming.return_value = "Refund Processing"

        # Set up trace reconstruction
        trace = WorkflowTrace(
            workflow_id="wf-1",
            events=[make_event(tool_name="a", step_number=1)],
            tool_sequence=["a"],
            total_duration_ms=200.0,
            total_steps=1,
            success=True,
        )
        mock_reconstruct.return_value = trace
        mock_subcluster.return_value = {"subcluster_0": [trace]}

        results = await run_analysis(mock_db, settings)
        # 1 subcluster + 1 group-level = 2
        assert len(results) == 2
        assert results[0].task_cluster == "Refund Processing"

    @patch("analysis.pipeline.cluster_by_embedding")
    async def test_no_clusters(self, mock_cluster: AsyncMock) -> None:
        mock_db = MockAnalysisDatabase()
        settings = Settings(
            database_url="postgresql://test:test@localhost/test",
        )
        mock_cluster.return_value = {}

        results = await run_analysis(mock_db, settings)
        assert results == []

    @patch("analysis.pipeline.generate_cluster_name")
    @patch("analysis.pipeline.cluster_by_embedding")
    @patch("analysis.pipeline.reconstruct_trace")
    @patch("analysis.pipeline.subcluster_by_trace")
    async def test_multiple_subclusters(
        self,
        mock_subcluster: MagicMock,
        mock_reconstruct: AsyncMock,
        mock_cluster: AsyncMock,
        mock_naming: AsyncMock,
    ) -> None:
        mock_db = MockAnalysisDatabase()
        settings = Settings(
            database_url="postgresql://test:test@localhost/test",
        )

        mock_cluster.return_value = {
            "refund": ClusterResult(["wf-1", "wf-2"], ["refund A", "refund B"]),
        }
        mock_naming.return_value = "Refund Processing"

        t1 = WorkflowTrace(
            workflow_id="wf-1",
            events=[make_event(tool_name="a", step_number=1)],
            tool_sequence=["a"],
            total_duration_ms=200.0,
            total_steps=1,
            success=True,
        )
        t2 = WorkflowTrace(
            workflow_id="wf-2",
            events=[make_event(tool_name="x", step_number=1)],
            tool_sequence=["x"],
            total_duration_ms=300.0,
            total_steps=1,
            success=True,
        )
        # reconstruct_trace is called 2x in run_analysis (level-1 loop)
        # + 1x per sub-cluster in run_analysis_for_cluster (level-2 loop)
        # + 2x for group-level run_analysis_for_cluster = 6 total
        mock_reconstruct.side_effect = [t1, t2, t1, t2, t1, t2]
        mock_subcluster.return_value = {
            "subcluster_0": [t1],
            "subcluster_1": [t2],
        }

        results = await run_analysis(mock_db, settings)
        # 2 subclusters + 1 group-level = 3
        assert len(results) == 3
        # Multiple subclusters → labels include sub_label
        labels = {r.task_cluster for r in results}
        assert any("subcluster" in label for label in labels)
        # Group-level result uses parent cluster name
        assert "Refund Processing" in labels

"""Tests for two-level clustering (embedding + edit distance)."""

from __future__ import annotations

import pytest

from analysis.clustering import (
    assign_cluster_label,
    cluster_by_embedding,
    cosine_similarity,
    edit_distance,
    normalized_edit_distance,
    subcluster_by_trace,
)
from analysis.models import WorkflowTrace
from tests.conftest import MockAnalysisDatabase, make_event


def _trace(
    wf_id: str = "wf-1",
    tools: list[str] | None = None,
) -> WorkflowTrace:
    tools = tools or ["a", "b"]
    events = [
        make_event(workflow_id=wf_id, tool_name=t, step_number=i + 1)
        for i, t in enumerate(tools)
    ]
    return WorkflowTrace(
        workflow_id=wf_id,
        events=events,
        tool_sequence=tools,
        total_duration_ms=500.0,
        total_steps=len(tools),
        success=True,
    )


# ── cosine_similarity ────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_different_lengths(self) -> None:
        assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_zero_vector(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_empty_vectors(self) -> None:
        assert cosine_similarity([], []) == 0.0


# ── edit_distance ────────────────────────────────────────────────────

class TestEditDistance:
    def test_identical_sequences(self) -> None:
        assert edit_distance(["a", "b"], ["a", "b"]) == 0

    def test_one_insertion(self) -> None:
        assert edit_distance(["a", "b"], ["a", "c", "b"]) == 1

    def test_complete_replacement(self) -> None:
        assert edit_distance(["a", "b"], ["c", "d"]) == 2

    def test_empty_sequences(self) -> None:
        assert edit_distance([], []) == 0

    def test_one_empty(self) -> None:
        assert edit_distance(["a", "b"], []) == 2


# ── normalized_edit_distance ─────────────────────────────────────────

class TestNormalizedEditDistance:
    def test_identical_sequences(self) -> None:
        assert normalized_edit_distance(["a", "b"], ["a", "b"]) == 0.0

    def test_completely_different(self) -> None:
        assert normalized_edit_distance(["a", "b"], ["c", "d"]) == pytest.approx(1.0)

    def test_one_insertion(self) -> None:
        # edit_distance=1, lengths 2+3=5, NED = 2*1/5 = 0.4
        assert normalized_edit_distance(["a", "b"], ["a", "c", "b"]) == pytest.approx(0.4)

    def test_different_lengths(self) -> None:
        # edit_distance=2, lengths 2+0=2, NED = 2*2/2 = 2.0 → clamped by formula
        assert normalized_edit_distance(["a", "b"], []) == pytest.approx(2.0)

    def test_both_empty(self) -> None:
        assert normalized_edit_distance([], []) == 0.0

    def test_length_normalized(self) -> None:
        short_ned = normalized_edit_distance(["a", "b"], ["a", "c"])
        long_ned = normalized_edit_distance(
            ["a", "b", "c", "d"], ["a", "b", "c", "e"],
        )
        assert short_ned > long_ned


# ── assign_cluster_label ─────────────────────────────────────────────

class TestAssignClusterLabel:
    def test_picks_shortest(self) -> None:
        assert assign_cluster_label(["refund request", "refund", "process refund"]) == "refund"

    def test_empty(self) -> None:
        assert assign_cluster_label([]) == "unknown"


# ── cluster_by_embedding ─────────────────────────────────────────────

class TestClusterByEmbedding:
    async def test_empty_embeddings(self, mock_db: MockAnalysisDatabase) -> None:
        mock_db.fetch_all_embeddings.return_value = []
        result = await cluster_by_embedding(mock_db)
        assert result == {}

    async def test_clusters_similar(self, mock_db: MockAnalysisDatabase) -> None:
        emb = [0.1] * 10
        mock_db.fetch_all_embeddings.return_value = [
            {"workflow_id": f"wf-{i}", "task_description": "refund", "embedding": emb}
            for i in range(5)
        ]
        result = await cluster_by_embedding(mock_db, similarity_threshold=0.9, min_executions=3)
        assert len(result) == 1
        assert len(list(result.values())[0]) == 5

    async def test_min_executions_filter(self, mock_db: MockAnalysisDatabase) -> None:
        emb = [0.1] * 10
        mock_db.fetch_all_embeddings.return_value = [
            {"workflow_id": "wf-1", "task_description": "refund", "embedding": emb},
            {"workflow_id": "wf-2", "task_description": "refund", "embedding": emb},
        ]
        result = await cluster_by_embedding(mock_db, min_executions=3)
        assert result == {}  # only 2 workflows, need 3

    async def test_dissimilar_embeddings(self, mock_db: MockAnalysisDatabase) -> None:
        mock_db.fetch_all_embeddings.return_value = [
            {"workflow_id": "wf-1", "task_description": "refund",
             "embedding": [1.0, 0.0, 0.0]},
            {"workflow_id": "wf-2", "task_description": "refund",
             "embedding": [1.0, 0.0, 0.0]},
            {"workflow_id": "wf-3", "task_description": "refund",
             "embedding": [1.0, 0.0, 0.0]},
            {"workflow_id": "wf-4", "task_description": "cancel",
             "embedding": [0.0, 1.0, 0.0]},
            {"workflow_id": "wf-5", "task_description": "cancel",
             "embedding": [0.0, 1.0, 0.0]},
            {"workflow_id": "wf-6", "task_description": "cancel",
             "embedding": [0.0, 1.0, 0.0]},
        ]
        result = await cluster_by_embedding(mock_db, similarity_threshold=0.9, min_executions=3)
        assert len(result) == 2  # two clusters

    async def test_handles_string_embeddings(self, mock_db: MockAnalysisDatabase) -> None:
        mock_db.fetch_all_embeddings.return_value = [
            {"workflow_id": f"wf-{i}", "task_description": "refund",
             "embedding": "[0.1,0.2,0.3]"}
            for i in range(3)
        ]
        result = await cluster_by_embedding(mock_db, min_executions=3)
        assert len(result) == 1


# ── subcluster_by_trace ──────────────────────────────────────────────

class TestSubclusterByTrace:
    def test_groups_similar_traces(self) -> None:
        t1 = _trace(wf_id="wf-1", tools=["a", "b"])
        t2 = _trace(wf_id="wf-2", tools=["a", "b"])
        t3 = _trace(wf_id="wf-3", tools=["a", "b", "c"])  # NED ≈ 0.4
        result = subcluster_by_trace([t1, t2, t3], ned_threshold=0.5)
        assert len(result) == 1  # all in one cluster

    def test_splits_divergent_traces(self) -> None:
        t1 = _trace(wf_id="wf-1", tools=["a", "b"])
        t2 = _trace(wf_id="wf-2", tools=["x", "y", "z"])  # NED ≈ 1.0
        result = subcluster_by_trace([t1, t2], ned_threshold=0.5)
        assert len(result) == 2

    def test_empty_traces(self) -> None:
        assert subcluster_by_trace([]) == {}

    def test_single_trace(self) -> None:
        t1 = _trace(wf_id="wf-1", tools=["a", "b"])
        result = subcluster_by_trace([t1])
        assert len(result) == 1

    def test_consolidates_with_more_data(self) -> None:
        """HAC should produce fewer clusters than traces when sequences are similar."""
        traces = [
            _trace(wf_id=f"wf-{i}", tools=["a", "b", "c", "d", "e", "f"])
            for i in range(10)
        ] + [
            _trace(wf_id=f"wf-{i+10}", tools=["a", "b", "c", "d", "e", "f", "g"])
            for i in range(5)
        ]
        result = subcluster_by_trace(traces, ned_threshold=0.4)
        assert len(result) <= 2  # similar sequences should consolidate

"""Two-level workflow clustering: semantic embeddings + trace edit distance."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

from analysis.logger import get_logger
from analysis.models import WorkflowTrace

if TYPE_CHECKING:
    from analysis.database import Database

log = get_logger("analysis.clustering")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (pure Python)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def edit_distance(seq_a: list[str], seq_b: list[str]) -> int:
    """Levenshtein edit distance between two tool name sequences."""
    m, n = len(seq_a), len(seq_b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if seq_a[i - 1] == seq_b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def normalized_edit_distance(seq_a: list[str], seq_b: list[str]) -> float:
    """Normalized edit distance in [0, 1]; 0 = identical, 1 = maximally different."""
    if not seq_a and not seq_b:
        return 0.0
    raw = edit_distance(seq_a, seq_b)
    return (2 * raw) / (len(seq_a) + len(seq_b))


class ClusterResult:
    """Result of Level-1 embedding clustering."""

    __slots__ = ("workflow_ids", "descriptions")

    def __init__(self, workflow_ids: list[str], descriptions: list[str]) -> None:
        self.workflow_ids = workflow_ids
        self.descriptions = descriptions


async def cluster_by_embedding(
    db: Database,
    similarity_threshold: float = 0.60,
    min_executions: int = 3,
) -> dict[str, ClusterResult]:
    """Group workflow_ids by task description embedding similarity.

    Level 1 clustering: HAC with average linkage on cosine distances.
    Returns {cluster_key: ClusterResult(workflow_ids, descriptions)}.
    """
    rows = await db.fetch_all_embeddings()
    if not rows:
        return {}

    items: list[dict[str, Any]] = []
    for r in rows:
        embedding = r["embedding"]
        if embedding is None:
            continue
        if isinstance(embedding, str):
            embedding = [float(x) for x in embedding.strip("[]").split(",")]
        items.append({
            "workflow_id": str(r["workflow_id"]),
            "description": r["task_description"],
            "embedding": embedding,
        })

    if not items:
        return {}

    if len(items) == 1:
        return {"cluster_0": ClusterResult(
            [items[0]["workflow_id"]], [items[0]["description"]],
        )}

    n = len(items)
    condensed = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = cosine_similarity(items[i]["embedding"], items[j]["embedding"])
            condensed.append(max(0.0, 1.0 - sim))

    z = linkage(np.array(condensed), method="average")
    labels = fcluster(z, t=1.0 - similarity_threshold, criterion="distance")

    raw_clusters: dict[int, ClusterResult] = {}
    for item, label in zip(items, labels):
        raw_clusters.setdefault(label, ClusterResult([], []))
        raw_clusters[label].workflow_ids.append(item["workflow_id"])
        raw_clusters[label].descriptions.append(item["description"])

    clusters = {
        f"cluster_{label}": cr for label, cr in raw_clusters.items()
        if len(cr.workflow_ids) >= min_executions
    }

    log.info("embedding_clusters", count=len(clusters))
    return clusters


def subcluster_by_trace(
    traces: list[WorkflowTrace],
    ned_threshold: float = 0.55,
) -> dict[str, list[WorkflowTrace]]:
    """Within a semantic cluster, sub-cluster by trace structure.

    Level 2 clustering: Hierarchical Agglomerative Clustering (HAC) with
    average linkage on a Normalized Edit Distance matrix.
    Returns {sub_label: [traces...]}.
    """
    if not traces:
        return {}
    if len(traces) == 1:
        return {"subcluster_0": traces}

    n = len(traces)
    condensed = []
    for i in range(n):
        for j in range(i + 1, n):
            condensed.append(normalized_edit_distance(
                traces[i].tool_sequence, traces[j].tool_sequence,
            ))

    z = linkage(np.array(condensed), method="average")
    labels = fcluster(z, t=ned_threshold, criterion="distance")

    subclusters: dict[str, list[WorkflowTrace]] = {}
    for trace, label in zip(traces, labels):
        key = f"subcluster_{label - 1}"
        subclusters.setdefault(key, []).append(trace)

    log.info("trace_subclusters", count=len(subclusters))
    return subclusters

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


def assign_cluster_label(descriptions: list[str]) -> str:
    """Choose a representative label for a cluster (shortest description)."""
    if not descriptions:
        return "unknown"
    return min(descriptions, key=len)


async def cluster_by_embedding(
    db: Database,
    similarity_threshold: float = 0.60,
    min_executions: int = 3,
) -> dict[str, list[str]]:
    """Group workflow_ids by task description embedding similarity.

    Level 1 clustering: greedy cosine similarity on pgvector embeddings.
    Returns {cluster_label: [workflow_id, ...]}.
    """
    rows = await db.fetch_all_embeddings()
    if not rows:
        return {}

    # Parse embedding data
    items: list[dict[str, Any]] = []
    for r in rows:
        embedding = r["embedding"]
        if embedding is None:
            continue
        # asyncpg may return embedding as string or list
        if isinstance(embedding, str):
            embedding = [float(x) for x in embedding.strip("[]").split(",")]
        items.append({
            "workflow_id": str(r["workflow_id"]),
            "description": r["task_description"],
            "embedding": embedding,
        })

    if not items:
        return {}

    # Greedy clustering
    assigned: set[int] = set()
    clusters: dict[str, list[str]] = {}

    for i, item in enumerate(items):
        if i in assigned:
            continue

        cluster_ids = [item["workflow_id"]]
        cluster_descs = [item["description"]]
        assigned.add(i)

        for j in range(i + 1, len(items)):
            if j in assigned:
                continue
            sim = cosine_similarity(item["embedding"], items[j]["embedding"])
            if sim >= similarity_threshold:
                cluster_ids.append(items[j]["workflow_id"])
                cluster_descs.append(items[j]["description"])
                assigned.add(j)

        if len(cluster_ids) >= min_executions:
            label = assign_cluster_label(cluster_descs)
            clusters[label] = cluster_ids

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

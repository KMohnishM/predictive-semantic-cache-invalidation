"""Shared retrieval-ranking and retrieval-fidelity primitives.

Used by both the standalone benchmarking pipeline (src/benchmarking/) and
Pipeline A's ground-truth generation (src/embedder/, src/predictor/), so
that "did entity X rank within the top-K for query Y" is computed by one
piece of code, not two independently-written implementations that might
silently disagree.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from embedder.util import compute_cosine_similarity


def rank_entities(
    query_embedding: np.ndarray,
    entity_embeddings: Dict[str, np.ndarray],
    top_k: int | None = None,
) -> List[Tuple[str, float]]:
    """
    Rank entities by cosine similarity to a query embedding.

    Mirrors EmbeddingManager.find_similar_entities, but as a standalone
    function so callers that only need to rank an already-built embedding
    matrix (e.g. the leave-one-out ground-truth generator) don't need a
    live EmbeddingManager instance.

    Args:
        query_embedding: Query embedding vector.
        entity_embeddings: Dict of entity_id -> embedding vector.
        top_k: If given, return only the top-K entries. If None, return the
            full ranking (needed when the caller must know the rank of a
            specific target entity even if it falls outside any top-K).

    Returns:
        List of (entity_id, similarity_score) tuples, sorted descending.
    """
    similarities = [
        (entity_id, compute_cosine_similarity(query_embedding, embedding))
        for entity_id, embedding in entity_embeddings.items()
    ]
    similarities.sort(key=lambda pair: pair[1], reverse=True)
    return similarities[:top_k] if top_k is not None else similarities


def compute_rank(ranked_ids: List[str], target_id: str) -> int:
    """
    1-indexed rank of target_id within ranked_ids.

    If target_id is absent, returns len(ranked_ids) + 1 — i.e. "worse than
    last place" — matching the convention already used inline in
    src/benchmarking/runner.py before this extraction.
    """
    if target_id in ranked_ids:
        return ranked_ids.index(target_id) + 1
    return len(ranked_ids) + 1


def recall_at_k(ranked_ids: List[str], target_id: str, k: int) -> float:
    """Compute binary Recall@K for target_id within ranked_ids.

    Args:
        ranked_ids: List of ranked entity IDs.
        target_id: Target entity ID.
        k: Top-K cutoff rank.

    Returns:
        1.0 if target_id is present in top-K, 0.0 otherwise.
    """
    return 1.0 if target_id in ranked_ids[:k] else 0.0


def mean_reciprocal_rank(ranked_ids: List[str], target_id: str) -> float:
    """Compute Mean Reciprocal Rank (MRR) for target_id within ranked_ids.

    Args:
        ranked_ids: List of ranked entity IDs.
        target_id: Target entity ID.

    Returns:
        Reciprocal rank score (1 / rank) or 0.0 if not found.
    """
    for index, entity_id in enumerate(ranked_ids, start=1):
        if entity_id == target_id:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: List[str], target_id: str, k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain at K (nDCG@K) for a single target ID.

    Args:
        ranked_ids: List of ranked entity IDs.
        target_id: Target entity ID.
        k: Cutoff rank K.

    Returns:
        nDCG@K score in range [0.0, 1.0].
    """
    top_k = ranked_ids[:k]
    if target_id not in top_k:
        return 0.0
    rank = top_k.index(target_id) + 1
    return 1.0 / np.log2(rank + 1)


def rank_delta(baseline_rank: int, selective_rank: int) -> int:
    """Compute rank displacement delta between baseline and selective invalidation.

    Args:
        baseline_rank: Rank under full re-indexing baseline.
        selective_rank: Rank under selective invalidation strategy.

    Returns:
        Integer rank difference (selective_rank - baseline_rank).
    """
    return selective_rank - baseline_rank


def score_delta(baseline_score: float, selective_score: float) -> float:
    """Compute similarity score delta between baseline and selective invalidation.

    Args:
        baseline_score: Similarity score under full re-indexing baseline.
        selective_score: Similarity score under selective invalidation strategy.

    Returns:
        Float score difference (selective_score - baseline_score).
    """
    return selective_score - baseline_score

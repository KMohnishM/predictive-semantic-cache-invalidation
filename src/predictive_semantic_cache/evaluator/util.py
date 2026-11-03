"""Stateless ranking-metric helpers for strategy evaluation."""

from typing import Dict, List

import numpy as np
from scipy.stats import spearmanr


def compute_recall_at_k(retrieved: List[str], ground_truth: List[str],
                        k: int = 5) -> float:
    """
    Compute Recall@K.

    Args:
        retrieved: List of retrieved entity IDs (ranked)
        ground_truth: List of relevant entity IDs
        k: Number of top results to consider

    Returns:
        Recall@K score
    """
    if not ground_truth:
        return 0.0

    top_k = retrieved[:k]
    relevant_retrieved = set(top_k) & set(ground_truth)
    return len(relevant_retrieved) / len(ground_truth)


def compute_mrr(retrieved: List[str], ground_truth: List[str]) -> float:
    """
    Compute Mean Reciprocal Rank (MRR).

    The reciprocal rank is 1 / rank_of_first_relevant_result.
    Returns 0 if no relevant result is found.

    Args:
        retrieved:    Ranked list of entity IDs.
        ground_truth: Set of relevant entity IDs.

    Returns:
        Reciprocal rank score in [0, 1].
    """
    gt_set = set(ground_truth)
    for rank, eid in enumerate(retrieved, start=1):
        if eid in gt_set:
            return 1.0 / rank
    return 0.0


def compute_ndcg_at_k(retrieved: List[str], ground_truth: List[str],
                      k: int = 10) -> float:
    """
    Compute Normalised Discounted Cumulative Gain at K (nDCG@K).

    Relevance is binary (1 if in ground truth, 0 otherwise).
    nDCG@K = DCG@K / IDCG@K.

    Args:
        retrieved:    Ranked list of entity IDs.
        ground_truth: List of relevant entity IDs.
        k:            Cut-off rank.

    Returns:
        nDCG@K score in [0, 1].
    """
    if not ground_truth:
        return 0.0

    gt_set = set(ground_truth)
    top_k  = retrieved[:k]

    # DCG
    dcg = sum(
        (1.0 / np.log2(rank + 2))  # log2(rank+2) because rank is 0-indexed
        for rank, eid in enumerate(top_k)
        if eid in gt_set
    )

    # IDCG — ideal ranking: all relevant docs at the top
    n_relevant = min(len(gt_set), k)
    idcg = sum(1.0 / np.log2(rank + 2) for rank in range(n_relevant))

    return dcg / idcg if idcg > 0 else 0.0


def compute_spearman_correlation(rankings1: Dict[str, float],
                                 rankings2: Dict[str, float]) -> float:
    """
    Compute Spearman's rank correlation between two rankings.

    Args:
        rankings1: First ranking (entity_id -> score)
        rankings2: Second ranking (entity_id -> score)

    Returns:
        Spearman correlation coefficient
    """
    # Get common entities
    common_ids = set(rankings1.keys()) & set(rankings2.keys())

    if len(common_ids) < 2:
        return 0.0

    # Extract scores in same order
    scores1 = [rankings1[eid] for eid in common_ids]
    scores2 = [rankings2[eid] for eid in common_ids]

    # Compute correlation
    correlation, _ = spearmanr(scores1, scores2)

    return correlation if not np.isnan(correlation) else 0.0

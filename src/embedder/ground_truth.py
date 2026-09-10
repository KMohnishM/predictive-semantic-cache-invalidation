"""Leave-one-out, rank-displacement ground-truth generation for the drift
predictor (Pipeline A).

Replaces the self-referential "did the raw cosine distance cross an
arbitrary threshold" label with an operationally-grounded one: for each
entity, does *retaining its stale (pre-commit) embedding* — while every
other entity stays fresh — actually change what gets retrieved for a
realistic, independently-authored query workload.

Query independence is load-bearing here: queries MUST come from
src/benchmarking/data/curated_queries.json (hand-authored, fixed
target_entity_id, no involvement of the embedding model being evaluated) —
never from run_experiment.py::_generate_queries(), which selects entities
by the model's own drift score and builds query text from the target's own
docstring, both of which reintroduce circularity. See
docs/ground_truth_method_comparison.md for the full rationale.

This module intentionally stops at continuous, raw scores (displacement
counts and per-query nDCG deltas) — binarizing them via a significance
test (Wilcoxon) is a separate, later step (Phase 4), so the two concerns
don't get tangled together.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# src/benchmarking/query_sources.py::load_curated_queries and its QueryCase
# type are the independent, non-circular query source this module requires.
try:
    from benchmarking.query_sources import load_curated_queries
    from benchmarking.types import QueryCase
except ImportError:
    from src.benchmarking.query_sources import load_curated_queries
    from src.benchmarking.types import QueryCase


DEFAULT_CURATED_QUERIES_PATH = str(
    Path(__file__).resolve().parent.parent / "benchmarking" / "data" / "curated_queries.json"
)


@dataclass
class LeaveOneOutResult:
    """Per-entity leave-one-out operational-staleness signal."""

    entity_id: str
    displaced_query_count: int
    evaluated_query_count: int
    ndcg_deltas: List[float] = field(default_factory=list)

    @property
    def mean_ndcg_delta(self) -> float:
        return float(np.mean(self.ndcg_deltas)) if self.ndcg_deltas else 0.0

    @property
    def any_displacement(self) -> bool:
        return self.displaced_query_count > 0


def _ndcg_gain(rank: int, top_k: int) -> float:
    """Single-relevant-document nDCG@k gain for a given rank (1-indexed)."""
    if rank > top_k:
        return 0.0
    return 1.0 / np.log2(rank + 1)


def compute_leave_one_out_scores(
    embeddings_before: Dict[str, np.ndarray],
    embeddings_after: Dict[str, np.ndarray],
    queries: List["QueryCase"],
    query_embeddings: Dict[str, np.ndarray],
    top_k: int = 10,
) -> Dict[str, LeaveOneOutResult]:
    """
    Compute the leave-one-out rank-displacement / nDCG-delta signal for
    every entity common to embeddings_before and embeddings_after.

    Args:
        embeddings_before: entity_id -> embedding, pre-commit.
        embeddings_after:  entity_id -> embedding, post-commit.
        queries: Curated QueryCase list (see load_ground_truth_queries).
        query_embeddings: query_id -> embedding, pre-computed once by the
            caller (queries are fixed across commit pairs, so callers
            should embed them once, not per commit pair).
        top_k: Context-window size (K) used for both the displacement
            check and the nDCG computation. Should match whatever K the
            downstream retrieval system actually serves.

    Returns:
        Dict entity_id -> LeaveOneOutResult, for every entity present in
        both embeddings_before and embeddings_after.
    """
    entity_ids = sorted(set(embeddings_before.keys()) & set(embeddings_after.keys()))
    if not entity_ids:
        return {}

    idx_of = {eid: i for i, eid in enumerate(entity_ids)}
    n = len(entity_ids)

    # Only queries whose target actually exists in this snapshot AND whose
    # embedding was supplied can be evaluated for this commit pair.
    usable_queries = [
        q for q in queries
        if q.target_entity_id in idx_of and q.query_id in query_embeddings
    ]
    skipped = len(queries) - len(usable_queries)
    if skipped:
        logger.info(
            f"compute_leave_one_out_scores: skipping {skipped}/{len(queries)} curated "
            f"queries whose target entity is absent from this snapshot."
        )
    if not usable_queries:
        logger.warning(
            "compute_leave_one_out_scores: no usable curated queries for this snapshot "
            "— returning zero-evaluated results for all entities."
        )
        return {
            eid: LeaveOneOutResult(entity_id=eid, displaced_query_count=0, evaluated_query_count=0)
            for eid in entity_ids
        }

    m = len(usable_queries)
    target_idx = np.array([idx_of[q.target_entity_id] for q in usable_queries])  # (m,)

    E_after = np.stack([embeddings_after[eid] for eid in entity_ids])  # (n, d)
    Q = np.stack([query_embeddings[q.query_id] for q in usable_queries])  # (m, d)

    # Embeddings are L2-normalized by EmbeddingManager, so dot product ==
    # cosine similarity — matches src/common/retrieval_metrics.py.
    S_fresh = Q @ E_after.T  # (m, n): S_fresh[q, j] = similarity(query q, entity j) fully fresh

    # Rank of every entity for every query, fully fresh (1-indexed). Two
    # argsorts on the negated scores give dense ranks without a manual
    # per-row Python sort.
    order = np.argsort(-S_fresh, axis=1)
    rank_fresh_all = np.empty_like(order)
    rows = np.arange(m)[:, None]
    rank_fresh_all[rows, order] = np.arange(1, n + 1)[None, :]  # (m, n)

    rank_fresh_of_target = rank_fresh_all[rows[:, 0], target_idx]  # (m,)
    score_of_target = S_fresh[rows[:, 0], target_idx]  # (m,)

    results: Dict[str, LeaveOneOutResult] = {}

    for eid in entity_ids:
        if eid not in embeddings_before:
            continue
        i = idx_of[eid]

        sims_i_stale = Q @ embeddings_before[eid]  # (m,) — entity i's stale-vector similarity per query
        sims_i_fresh = S_fresh[:, i]  # (m,)

        # --- D(i, q): did entity i itself fall out of the top-K? ---
        # Only entity i's own score changes; recompute its rank in the
        # stale-i matrix by counting how many OTHER entities now score
        # higher than its new (stale) score.
        higher_incl_self = (S_fresh > sims_i_stale[:, None]).sum(axis=1)  # (m,)
        self_would_count_itself = (S_fresh[:, i] > sims_i_stale).astype(int)  # (m,)
        rank_stale_of_i = higher_incl_self - self_would_count_itself + 1  # (m,)
        rank_fresh_of_i = rank_fresh_all[:, i]  # (m,)

        displaced_mask = (rank_fresh_of_i <= top_k) & (rank_stale_of_i > top_k)
        displaced_query_count = int(displaced_mask.sum())

        # --- nDCG delta w.r.t. each query's own curated target entity ---
        is_self_target = target_idx == i
        i_orig_gt_target = (sims_i_fresh > score_of_target).astype(int)
        i_new_gt_target = (sims_i_stale > score_of_target).astype(int)

        # When entity i IS the query's target, its stale rank is exactly
        # rank_stale_of_i (already computed above). Otherwise, only entity
        # i's own crossing of the target's score can move the target's
        # rank by +-1 per query — every other entity's relative order to
        # the target is unchanged.
        rank_stale_of_target = np.where(
            is_self_target,
            rank_stale_of_i,
            rank_fresh_of_target - i_orig_gt_target + i_new_gt_target,
        )

        ndcg_fresh = np.array([_ndcg_gain(r, top_k) for r in rank_fresh_of_target])
        ndcg_stale = np.array([_ndcg_gain(r, top_k) for r in rank_stale_of_target])
        ndcg_deltas = (ndcg_fresh - ndcg_stale).tolist()

        results[eid] = LeaveOneOutResult(
            entity_id=eid,
            displaced_query_count=displaced_query_count,
            evaluated_query_count=m,
            ndcg_deltas=ndcg_deltas,
        )

    return results


def load_ground_truth_queries(path: Optional[str] = None) -> List["QueryCase"]:
    """Load the independent curated query set used as ground truth for
    leave-one-out scoring. Defaults to
    src/benchmarking/data/curated_queries.json.
    """
    return load_curated_queries(path or DEFAULT_CURATED_QUERIES_PATH)

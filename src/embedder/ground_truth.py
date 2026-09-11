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

compute_leave_one_out_scores() stops at continuous, raw scores
(displacement counts and per-query nDCG deltas) — binarize_ground_truth()
below turns those into the final Y_i label via a Wilcoxon signed-rank
significance test, kept as a separate step so "did retaining a stale
embedding measurably matter" and "was that measured effect statistically
real, not noise" stay two distinct, inspectable stages:

    Y_i = 1  if  (displaced_query_count >= 1)  AND  (p_i < alpha)
    Y_i = 0  otherwise
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scipy.stats import wilcoxon

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


# ---------------------------------------------------------------------------
# Phase 4: statistical significance + binarization
# ---------------------------------------------------------------------------

DEFAULT_ALPHA = 0.05
DEFAULT_MIN_NONZERO_QUERIES = 5


@dataclass
class GroundTruthLabel:
    """Final per-entity training label, plus everything needed to audit it."""

    entity_id: str
    label: int  # Y_i in {0, 1} — the value predictor.py should train against
    displaced_query_count: int
    evaluated_query_count: int
    nonzero_delta_count: int
    mean_ndcg_delta: float
    p_value: Optional[float]
    underpowered: bool


def compute_wilcoxon_significance(
    ndcg_deltas: List[float],
    alternative: str = "greater",
) -> Tuple[Optional[float], int]:
    """
    One-sided Wilcoxon signed-rank test: H1: E[ndcg_deltas] > 0, i.e. the
    fresh embedding measurably outperforms the stale one across the paired
    per-query nDCG differences.

    Returns (p_value, nonzero_count). p_value is None only when there is
    no data at all (empty deltas — e.g. no curated query had a target
    present in this snapshot). An all-zero deltas vector is a valid,
    meaningful result (no measurable effect anywhere) and returns p=1.0,
    not None — scipy.stats.wilcoxon raises ValueError on that input, so
    it's handled explicitly here rather than being an error.
    """
    if not ndcg_deltas:
        return None, 0

    nonzero_count = sum(1 for d in ndcg_deltas if d != 0.0)
    if nonzero_count == 0:
        return 1.0, 0

    try:
        _, p_value = wilcoxon(ndcg_deltas, alternative=alternative)
        return float(p_value), nonzero_count
    except ValueError as exc:
        # Defensive: scipy can still raise on pathological inputs we
        # haven't anticipated (e.g. a single non-zero difference under
        # some scipy versions' exact-method edge cases). Treat as "could
        # not establish significance" rather than propagating a crash
        # into dataset construction.
        logger.debug(f"wilcoxon() raised for deltas={ndcg_deltas!r}: {exc}")
        return None, nonzero_count


def binarize_ground_truth(
    loo_results: Dict[str, "LeaveOneOutResult"],
    alpha: float = DEFAULT_ALPHA,
    min_nonzero_queries: int = DEFAULT_MIN_NONZERO_QUERIES,
) -> Dict[str, GroundTruthLabel]:
    """
    Turn compute_leave_one_out_scores() output into the final Y_i label:

        Y_i = 1  if  (displaced_query_count >= 1)  AND  (p_i < alpha)
        Y_i = 0  otherwise

    Entities whose Wilcoxon test rests on fewer than min_nonzero_queries
    non-zero paired differences are labeled `underpowered=True` — the
    label is still computed (so training data isn't silently dropped),
    but callers (and the summary logged here) should not treat a
    significant p-value from an underpowered test as reliable.
    """
    labels: Dict[str, GroundTruthLabel] = {}
    underpowered_ids: List[str] = []
    positive_count = 0

    for entity_id, result in loo_results.items():
        p_value, nonzero_count = compute_wilcoxon_significance(result.ndcg_deltas)
        underpowered = nonzero_count < min_nonzero_queries
        if underpowered:
            underpowered_ids.append(entity_id)

        significant = p_value is not None and p_value < alpha
        label = 1 if (result.any_displacement and significant) else 0
        positive_count += label

        labels[entity_id] = GroundTruthLabel(
            entity_id=entity_id,
            label=label,
            displaced_query_count=result.displaced_query_count,
            evaluated_query_count=result.evaluated_query_count,
            nonzero_delta_count=nonzero_count,
            mean_ndcg_delta=result.mean_ndcg_delta,
            p_value=p_value,
            underpowered=underpowered,
        )

    total = len(labels)
    if underpowered_ids:
        logger.warning(
            f"binarize_ground_truth: {len(underpowered_ids)}/{total} entities have fewer than "
            f"{min_nonzero_queries} non-zero paired nDCG differences — their p-values are "
            f"statistically underpowered and should not be treated as reliable significance "
            f"tests. Consider adding more curated queries covering these entities."
        )
    if total:
        positive_rate = positive_count / total
        logger.info(
            f"binarize_ground_truth: {positive_count}/{total} entities ({positive_rate:.1%}) "
            f"labeled Y_i=1 (alpha={alpha}, min_nonzero_queries={min_nonzero_queries})."
        )
        if positive_rate == 0.0 or positive_rate == 1.0:
            logger.warning(
                f"binarize_ground_truth: label distribution is degenerate ({positive_rate:.0%} "
                f"positive) — this is either a genuine property of the sampled commits or a "
                f"sign the query set / top_k / alpha need review before training on this label."
            )

    return labels

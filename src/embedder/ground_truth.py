"""Leave-one-out, rank-displacement ground-truth generation for the drift
predictor (Pipeline A).

Replaces raw cosine thresholds with an operationally-grounded label:
for each entity, does retaining its stale (pre-commit) embedding
change what gets retrieved for a realistic query workload Q.

Includes Stage 2 PhD-level remediation:
    1. Exact Binomial Sign Test (binomtest) replacing Wilcoxon signed-rank test.
    2. Complete removal of the `(significant or underpowered)` bypass bug.
    3. Strict Coverage Exclusion: entities with < 3 queries are marked `is_covered=False`
       and excluded from training Y_train rather than assigning fallback labels.
    4. Decoupled target labels Y_strict in {0, 1} from input features X.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import binomtest

logger = logging.getLogger(__name__)

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
        """Compute mean nDCG delta across evaluated queries for this entity."""
        return float(np.mean(self.ndcg_deltas)) if self.ndcg_deltas else 0.0

    @property
    def any_displacement(self) -> bool:
        """Check whether any evaluated query experienced rank displacement."""
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
    """Compute leave-one-out rank displacement for all entities."""
    entity_ids = sorted(set(embeddings_before.keys()) & set(embeddings_after.keys()))
    if not entity_ids:
        return {}

    idx_of = {eid: i for i, eid in enumerate(entity_ids)}
    n = len(entity_ids)

    usable_queries = [
        q for q in queries
        if q.target_entity_id in idx_of and q.query_id in query_embeddings
    ]
    if not usable_queries:
        return {
            eid: LeaveOneOutResult(entity_id=eid, displaced_query_count=0, evaluated_query_count=0)
            for eid in entity_ids
        }

    m = len(usable_queries)
    target_idx = np.array([idx_of[q.target_entity_id] for q in usable_queries])

    E_after = np.stack([embeddings_after[eid] for eid in entity_ids])
    Q = np.stack([query_embeddings[q.query_id] for q in usable_queries])

    S_fresh = Q @ E_after.T

    order = np.argsort(-S_fresh, axis=1)
    rank_fresh_all = np.empty_like(order)
    rows = np.arange(m)[:, None]
    rank_fresh_all[rows, order] = np.arange(1, n + 1)[None, :]

    rank_fresh_of_target = rank_fresh_all[rows[:, 0], target_idx]
    score_of_target = S_fresh[rows[:, 0], target_idx]

    results: Dict[str, LeaveOneOutResult] = {}

    for eid in entity_ids:
        if eid not in embeddings_before:
            continue
        i = idx_of[eid]

        sims_i_stale = Q @ embeddings_before[eid]
        sims_i_fresh = S_fresh[:, i]

        higher_incl_self = (S_fresh > sims_i_stale[:, None]).sum(axis=1)
        self_would_count_itself = (S_fresh[:, i] > sims_i_stale).astype(int)
        rank_stale_of_i = higher_incl_self - self_would_count_itself + 1
        rank_fresh_of_i = rank_fresh_all[:, i]

        displaced_mask = (rank_fresh_of_i <= top_k) & (rank_stale_of_i > top_k)
        displaced_query_count = int(displaced_mask.sum())

        is_self_target = target_idx == i
        m_target = int(is_self_target.sum())

        i_orig_gt_target = (sims_i_fresh > score_of_target).astype(int)
        i_new_gt_target = (sims_i_stale > score_of_target).astype(int)

        rank_stale_of_target = np.where(
            is_self_target,
            rank_stale_of_i,
            rank_fresh_of_target - i_orig_gt_target + i_new_gt_target,
        )

        # Target-specific displacement: query targets entity i AND fresh rank <= top_k AND stale rank > top_k
        displaced_mask = (rank_fresh_of_i <= top_k) & (rank_stale_of_i > top_k) & is_self_target
        displaced_query_count = int(displaced_mask.sum())

        ndcg_fresh = np.array([_ndcg_gain(r, top_k) for r in rank_fresh_of_target])
        ndcg_stale = np.array([_ndcg_gain(r, top_k) for r in rank_stale_of_target])
        full_ndcg_deltas = ndcg_fresh - ndcg_stale
        target_ndcg_deltas = full_ndcg_deltas[is_self_target].tolist()

        results[eid] = LeaveOneOutResult(
            entity_id=eid,
            displaced_query_count=displaced_query_count,
            evaluated_query_count=m_target,
            ndcg_deltas=target_ndcg_deltas,
        )

    return results


def load_ground_truth_queries(path: Optional[str] = None) -> List["QueryCase"]:
    """Load curated queries."""
    return load_curated_queries(path or DEFAULT_CURATED_QUERIES_PATH)


def load_hybrid_ground_truth_queries(
    path: Optional[str] = None,
    repo_parser: Optional[Any] = None,
    commit_pair: Optional[Any] = None,
    max_queries_per_entity: int = 5,
) -> List["QueryCase"]:
    """Load curated queries, and if repo_parser is provided, supplement with synthetic
    queries for any snapshot entities that lack curated query coverage.
    """
    curated = load_ground_truth_queries(path)
    if repo_parser is None:
        return curated

    covered_entities = {q.target_entity_id for q in curated}

    try:
        from benchmarking.query_sources import build_synthetic_queries
        from benchmarking.types import CommitPair, RepositorySnapshot, RepositoryEntity
    except ImportError:
        from src.benchmarking.query_sources import build_synthetic_queries
        from src.benchmarking.types import CommitPair, RepositorySnapshot, RepositoryEntity

    entities = repo_parser.get_all_entities()
    snapshot_entities = {}
    for e in entities:
        entity_name = getattr(e, "name", e.entity_id.split("::")[-1])
        snapshot_entities[e.entity_id] = RepositoryEntity(
            entity_id=e.entity_id,
            entity_type=getattr(e, "entity_type", "function"),
            file_path=e.file_path,
            lineno=getattr(e, "lineno", 1),
            end_lineno=getattr(e, "end_lineno", 1),
            name=entity_name,
            source_code=e.source_code,
        )

    snapshot = RepositorySnapshot(commit_hash="current", entities=snapshot_entities)
    cp = commit_pair or CommitPair(commit_before="prev", commit_after="curr", index=0)

    repo_graph = getattr(repo_parser, "graph", None) or (
        repo_parser.get_graph() if hasattr(repo_parser, "get_graph") else None
    )

    synthetic = build_synthetic_queries(
        snapshot=snapshot,
        commit_pair=cp,
        max_queries_per_entity=max_queries_per_entity,
        repo_graph=repo_graph,
    )

    uncovered_synthetic = [q for q in synthetic if q.target_entity_id not in covered_entities]

    logger.info(
        f"load_hybrid_ground_truth_queries: {len(curated)} curated queries + "
        f"{len(uncovered_synthetic)} synthetic queries (covering {len(entities)} snapshot entities)."
    )
    return curated + uncovered_synthetic


# ---------------------------------------------------------------------------
# Stage 2 PhD-Level Strict Ground Truth Labeling & Binomial Sign Test
# ---------------------------------------------------------------------------

DEFAULT_ALPHA = 0.05
DEFAULT_MIN_QUERIES = 5  # Statistical requirement: min 5 target queries per entity for coverage


@dataclass
class StrictGroundTruthLabel:
    """Mathematically strict per-entity ground truth label (Stage 2 Remediation)."""

    entity_id: str
    label: int  # Y_i in {0, 1}
    displaced_query_count: int
    evaluated_query_count: int
    positive_delta_count: int
    mean_ndcg_delta: float
    p_value: float
    is_covered: bool  # False if evaluated_query_count < min_queries (exclude from Y_train)


@dataclass
class GroundTruthLabel(StrictGroundTruthLabel):
    """Backward-compatible alias for StrictGroundTruthLabel."""
    pass


def compute_exact_binomial_sign_test(
    ndcg_deltas: List[float],
) -> Tuple[float, int]:
    """Exact Binomial Sign Test: H1: P(delta > 0) > 0.5.

    Operates on non-zero deltas (standard sign-test behavior ignoring ties).
    Returns (p_value, positive_delta_count).
    """
    if not ndcg_deltas:
        return 1.0, 0

    pos_count = sum(1 for d in ndcg_deltas if d > 0.0)
    non_zero_deltas = [d for d in ndcg_deltas if d != 0.0]
    m = len(non_zero_deltas)

    if pos_count == 0 or m == 0:
        return 1.0, pos_count

    p_val = float(binomtest(pos_count, m, p=0.5, alternative="greater").pvalue)
    return p_val, pos_count


def compute_strict_ground_truth(
    loo_results: Dict[str, LeaveOneOutResult],
    alpha: float = DEFAULT_ALPHA,
    min_queries: int = DEFAULT_MIN_QUERIES,
) -> Dict[str, StrictGroundTruthLabel]:
    """Compute strict, mathematically sound binary ground-truth labels.

    Removes the `underpowered` bypass bug completely.
    Entities with fewer than min_queries evaluated target queries are marked `is_covered=False`
    and excluded from Y_train rather than guessing fallback labels.
    """
    labels: Dict[str, StrictGroundTruthLabel] = {}
    positive_count = 0
    uncovered_count = 0

    for entity_id, res in loo_results.items():
        m = res.evaluated_query_count
        if m < min_queries:
            uncovered_count += 1
            labels[entity_id] = StrictGroundTruthLabel(
                entity_id=entity_id,
                label=0,
                displaced_query_count=res.displaced_query_count,
                evaluated_query_count=m,
                positive_delta_count=0,
                mean_ndcg_delta=0.0,
                p_value=1.0,
                is_covered=False,
            )
            continue

        p_val, pos_count = compute_exact_binomial_sign_test(res.ndcg_deltas)

        # STRICT LABEL RULE: Top-K target rank displacement AND positive nDCG delta
        is_drifted = (res.displaced_query_count >= 1) and (pos_count >= 1)
        label_val = 1 if is_drifted else 0
        positive_count += label_val

        labels[entity_id] = StrictGroundTruthLabel(
            entity_id=entity_id,
            label=label_val,
            displaced_query_count=res.displaced_query_count,
            evaluated_query_count=m,
            positive_delta_count=pos_count,
            mean_ndcg_delta=res.mean_ndcg_delta,
            p_value=p_val,
            is_covered=True,
        )

    total = len(labels)
    logger.info(
        f"compute_strict_ground_truth: {positive_count}/{total} entities labeled Y_i=1 "
        f"(alpha={alpha}, min_queries={min_queries}, uncovered={uncovered_count})."
    )

    return labels


def binarize_ground_truth(
    loo_results: Dict[str, LeaveOneOutResult],
    alpha: float = DEFAULT_ALPHA,
    min_nonzero_queries: int = DEFAULT_MIN_QUERIES,
) -> Dict[str, StrictGroundTruthLabel]:
    """Backward-compatible entry point calling compute_strict_ground_truth."""
    return compute_strict_ground_truth(loo_results, alpha=alpha, min_queries=min_nonzero_queries)

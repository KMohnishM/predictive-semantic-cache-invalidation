"""Staleness cost of a selective re-embedding strategy, relative to a full re-index.

The absolute metrics (freshness / cache-preservation success rate) count whether
a query's target is in the strategy's top-k at all, so they are dominated by how
good the embedding model is at retrieval and come out nearly identical for every
strategy. What a cache-invalidation strategy controls is only the *difference*
from a full re-index over the same queries, so that is what is measured here:

    lost@k    reference (full re-index) has the target in the top-k, the strategy's
              index does not — staleness cost a correct answer.
    gained@k  the reverse. A stale vector beating a fresh one is not a benefit of
              the strategy (usually a query written against an older version of
              the code, or a stale competitor dropping out of the ranking), so it
              is reported separately and never credited.

Every rate is given for all queries and for the queries whose target's vector in
the strategy's index differs from the reference vector ("stale-target" queries),
the subset where staleness can act directly on the target.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import numpy as np

from .reporting import wilson_ci


def _at_k(baseline: np.ndarray, selective: np.ndarray, k: int) -> Dict[str, Any]:
    reference_hits = int(np.sum(baseline <= k))
    reference_misses = int(baseline.size - reference_hits)
    lost = int(np.sum((baseline <= k) & (selective > k)))
    gained = int(np.sum((baseline > k) & (selective <= k)))
    loss_rate = lost / reference_hits if reference_hits else 0.0
    return {
        "reference_hits": reference_hits,
        "lost": lost,
        "gained": gained,
        "loss_rate": loss_rate,
        "loss_rate_ci_95": list(wilson_ci(lost, reference_hits)),
        "gain_rate": gained / reference_misses if reference_misses else 0.0,
        "retention": 1.0 - loss_rate,
    }


def _block(baseline: np.ndarray, selective: np.ndarray, k_values: List[int]) -> Dict[str, Any]:
    n = int(baseline.size)
    if n == 0:
        return {"n_queries": 0, "at_k": {}, "rank_degraded_rate": 0.0,
                "rank_improved_rate": 0.0, "mean_reciprocal_rank_delta": 0.0}
    return {
        "n_queries": n,
        "at_k": {str(k): _at_k(baseline, selective, k) for k in k_values},
        "rank_degraded_rate": float(np.mean(selective > baseline)),
        "rank_improved_rate": float(np.mean(selective < baseline)),
        # Continuous: mean change in 1/rank (negative = strategy ranks targets lower)
        "mean_reciprocal_rank_delta": float(np.mean(1.0 / selective - 1.0 / baseline)),
    }


def compute_staleness_metrics(
    results: Iterable[Any],
    k_values: List[int],
    primary_k: int,
) -> Dict[str, Any]:
    """Staleness cost for one strategy's PerQueryResult rows (see module docstring)."""
    rows = list(results)
    baseline = np.array([r.baseline_rank for r in rows], dtype=float)
    selective = np.array([r.selective_rank for r in rows], dtype=float)
    stale = np.array([bool(getattr(r, "target_stale", False)) for r in rows], dtype=bool)
    k_values = sorted(set(k_values) | {primary_k})

    metrics = _block(baseline, selective, k_values)
    metrics["primary_k"] = primary_k
    metrics["stale_target"] = _block(baseline[stale], selective[stale], k_values)
    return metrics

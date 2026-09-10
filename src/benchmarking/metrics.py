"""Benchmark retrieval fidelity metrics.

These are thin re-exports of src/common/retrieval_metrics.py — moved there
so Pipeline A's ground-truth generator (src/embedder/, src/predictor/) can
share the exact same rank/recall/ndcg computation instead of reimplementing
it. Kept importable from here unchanged so existing `from .metrics import
...` call sites in this package don't need to change.
"""

from __future__ import annotations

from common.retrieval_metrics import (
    compute_rank,
    mean_reciprocal_rank,
    ndcg_at_k,
    rank_delta,
    rank_entities,
    recall_at_k,
    score_delta,
)

__all__ = [
    "compute_rank",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "rank_delta",
    "rank_entities",
    "recall_at_k",
    "score_delta",
]

"""Benchmark retrieval fidelity metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np


def recall_at_k(ranked_ids: List[str], target_id: str, k: int) -> float:
    return 1.0 if target_id in ranked_ids[:k] else 0.0


def mean_reciprocal_rank(ranked_ids: List[str], target_id: str) -> float:
    for index, entity_id in enumerate(ranked_ids, start=1):
        if entity_id == target_id:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: List[str], target_id: str, k: int) -> float:
    top_k = ranked_ids[:k]
    if target_id not in top_k:
        return 0.0
    rank = top_k.index(target_id) + 1
    return 1.0 / np.log2(rank + 1)


def rank_delta(baseline_rank: int, selective_rank: int) -> int:
    return selective_rank - baseline_rank


def score_delta(baseline_score: float, selective_score: float) -> float:
    return selective_score - baseline_score

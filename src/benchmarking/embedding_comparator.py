"""Direct embedding quality comparison module for benchmark runs."""

from __future__ import annotations

from typing import List, Optional, Set

import numpy as np

from .types import (
    EntityEmbeddingComparison,
    IndexSnapshot,
    StrategyEmbeddingComparisonResult,
)


def compare_index_snapshots(
    baseline_snapshot: IndexSnapshot,
    candidate_snapshot: IndexSnapshot,
    modified_files: Set[str],
    strategy_name: str,
    store_raw_vectors: bool = True,
    before_entity_ids: Optional[Set[str]] = None,
    updated_entity_ids: Optional[List[str]] = None,
) -> StrategyEmbeddingComparisonResult:
    """
    Compare baseline embeddings against candidate selective embeddings.

    Args:
        baseline_snapshot: Full re-index snapshot at Commit B.
        candidate_snapshot: Selective/candidate re-index snapshot at Commit B.
        modified_files: Set of file paths modified between Commit A and Commit B.
        strategy_name: Name of candidate strategy.
        store_raw_vectors: If True, include raw float vector payloads.
        before_entity_ids: Set of entity IDs present in Commit A snapshot.
        updated_entity_ids: List of entity IDs refreshed by candidate strategy.

    Returns:
        StrategyEmbeddingComparisonResult object containing per-entity & aggregate metrics.
    """
    comparisons: List[EntityEmbeddingComparison] = []
    similarities: List[float] = []

    total_entities = len(baseline_snapshot.entity_embeddings)
    updated_set = set(updated_entity_ids) if updated_entity_ids is not None else set()

    for entity_id, base_raw in baseline_snapshot.entity_embeddings.items():
        base_vec = np.asarray(base_raw, dtype=float)
        cand_raw = candidate_snapshot.entity_embeddings.get(entity_id)

        if cand_raw is not None:
            cand_vec = np.asarray(cand_raw, dtype=float)
            norm_b = np.linalg.norm(base_vec)
            norm_c = np.linalg.norm(cand_vec)
            if norm_b > 0 and norm_c > 0:
                similarity = float(np.dot(base_vec, cand_vec) / (norm_b * norm_c))
            else:
                similarity = 0.0
        else:
            similarity = 0.0

        # Clamp similarity to [-1.0, 1.0] range to prevent precision overflow
        similarity = max(-1.0, min(1.0, similarity))
        drift = float(1.0 - similarity)
        similarities.append(similarity)

        metadata = baseline_snapshot.entity_metadata.get(entity_id, {})
        file_path = str(metadata.get("file_path", ""))
        entity_type = str(metadata.get("entity_type", "unknown"))

        if before_entity_ids is not None and entity_id not in before_entity_ids:
            status = "added"
        elif file_path in modified_files:
            status = "modified"
        else:
            status = "unchanged"

        comparisons.append(
            EntityEmbeddingComparison(
                entity_id=entity_id,
                entity_type=entity_type,
                file_path=file_path,
                status=status,
                cosine_similarity=similarity,
                semantic_drift=drift,
                baseline_raw_vector=base_vec.tolist() if store_raw_vectors else None,
                candidate_raw_vector=cand_vec.tolist() if (store_raw_vectors and cand_raw is not None) else None,
            )
        )

    if similarities:
        mean_sim = float(np.mean(similarities))
        min_sim = float(np.min(similarities))
        p95_sim = float(np.percentile(similarities, 95))
    else:
        mean_sim = 1.0
        min_sim = 1.0
        p95_sim = 1.0

    updated_fraction = (len(updated_set) / total_entities) if total_entities > 0 else 0.0

    return StrategyEmbeddingComparisonResult(
        strategy_name=strategy_name,
        total_entities=total_entities,
        mean_cosine_similarity=mean_sim,
        min_cosine_similarity=min_sim,
        p95_cosine_similarity=p95_sim,
        updated_fraction=updated_fraction,
        per_entity_comparisons=comparisons,
    )

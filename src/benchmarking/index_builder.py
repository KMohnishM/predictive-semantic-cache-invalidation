"""Build baseline and selective retrieval indices for benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

try:
    from embedder.embedding_manager import EmbeddingManager
except ImportError:
    try:
        from src.embedder.embedding_manager import EmbeddingManager
    except ImportError:
        from ..embedder.embedding_manager import EmbeddingManager

from .types import IndexSnapshot, RepositorySnapshot


@dataclass(frozen=True)
class RetrievalResult:
    """Dataclass storing ranked entity IDs and similarity scores for a query."""
    ranked_entity_ids: List[str]
    ranked_scores: List[float]


def build_index_snapshot(snapshot: RepositorySnapshot, embedding_manager: EmbeddingManager) -> IndexSnapshot:
    """Generate vector embeddings for all entities in a repository snapshot.

    Args:
        snapshot: RepositorySnapshot containing parsed entities.
        embedding_manager: EmbeddingManager instance.

    Returns:
        IndexSnapshot containing serialized float vector embeddings and metadata.
    """
    if not snapshot.entities:
        return IndexSnapshot(commit_hash=snapshot.commit_hash, entity_embeddings={}, entity_metadata={})

    entities_dict = {entity_id: entity.source_code for entity_id, entity in snapshot.entities.items()}
    raw_embeddings = embedding_manager.generate_embeddings_batch(entities_dict)

    entity_embeddings: Dict[str, List[float]] = {
        entity_id: vec.astype(float).tolist() for entity_id, vec in raw_embeddings.items()
    }

    entity_metadata: Dict[str, Dict[str, object]] = {
        entity_id: {
            "file_path": entity.file_path,
            "entity_type": entity.entity_type,
            "lineno": entity.lineno,
            "end_lineno": entity.end_lineno,
            "name": entity.name,
        }
        for entity_id, entity in snapshot.entities.items()
    }

    return IndexSnapshot(commit_hash=snapshot.commit_hash, entity_embeddings=entity_embeddings, entity_metadata=entity_metadata)



def build_selective_snapshot(
    after_snapshot: IndexSnapshot,
    before_snapshot: IndexSnapshot,
    updated_entity_ids: List[str],
) -> IndexSnapshot:
    """Build a selective index snapshot where only updated entity IDs take new embeddings.

    Args:
        after_snapshot: IndexSnapshot of the later commit.
        before_snapshot: IndexSnapshot of the earlier commit.
        updated_entity_ids: List of entity IDs selected for re-indexing.

    Returns:
        Selective IndexSnapshot combining updated and cached embeddings.
    """
    entity_embeddings: Dict[str, List[float]] = {}
    for entity_id, embedding in after_snapshot.entity_embeddings.items():
        if entity_id in updated_entity_ids or entity_id not in before_snapshot.entity_embeddings:
            entity_embeddings[entity_id] = embedding
        else:
            entity_embeddings[entity_id] = before_snapshot.entity_embeddings[entity_id]

    return IndexSnapshot(
        commit_hash=after_snapshot.commit_hash,
        entity_embeddings=entity_embeddings,
        entity_metadata=after_snapshot.entity_metadata,
    )


def retrieve_top_k(
    query_text: str,
    snapshot: IndexSnapshot,
    embedding_manager: EmbeddingManager,
    top_k: int,
    query_embedding: Optional[np.ndarray] = None,
) -> RetrievalResult:
    """Retrieve top-K similar entities for a given query against an index snapshot.

    Args:
        query_text: Natural language or docstring query string.
        snapshot: Target IndexSnapshot.
        embedding_manager: EmbeddingManager instance.
        top_k: Number of top results to retrieve.
        query_embedding: Precomputed query embedding vector or None.

    Returns:
        RetrievalResult containing ranked entity IDs and similarity scores.
    """
    if query_embedding is None:
        query_embedding = embedding_manager.generate_embedding(f"query::{query_text}", query_text)
    entity_embeddings = {entity_id: np.asarray(values, dtype=float) for entity_id, values in snapshot.entity_embeddings.items()}
    ranked = embedding_manager.find_similar_entities(query_embedding, entity_embeddings, top_k=top_k)
    ranked_entity_ids = [entity_id for entity_id, _ in ranked]
    ranked_scores = [float(score) for _, score in ranked]
    return RetrievalResult(ranked_entity_ids=ranked_entity_ids, ranked_scores=ranked_scores)


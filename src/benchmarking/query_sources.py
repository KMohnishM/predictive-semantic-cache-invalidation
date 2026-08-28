"""Query generation and curated query loading for benchmark evaluation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List, Optional

from .types import CommitPair, QueryCase, RepositorySnapshot


def _normalize_query(text: str) -> str:
    return " ".join(text.strip().split())


def build_synthetic_queries(
    snapshot: RepositorySnapshot,
    commit_pair: CommitPair,
    max_queries_per_entity: int = 2,
    modified_entity_ids: Optional[Set[str]] = None,
) -> List[QueryCase]:
    queries: List[QueryCase] = []
    entities = sorted(snapshot.entities.values(), key=lambda entity: entity.entity_id)

    for entity_index, entity in enumerate(entities):
        is_changed = False
        if modified_entity_ids is not None:
            is_changed = entity.entity_id in modified_entity_ids
        else:
            is_changed = (entity_index % 2 == 0)

        templates = [
            f"What does {entity.entity_id} do after the latest commit?",
            f"Where is {entity.entity_id} implemented in the updated version?",
        ]
        for template_index, template in enumerate(templates[:max_queries_per_entity]):
            query_id = f"{commit_pair.commit_after[:8]}::{entity.entity_id}::{template_index}"
            queries.append(
                QueryCase(
                    query_id=query_id,
                    query_text=_normalize_query(template),
                    query_source="synthetic",
                    category="changed_entity" if is_changed else "unchanged_entity",
                    target_entity_id=entity.entity_id,
                    target_entity_name=entity.entity_id.split("::")[-1],
                    expected_behavior="latest_snapshot" if is_changed else "cached_snapshot",
                    commit_after=commit_pair.commit_after,
                    file_path=entity.file_path,
                    entity_type=entity.entity_type,
                )
            )

    return queries


def load_curated_queries(path: str) -> List[QueryCase]:
    query_path = Path(path)
    if not query_path.exists():
        return []

    if query_path.suffix.lower() == ".json":
        with query_path.open("r", encoding="utf-8") as handle:
            rows = json.load(handle)
    else:
        with query_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

    queries: List[QueryCase] = []
    for row in rows:
        queries.append(
            QueryCase(
                query_id=row["query_id"],
                query_text=_normalize_query(row["query_text"]),
                query_source="curated",
                category=row.get("category", "curated"),
                target_entity_id=row["target_entity_id"],
                target_entity_name=row.get("target_entity_name", row["target_entity_id"]),
                expected_behavior=row.get("expected_behavior", "latest_snapshot"),
                commit_after=row.get("commit_after", ""),
                file_path=row.get("file_path", ""),
                entity_type=row.get("entity_type", "unknown"),
            )
        )

    return queries


def build_queries(
    snapshot: RepositorySnapshot,
    commit_pair: CommitPair,
    query_mode: str,
    curated_queries_path: Optional[str],
    max_queries_per_entity: int,
    modified_entity_ids: Optional[Set[str]] = None,
) -> List[QueryCase]:
    synthetic_queries = build_synthetic_queries(
        snapshot,
        commit_pair,
        max_queries_per_entity=max_queries_per_entity,
        modified_entity_ids=modified_entity_ids,
    )
    if query_mode == "synthetic":
        return synthetic_queries

    curated_queries = load_curated_queries(curated_queries_path) if curated_queries_path else []
    if query_mode == "curated":
        return curated_queries

    return synthetic_queries + curated_queries

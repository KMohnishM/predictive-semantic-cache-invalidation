"""Query generation and curated query loading for benchmark evaluation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List, Optional, Set

from .types import CommitPair, QueryCase, RepositorySnapshot


def _normalize_query(text: str) -> str:
    return " ".join(text.strip().split())


def _extract_docstring_summary(source_code: str) -> Optional[str]:
    import re
    match = re.search(r'"""(.*?)"""', source_code, re.DOTALL)
    if not match:
        match = re.search(r"'''(.*?)'''", source_code, re.DOTALL)
    if match:
        doc = match.group(1).strip()
        first_line = doc.split('\n')[0].strip()
        if len(first_line) > 5:
            return first_line
    return None


def build_synthetic_queries(
    snapshot: RepositorySnapshot,
    commit_pair: CommitPair,
    max_queries_per_entity: int = 2,
    modified_entity_ids: Optional[Set[str]] = None,
    repo_graph=None,  # Phase 1.1: optional nx.DiGraph for caller-perspective queries
) -> List[QueryCase]:
    """
    Generate evaluation queries from the repository snapshot.

    Phase 1.1 fix: Query text MUST NOT contain the target entity name, class name,
    or file name (Cranfield/TREC paradigm).

    - For entities with a docstring: use the docstring summary as query text.
    - For entities without a docstring: generate a caller-perspective query using
      the dependency graph (predecessors of the entity).
    - If neither is available: skip the entity entirely.

    Rationale: Queries that embed the target's own identity make retrieval trivially
    solvable regardless of embedding freshness, saturating the benchmark at Recall@10
    ~= 1.0 for every strategy. This is the root cause documented in
    latest_runs_analysis.md §3.

    Literature:
        Cleverdon (Cranfield paradigm, 1960s); Voorhees (TREC, 1991) — queries must
        be independently authored and decoupled from target document identity.
        Thakur et al., BEIR (NeurIPS 2021) — in-distribution self-generated evaluation
        consistently overstates real retrieval quality.
    """
    queries: List[QueryCase] = []
    entities = sorted(snapshot.entities.values(), key=lambda e: e.entity_id)

    for entity_index, entity in enumerate(entities):
        is_changed = (
            entity.entity_id in modified_entity_ids
            if modified_entity_ids is not None
            else entity_index % 2 == 0
        )

        doc_summary = _extract_docstring_summary(entity.source_code)
        templates = []

        if doc_summary:
            # Safe: uses the docstring's own description — no entity name in query
            templates.append(doc_summary)
            templates.append(f"Which function is described as: {doc_summary}?")
        else:
            # No docstring: attempt a caller-perspective query via the call graph
            if repo_graph is not None:
                try:
                    callers = list(repo_graph.predecessors(entity.entity_id))
                    if callers:
                        # Use only the short method/function name of the first caller
                        caller_short = callers[0].split("::")[-1]
                        templates.append(
                            f"What does {caller_short} rely on for its core operation?"
                        )
                except Exception:
                    pass

            # If still no templates (no graph, no callers, no docstring):
            # Skip this entity entirely — an honest absence of queries beats
            # a name-leaking saturating query.
            if not templates:
                continue

        # Deduplicate templates
        seen: Set[str] = set()
        unique_templates = []
        for t in templates:
            t_norm = _normalize_query(t)
            if t_norm not in seen:
                seen.add(t_norm)
                unique_templates.append(t)

        for template_index, template in enumerate(unique_templates[:max_queries_per_entity]):
            query_id = f"{commit_pair.commit_after[:8]}::{entity.entity_id}::{template_index}"
            queries.append(
                QueryCase(
                    query_id=query_id,
                    query_text=_normalize_query(template),
                    query_source="synthetic",
                    category="changed_entity" if is_changed else "unchanged_entity",
                    target_entity_id=entity.entity_id,
                    target_entity_name=entity.name,
                    expected_behavior="latest_snapshot" if is_changed else "cached_snapshot",
                    commit_after=commit_pair.commit_after,
                    file_path=entity.file_path,
                    entity_type=entity.entity_type,
                )
            )

    return queries


def load_curated_queries(path: str) -> List[QueryCase]:
    """Load hand-authored curated queries from JSON or CSV.

    Curated queries follow the Cranfield/TREC paradigm: independently authored,
    no target entity name in query text. See src/benchmarking/data/curated_queries.json.
    """
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
    repo_graph=None,  # Phase 1.2: call graph passed from runner for caller-perspective queries
) -> List[QueryCase]:
    """Build the query set for a commit pair.

    query_mode values:
        "synthetic" — only auto-generated queries (no entity-name leakage after Phase 1.1 fix)
        "curated"   — only hand-authored queries from curated_queries_path
        "hybrid"    — curated queries first, synthetic queries as supplement (default after 1.3)
    """
    synthetic_queries = build_synthetic_queries(
        snapshot,
        commit_pair,
        max_queries_per_entity=max_queries_per_entity,
        modified_entity_ids=modified_entity_ids,
        repo_graph=repo_graph,
    )

    if query_mode == "synthetic":
        return synthetic_queries

    curated_queries = load_curated_queries(curated_queries_path) if curated_queries_path else []

    if query_mode == "curated":
        return curated_queries

    # hybrid: curated first (better quality), then synthetic as supplement
    return curated_queries + synthetic_queries

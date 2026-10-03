"""Build benchmark dataset records from commit pairs and query cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .types import CommitPair, QueryCase


@dataclass(frozen=True)
class BenchmarkDatasetRow:
    """Benchmark dataset record pairing a commit transition with a test query case."""
    commit_before: str
    commit_after: str
    query: QueryCase


def build_dataset(commit_pair: CommitPair, queries: List[QueryCase]) -> List[BenchmarkDatasetRow]:
    """Construct dataset rows by pairing a commit transition with query cases.

    Args:
        commit_pair: Commit transition pair.
        queries: List of query cases.

    Returns:
        List of BenchmarkDatasetRow instances.
    """
    return [BenchmarkDatasetRow(commit_pair.commit_before, commit_pair.commit_after, query) for query in queries]

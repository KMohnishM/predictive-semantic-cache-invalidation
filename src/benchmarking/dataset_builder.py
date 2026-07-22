"""Build benchmark dataset records from commit pairs and query cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from benchmarking.types import CommitPair, QueryCase


@dataclass(frozen=True)
class BenchmarkDatasetRow:
    commit_before: str
    commit_after: str
    query: QueryCase


def build_dataset(commit_pair: CommitPair, queries: List[QueryCase]) -> List[BenchmarkDatasetRow]:
    return [BenchmarkDatasetRow(commit_pair.commit_before, commit_pair.commit_after, query) for query in queries]

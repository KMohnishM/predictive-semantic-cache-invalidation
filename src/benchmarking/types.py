"""Shared benchmark types and result schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RepositoryEntity:
    entity_id: str
    entity_type: str
    file_path: str
    lineno: int
    end_lineno: int
    name: str
    source_code: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepositorySnapshot:
    commit_hash: str
    entities: Dict[str, RepositoryEntity]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_hash": self.commit_hash,
            "entities": {entity_id: entity.to_dict() for entity_id, entity in self.entities.items()},
        }


@dataclass(frozen=True)
class EntityEmbeddingComparison:
    entity_id: str
    entity_type: str
    file_path: str
    status: str
    cosine_similarity: float
    semantic_drift: float
    baseline_raw_vector: Optional[List[float]] = None
    candidate_raw_vector: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyEmbeddingComparisonResult:
    strategy_name: str
    total_entities: int
    mean_cosine_similarity: float
    min_cosine_similarity: float
    p95_cosine_similarity: float
    updated_fraction: float
    per_entity_comparisons: List[EntityEmbeddingComparison]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_entities": self.total_entities,
            "mean_cosine_similarity": self.mean_cosine_similarity,
            "min_cosine_similarity": self.min_cosine_similarity,
            "p95_cosine_similarity": self.p95_cosine_similarity,
            "updated_fraction": self.updated_fraction,
            "per_entity_comparisons": [item.to_dict() for item in self.per_entity_comparisons],
        }


@dataclass(frozen=True)
class BenchmarkConfig:
    repo_url: str
    repo_path: str
    output_dir: str
    benchmark_version: str = "1.0"
    seed: int = 13
    num_commits: int = 10
    commit_stride: int = 1
    sampling_mode: str = "adjacent"
    query_mode: str = "synthetic"
    curated_queries_path: Optional[str] = None
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    clean_mode: bool = False
    top_k_values: List[int] = field(default_factory=lambda: [1, 5, 10])
    output_format: str = "jsonl"
    max_queries_per_entity: int = 2
    strategies: List[str] = field(default_factory=lambda: ["changed_only"])
    compare_embeddings: bool = True
    store_raw_vectors: bool = True
    parser_mode: str = "ast"
    predictions_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommitPair:
    commit_before: str
    commit_after: str
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueryCase:
    query_id: str
    query_text: str
    query_source: str
    category: str
    target_entity_id: str
    target_entity_name: str
    expected_behavior: str
    commit_after: str
    file_path: str
    entity_type: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IndexSnapshot:
    commit_hash: str
    entity_embeddings: Dict[str, List[float]]
    entity_metadata: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyDecision:
    strategy_name: str
    updated_entity_ids: List[str]
    updated_fraction: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PerQueryResult:
    run_id: str
    commit_before: str
    commit_after: str
    query_id: str
    query_text: str
    query_source: str
    category: str
    target_entity_id: str
    target_entity_name: str
    expected_behavior: str
    baseline_rank: int
    selective_rank: int
    baseline_score: float
    selective_score: float
    top_k_hit_baseline: bool
    top_k_hit_selective: bool
    freshness_pass: bool
    cache_preservation_pass: bool
    rank_delta: int
    score_delta: float
    updated_entity_fraction: float
    strategy_name: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkSummary:
    run_id: str
    total_queries: int
    changed_query_count: int
    unchanged_query_count: int
    baseline_metrics: Dict[str, float]
    selective_metrics: Dict[str, float]
    metric_deltas: Dict[str, float]
    freshness_success_rate: float
    cache_preservation_success_rate: float
    candidate_update_fraction: float
    benchmark_passed: bool
    embedding_comparison_summaries: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_output_dir(base_dir: str, run_id: str) -> Path:
    return Path(base_dir).resolve() / run_id



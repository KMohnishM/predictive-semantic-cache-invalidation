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
    # Phase 1.2: call graph and parser stored on snapshot for use by strategy_runner
    graph: Optional[Any] = None    # nx.DiGraph — call graph at this commit
    parser: Optional[Any] = None   # repo parser — used by fixed_hop propagation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_hash": self.commit_hash,
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            # graph and parser are not serialised (they are live objects)
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
    decision_latency_seconds: float = 0.0
    total_e2e_time_seconds: float = 0.0
    per_entity_comparisons: List[EntityEmbeddingComparison] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_entities": self.total_entities,
            "mean_cosine_similarity": self.mean_cosine_similarity,
            "min_cosine_similarity": self.min_cosine_similarity,
            "p95_cosine_similarity": self.p95_cosine_similarity,
            "updated_fraction": self.updated_fraction,
            "decision_latency_seconds": self.decision_latency_seconds,
            "total_e2e_time_seconds": self.total_e2e_time_seconds,
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
    # Phase 1.3: default changed from "synthetic" to "hybrid"
    query_mode: str = "hybrid"
    curated_queries_path: Optional[str] = "src/benchmarking/data/curated_queries.json"
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    clean_mode: bool = False
    top_k_values: List[int] = field(default_factory=lambda: [1, 5, 10])
    output_format: str = "jsonl"
    max_queries_per_entity: int = 2
    # Phase 2.4: predictive_ml and fixed_hop in default strategy list
    strategies: List[str] = field(
        default_factory=lambda: ["changed_only", "fixed_hop", "predictive_ml", "full_reindex"]
    )
    compare_embeddings: bool = True
    store_raw_vectors: bool = True
    parser_mode: str = "ast"
    predictions_path: Optional[str] = None
    # Phase 2.3: hop depth for fixed_hop strategy
    hop_k: int = 2
    # Phase 2.3: score threshold for predictive_ml continuous scores
    ml_threshold: float = 0.5
    # Phase 3.3: number of independent runs for mean +- CI aggregation
    n_seeds: int = 1

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # graph/parser fields are not in BenchmarkConfig, nothing extra to strip
        return d


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
    decision_latency_seconds: float = 0.0

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
    # Phase 3.1: benchmark_passed removed — replaced by Wilson CI columns in reporting
    # Phase 1.4: saturation_warning flag added
    saturation_warning: bool = False
    embedding_comparison_summaries: Optional[List[Dict[str, Any]]] = None
    strategy_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_output_dir(base_dir: str, run_id: str) -> Path:
    return Path(base_dir).resolve() / run_id

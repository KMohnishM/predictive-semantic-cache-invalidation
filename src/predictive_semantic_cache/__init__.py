"""Predictive Semantic Cache Invalidation for LLM/RAG Indexing.

Predictive Semantic Cache Invalidation tracks semantic code drift across Git commits
using AST & call-graph feature extraction and machine learning, selectively re-embedding
only drifted entities while preserving fresh cache entries.
"""

__version__ = "0.1.0"

from .parser.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
from .extractor.feature_extractor import FeatureExtractor
from .predictor.predictor import DriftPredictor, positive_class_proba
from .integrations.llama_index import (
    CodeGraphNodeParser,
    PredictiveCacheFilter,
    build_predictive_ingestion_pipeline,
)

__all__ = [
    "__version__",
    "TreeSitterRepoParser",
    "Entity",
    "FeatureExtractor",
    "DriftPredictor",
    "positive_class_proba",
    "CodeGraphNodeParser",
    "PredictiveCacheFilter",
    "build_predictive_ingestion_pipeline",
]

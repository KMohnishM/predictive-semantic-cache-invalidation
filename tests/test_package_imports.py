"""Tests for package importability and metadata."""

import pytest


def test_package_metadata():
    import predictive_semantic_cache as psc
    assert hasattr(psc, "__version__")
    assert psc.__version__ == "0.1.0"


def test_top_level_exports():
    import predictive_semantic_cache as psc
    assert hasattr(psc, "TreeSitterRepoParser")
    assert hasattr(psc, "Entity")
    assert hasattr(psc, "FeatureExtractor")
    assert hasattr(psc, "DriftPredictor")
    assert hasattr(psc, "positive_class_proba")
    assert hasattr(psc, "CodeGraphNodeParser")
    assert hasattr(psc, "PredictiveCacheFilter")
    assert hasattr(psc, "build_predictive_ingestion_pipeline")


def test_submodule_imports():
    from predictive_semantic_cache.parser.tree_sitter_repo_parser import TreeSitterRepoParser
    from predictive_semantic_cache.extractor.feature_extractor import FeatureExtractor
    from predictive_semantic_cache.predictor.predictor import DriftPredictor
    from predictive_semantic_cache.integrations.llama_index import (
        CodeGraphNodeParser,
        PredictiveCacheFilter,
        build_predictive_ingestion_pipeline,
    )
    from predictive_semantic_cache.benchmarking.runner import main
    from predictive_semantic_cache.common.retrieval_metrics import rank_entities

    assert TreeSitterRepoParser is not None
    assert FeatureExtractor is not None
    assert DriftPredictor is not None
    assert CodeGraphNodeParser is not None
    assert PredictiveCacheFilter is not None
    assert main is not None
    assert rank_entities is not None

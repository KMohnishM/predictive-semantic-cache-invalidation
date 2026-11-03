"""Unit tests for the PredictiveCache client facade."""

from pathlib import Path
import pytest
from predictive_semantic_cache import PredictiveCache, DEFAULT_MODEL_PATH
from predictive_semantic_cache.predictor import DriftPredictor


def test_default_model_artifact_exists():
    assert DEFAULT_MODEL_PATH.exists(), f"Default model not found at {DEFAULT_MODEL_PATH}"
    assert DEFAULT_MODEL_PATH.stat().st_size > 1000, "Default model artifact appears truncated"


def test_client_init_default():
    cache = PredictiveCache(repo_path=".")
    assert cache.strategy == "predictive_ml"
    assert cache.predictor is not None
    assert isinstance(cache.predictor, DriftPredictor)
    assert cache.predictor.is_trained is True


def test_client_init_heuristics():
    cache_changed = PredictiveCache(repo_path=".", strategy="changed_only")
    assert cache_changed.strategy == "changed_only"
    assert cache_changed.predictor is None

    cache_fixed = PredictiveCache(repo_path=".", strategy="fixed_hop", hop_k=2)
    assert cache_fixed.strategy == "fixed_hop"
    assert cache_fixed.hop_k == 2


def test_client_custom_model_invalid_path():
    with pytest.raises(FileNotFoundError):
        PredictiveCache(repo_path=".", model_path="non_existent_model_12345.pkl")


def test_client_summary_structure():
    cache = PredictiveCache(repo_path=".")
    summary = cache.get_stale_summary("HEAD~1", "HEAD")
    assert "from_commit" in summary
    assert "to_commit" in summary
    assert "total_entities" in summary
    assert "stale_count" in summary
    assert "reembed_ratio" in summary
    assert "stale_entity_ids" in summary
    assert isinstance(summary["stale_entity_ids"], list)

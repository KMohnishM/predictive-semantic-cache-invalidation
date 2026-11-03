"""Unit tests for the PredictiveCache client facade."""

import subprocess
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


def test_client_summary_structure(tmp_path):
    # Create isolated 2-commit git repository in tmp_path
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True, capture_output=True)

    py_file = repo_dir / "module.py"
    py_file.write_text("def greet():\n    return 'hello'\n", encoding="utf-8")
    subprocess.run(["git", "add", "module.py"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True, capture_output=True)

    c1 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    py_file.write_text("def greet():\n    return 'world'\n", encoding="utf-8")
    subprocess.run(["git", "add", "module.py"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "second commit"], cwd=repo_dir, check=True, capture_output=True)

    c2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    cache = PredictiveCache(repo_path=repo_dir)
    summary = cache.get_stale_summary(c1, c2)
    assert summary["from_commit"] == c1
    assert summary["to_commit"] == c2
    assert summary["total_entities"] >= 1
    assert summary["stale_count"] >= 1
    assert summary["reembed_ratio"] > 0.0
    assert "module.py::greet" in summary["stale_entity_ids"]

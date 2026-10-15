"""Tests for llama_index_integration module."""

import os
import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

# Add repo root and src/ to path
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / "src"))

from llama_index_integration import (
    CodeGraphNodeParser,
    PredictiveCacheFilter,
    build_predictive_ingestion_pipeline,
    TextNode
)
from parser.tree_sitter_repo_parser import TreeSitterRepoParser
from predictor.predictor import DriftPredictor


def test_code_graph_node_parser(tmp_path):
    """Test that CodeGraphNodeParser parses python files into call-graph TextNodes."""
    # Create sample Python files with caller/callee relationships
    code_file = tmp_path / "module_a.py"
    code_file.write_text(
        "def callee():\n"
        "    return 42\n\n"
        "def caller():\n"
        "    return callee() + 1\n",
        encoding="utf-8"
    )

    parser = CodeGraphNodeParser(repo_path=str(tmp_path))
    nodes = parser.parse_repository()

    assert len(nodes) >= 2
    entity_ids = {n.id_ for n in nodes}
    assert any("callee" in eid for eid in entity_ids)
    assert any("caller" in eid for eid in entity_ids)

    # Check caller node metadata
    caller_node = next(n for n in nodes if "caller" in n.id_)
    assert "callees" in caller_node.metadata
    assert "callers" in caller_node.metadata
    assert caller_node.metadata["file_path"].endswith("module_a.py")
    assert caller_node.text.strip().startswith("def caller")


def test_predictive_cache_filter(tmp_path):
    """Test that PredictiveCacheFilter filters nodes based on direct modifications and predicted drift."""
    code_file = tmp_path / "service.py"
    code_file.write_text(
        "def helper():\n"
        "    return 1\n\n"
        "def main_func():\n"
        "    return helper()\n",
        encoding="utf-8"
    )

    node_parser = CodeGraphNodeParser(repo_path=str(tmp_path))
    nodes = node_parser.parse_repository()

    # Create and fit a mock DriftPredictor
    predictor = DriftPredictor(model_type="random_forest", task_type="classification")
    feature_names = [
        "out_degree", "in_degree", "pagerank", "closeness", "betweenness",
        "is_modified", "distance_to_modified_directed", "distance_to_modified_undirected",
        "modified_dependents_count", "modified_dependencies_count", "pagerank_impact",
        "file_lines_added", "file_lines_deleted", "entity_size", "entity_modification_size",
        "modification_frequency", "previous_drift", "gtd_change_class",
        "gtd_local_edges_added", "gtd_local_edges_removed", "gtd_local_edge_churn",
        "cyclomatic_complexity", "ast_node_count", "max_nesting_depth",
        "data_flow_distance", "modified_data_deps_count", "taint_reachability_score",
        "context_stub_changed_count", "modified_member_count", "own_source_changed"
    ]
    predictor.feature_names = feature_names

    # Mock trained state
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier

    X_mock = np.zeros((4, len(feature_names)))
    y_mock = np.array([0, 0, 1, 1])
    predictor.scaler = StandardScaler().fit(X_mock)
    predictor.model = RandomForestClassifier(n_estimators=10, random_state=42).fit(
        predictor.scaler.transform(X_mock), y_mock
    )
    predictor.is_trained = True
    predictor.decision_threshold = 0.5

    helper_node = next(n for n in nodes if "helper" in n.id_)
    main_node = next(n for n in nodes if "main_func" in n.id_)

    # Case 1: helper is modified -> should be included in dirty_nodes
    cache_filter = PredictiveCacheFilter(
        predictor_or_path=predictor,
        repo_parser=node_parser.repo_parser,
        modified_entities={helper_node.id_}
    )

    dirty = cache_filter(nodes)
    dirty_ids = [n.id_ for n in dirty]
    assert helper_node.id_ in dirty_ids

    # Case 2: update modified entities dynamically
    cache_filter.set_modified_entities({main_node.id_})
    dirty_updated = cache_filter(nodes)
    dirty_updated_ids = [n.id_ for n in dirty_updated]
    assert main_node.id_ in dirty_updated_ids


def test_build_predictive_ingestion_pipeline(tmp_path):
    """Test the convenience pipeline builder."""
    code_file = tmp_path / "app.py"
    code_file.write_text("def ping():\n    return 'pong'\n", encoding="utf-8")

    predictor = DriftPredictor(model_type="random_forest", task_type="classification")
    predictor.feature_names = ["out_degree", "is_modified"]
    from sklearn.preprocessing import StandardScaler
    from sklearn.dummy import DummyClassifier
    predictor.scaler = StandardScaler().fit([[0, 0], [1, 1]])
    predictor.model = DummyClassifier(strategy="constant", constant=0).fit([[0, 0], [1, 1]], [0, 0])
    predictor.is_trained = True

    pipeline = build_predictive_ingestion_pipeline(
        repo_path=str(tmp_path),
        predictor_or_path=predictor,
        modified_entities={"app.py::ping"}
    )

    assert "node_parser" in pipeline
    assert "cache_filter" in pipeline
    nodes = pipeline["node_parser"].parse_repository()
    assert len(nodes) == 1
    dirty = pipeline["cache_filter"](nodes)
    assert len(dirty) == 1


def test_filter_passes_previous_parser_to_feature_extractor(tmp_path, monkeypatch):
    """The earlier-commit parser must reach FeatureExtractor as parser_a, otherwise
    the call-graph-context features are always zero."""
    import llama_index_integration as li

    (tmp_path / "m.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    node_parser = CodeGraphNodeParser(repo_path=str(tmp_path))
    nodes = node_parser.parse_repository()

    seen = {}
    real = li.FeatureExtractor

    class Spy(real):
        def __init__(self, parser, *args, **kwargs):
            seen["parser_a"] = kwargs.get("parser_a")
            super().__init__(parser, *args, **kwargs)

    monkeypatch.setattr(li, "FeatureExtractor", Spy)

    predictor = DriftPredictor(model_type="random_forest", task_type="classification")
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier
    predictor.feature_names = ["out_degree", "in_degree"]
    X = np.zeros((4, 2)); y = np.array([0, 0, 1, 1])
    predictor.scaler = StandardScaler().fit(X)
    predictor.model = RandomForestClassifier(n_estimators=5, random_state=0).fit(predictor.scaler.transform(X), y)
    predictor.is_trained = True
    predictor.decision_threshold = 0.5

    prev = node_parser.repo_parser  # any parser object stands in for the earlier commit
    pipe = build_predictive_ingestion_pipeline(
        repo_path=str(tmp_path), predictor_or_path=predictor, previous_parser=prev
    )
    pipe["cache_filter"](nodes)
    assert seen["parser_a"] is prev

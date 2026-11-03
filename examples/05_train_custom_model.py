"""Example 5: Training a Custom DriftPredictor Model.

Demonstrates how an engineering team or researcher can train their own
predictive invalidation model tailored to their proprietary repository's
commit history, call-graph topologies, and coding conventions.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from predictive_semantic_cache import DriftPredictor, FeatureExtractor
from predictive_semantic_cache.parser import GitHelper, TreeSitterRepoParser


def train_custom_model():
    repo_path = Path(".").resolve()
    print(f"Training custom model for repository at: {repo_path}")

    # =========================================================================
    # Step 1: Initialize Git and Tree-Sitter Parser
    # =========================================================================
    git_helper = GitHelper(str(repo_path))
    parser = TreeSitterRepoParser(str(repo_path))
    parser.parse_directory(str(repo_path))
    print(f"Extracted {len(parser.entities)} entities and {parser.graph.number_of_edges()} call edges.")

    # =========================================================================
    # Step 2: Feature Extraction across historical commits
    # Collect Graph Transition Descriptors (GTD), Repository State Descriptors (RSD),
    # centrality shifts, complexity, and call-graph distances.
    # =========================================================================
    extractor = FeatureExtractor(parser)
    all_entity_ids = list(parser.entities.keys())

    # Example: Generating synthetic or empirical training features
    features_list = []
    labels = []

    for eid in all_entity_ids[:100]:  # Example slice
        feats = extractor.extract_features(eid, modified_entities=set())
        features_list.append(feats)
        # In a real training pipeline, labels are 1 (drifted) or 0 (fresh)
        # determined by embedding cosine similarity threshold (e.g. drift > 0.02)
        labels.append(1 if feats.get("distance_to_modified_directed", 999) <= 1 else 0)

    features_df = pd.DataFrame(features_list, index=all_entity_ids[:100])
    labels_series = pd.Series(labels, index=all_entity_ids[:100])

    print(f"Collected training matrix: {features_df.shape[0]} samples x {features_df.shape[1]} features")

    # =========================================================================
    # Step 3: Train the DriftPredictor Classifier
    # Supported models: 'random_forest', 'gradient_boosting', 'hist_gradient_boosting',
    #                   'lightgbm', 'extra_trees', 'logistic_regression', 'mlp'
    # =========================================================================
    predictor = DriftPredictor(
        model_type="hist_gradient_boosting",
        task_type="classification",
        target_recall=0.98,  # Prioritize catching stale entities (high recall)
    )

    X = features_df.values
    y = labels_series.values
    predictor.train(X, y, feature_names=list(features_df.columns))

    print(f"Model trained successfully! Calibrated decision threshold: {predictor.decision_threshold:.4f}")

    # =========================================================================
    # Step 4: Save the Custom Artifact
    # =========================================================================
    output_model_path = "models/custom_drift_predictor.pkl"
    Path(output_model_path).parent.mkdir(parents=True, exist_ok=True)
    predictor.save(output_model_path)
    print(f"Saved custom model artifact to: {output_model_path}")

    # =========================================================================
    # Step 5: Use the Custom Artifact with PredictiveCache
    # =========================================================================
    print("\nTo use this model in your pipeline or CI/CD:")
    print(">>> from predictive_semantic_cache import PredictiveCache")
    print(f">>> cache = PredictiveCache(repo_path='.', model_path='{output_model_path}')")
    print(">>> stale = cache.get_stale_entities('HEAD~1', 'HEAD')")


if __name__ == "__main__":
    train_custom_model()

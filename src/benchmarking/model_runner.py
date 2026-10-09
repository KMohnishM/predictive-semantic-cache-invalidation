"""Model runner for dynamic .pkl inference in Pipeline B."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def positive_class_proba(model: Any, probs: np.ndarray) -> np.ndarray:
    """Extract positive class probability safely."""
    if probs.shape[1] >= 2:
        return probs[:, 1]
    only_class = getattr(model, "classes_", [1])[0]
    fill_value = 1.0 if only_class == 1 else 0.0
    return np.full(probs.shape[0], fill_value)


class ModelRunner:
    """
    Loads a serialized DriftPredictor .pkl artifact and executes dynamic
    inference for stateful entity pairs (anchor_commit -> current_commit).
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model: Optional[Any] = None
        self.scaler: Optional[Any] = None
        self.feature_names: Optional[List[str]] = None
        self.task_type: str = "classification"
        self.model_type: str = "unknown"
        self.threshold: float = 0.5
        self.version: str = "1.0"
        self.is_loaded: bool = False

        if model_path:
            self.load(model_path)

    def load(self, model_path: str) -> None:
        """Load and validate the .pkl model bundle."""
        path = Path(model_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at: {path}")

        loaded_data = joblib.load(str(path))

        if isinstance(loaded_data, dict):
            self.model = loaded_data.get("model")
            self.scaler = loaded_data.get("scaler")
            self.feature_names = loaded_data.get("feature_names")
            self.task_type = loaded_data.get("task_type", "classification")
            self.model_type = loaded_data.get("model_type", "unknown")
            self.threshold = float(loaded_data.get("threshold", 0.5))
            self.version = str(loaded_data.get("version", "1.0"))
        elif hasattr(loaded_data, "model") and hasattr(loaded_data, "scaler"):
            self.model = getattr(loaded_data, "model")
            self.scaler = getattr(loaded_data, "scaler")
            self.feature_names = getattr(loaded_data, "feature_names", None)
            self.task_type = getattr(loaded_data, "task_type", "classification")
            self.model_type = getattr(loaded_data, "model_type", "unknown")
            self.threshold = float(getattr(loaded_data, "threshold", 0.5))
            self.version = "1.0"
        else:
            raise ValueError(f"Unrecognized model bundle structure in: {path}")

        if self.model is None or self.scaler is None:
            raise ValueError("Loaded artifact does not contain required 'model' and 'scaler'.")

        self.is_loaded = True
        logger.info(
            f"Successfully loaded model artifact '{self.model_type}' ({self.task_type}) "
            f"from {path.name} (version: {self.version}, features: {len(self.feature_names or [])})"
        )

    def predict_entities(
        self,
        entity_ids: List[str],
        anchor_commits: Dict[str, str],
        current_commit: str,
        git_helper: Any,
        repo_parser: Any,
        ml_threshold: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Dynamically extract features and predict drift scores for entities
        comparing each entity against its specific anchor commit.
        """
        if not self.is_loaded:
            raise RuntimeError("ModelRunner must load a model artifact before calling predict_entities.")

        if not entity_ids:
            return {}

        try:
            from src.extractor.feature_extractor import FeatureExtractor
        except ImportError:
            try:
                from extractor.feature_extractor import FeatureExtractor
            except ImportError:
                raise ImportError("Could not import FeatureExtractor from src.extractor.feature_extractor")

        # Group entities by their anchor commit to batch feature extraction
        anchor_groups: Dict[str, List[str]] = {}
        for eid in entity_ids:
            anchor = anchor_commits.get(eid, current_commit)
            anchor_groups.setdefault(anchor, []).append(eid)

        predicted_scores: Dict[str, float] = {}

        for anchor_commit, group_eids in anchor_groups.items():
            if not anchor_commit or anchor_commit == current_commit:
                # Same commit -> drift is zero
                for eid in group_eids:
                    predicted_scores[eid] = 0.0
                continue

            try:
                modified_files = set(git_helper.get_modified_files(anchor_commit, current_commit))
            except Exception as exc:
                logger.warning(f"Failed to get modified files between {anchor_commit[:8]} and {current_commit[:8]}: {exc}")
                modified_files = set()

            modified_entities = {
                eid for eid in group_eids
                if repo_parser.get_entity(eid) and repo_parser.get_entity(eid).file_path in modified_files
            }

            extractor = FeatureExtractor(
                repo_parser=repo_parser,
                git_helper=git_helper,
                commit_a=anchor_commit,
                commit_b=current_commit,
            )

            # Batch feature extraction for this anchor group
            df_features = extractor.extract_features_batch(
                entity_ids=group_eids,
                commit_a=anchor_commit,
                commit_b=current_commit,
                modified_entities=modified_entities,
                modification_history={},
                previous_drifts={},
                git_helper=git_helper,
            )

            if df_features.empty:
                for eid in group_eids:
                    predicted_scores[eid] = 0.0
                continue

            # Align columns to model's expected feature names
            if self.feature_names:
                missing_cols = set(self.feature_names) - set(df_features.columns)
                if missing_cols:
                    logger.warning(
                        f"Model expected {len(missing_cols)} feature columns missing from extracted features: {missing_cols}. Filling with 0.0."
                    )
                for col in self.feature_names:
                    if col not in df_features.columns:
                        df_features[col] = 0.0
                X_vals = df_features[self.feature_names].values
            else:
                X_vals = df_features.values

            # Scale and predict
            try:
                X_scaled = self.scaler.transform(X_vals)
                if self.task_type == "classification" and hasattr(self.model, "predict_proba"):
                    probs = self.model.predict_proba(X_scaled)
                    preds = positive_class_proba(self.model, probs)
                else:
                    preds = self.model.predict(X_scaled)

                for eid, score in zip(df_features.index, preds):
                    predicted_scores[str(eid)] = float(score)

            except Exception as pred_err:
                logger.error(f"Inference failed for anchor {anchor_commit[:8]} -> {current_commit[:8]}: {pred_err}")
                for eid in group_eids:
                    predicted_scores[eid] = 0.0

        return predicted_scores

    def evaluate_invalidation(
        self,
        scores: Dict[str, float],
        threshold: Optional[float] = None,
    ) -> List[str]:
        """Return list of entity IDs exceeding the threshold."""
        thresh = threshold if threshold is not None else self.threshold
        return [eid for eid, score in scores.items() if score >= thresh]

"""Drift predictor module for training ML models."""

from typing import Dict, List, Tuple, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
import logging
import joblib
import os

logger = logging.getLogger(__name__)


class DriftPredictor:
    """Trains models to predict semantic drift."""

    def __init__(self, model_type: str = "random_forest", task_type: str = "regression",
                 threshold: float = 0.02):
        """
        Initialize drift predictor.

        Args:
            model_type: Type of model ("random_forest", "gradient_boosting", "linear")
            task_type: "regression" or "classification"
            threshold: Threshold for classification (drift >= threshold -> 1)
        """
        self.model_type = model_type
        self.task_type = task_type
        self.threshold = threshold
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.is_trained = False

    def _create_model(self):
        """
        Create model based on type and task.

        Returns:
            Sklearn model instance
        """
        if self.task_type == "regression":
            if self.model_type == "random_forest":
                return RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1
                )
            elif self.model_type == "gradient_boosting":
                return GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42
                )
            elif self.model_type == "linear":
                return Ridge(alpha=1.0, random_state=42)
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")

        else:  # classification
            if self.model_type == "random_forest":
                return RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                    class_weight='balanced'
                )
            elif self.model_type == "gradient_boosting":
                return GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42
                )
            elif self.model_type == "linear":
                return LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                    class_weight='balanced'
                )
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")

    def prepare_data(self, features_df: pd.DataFrame, drifts: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features and labels for training.

        Args:
            features_df: DataFrame with features (index is entity_id)
            drifts: Dictionary mapping entity_id to drift value

        Returns:
            Tuple of (X, y) arrays
        """
        # Align features with drifts
        common_ids = set(features_df.index) & set(drifts.keys())
        if not common_ids:
            raise ValueError("No common entities between features and drifts")

        X = features_df.loc[list(common_ids)].values
        drift_values = [drifts[eid] for eid in common_ids]

        if self.task_type == "regression":
            y = np.array(drift_values)
        else:
            # Classification: binary label based on threshold
            y = np.array([1 if d >= self.threshold else 0 for d in drift_values])

        self.feature_names = features_df.columns.tolist()
        return X, y

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Train the model.

        Args:
            X: Feature matrix
            y: Target values

        Returns:
            Dictionary of training metrics
        """
        logger.info(f"Training {self.model_type} {self.task_type} model...")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Create and train model
        self.model = self._create_model()
        self.model.fit(X_scaled, y)

        self.is_trained = True

        # Training metrics
        metrics = {}

        if self.task_type == "regression":
            y_pred = self.model.predict(X_scaled)
            metrics['train_mse'] = mean_squared_error(y, y_pred)
            metrics['train_r2'] = r2_score(y, y_pred)
            logger.info(f"Training MSE: {metrics['train_mse']:.6f}")
            logger.info(f"Training R²: {metrics['train_r2']:.4f}")
        else:
            y_pred = self.model.predict(X_scaled)
            metrics['train_accuracy'] = self.model.score(X_scaled, y)
            metrics['train_f1'] = f1_score(y, y_pred, zero_division=0)
            metrics['train_precision'] = precision_score(y, y_pred, zero_division=0)
            metrics['train_recall'] = recall_score(y, y_pred, zero_division=0)
            logger.info(f"Training Accuracy: {metrics['train_accuracy']:.4f}")
            logger.info(f"Training F1: {metrics['train_f1']:.4f}")

        return metrics

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate the model on test data.

        Args:
            X: Feature matrix
            y: Target values

        Returns:
            Dictionary of evaluation metrics
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before evaluation")

        logger.info("Evaluating model on test data...")

        X_scaled = self.scaler.transform(X)
        metrics = {}

        if self.task_type == "regression":
            y_pred = self.model.predict(X_scaled)
            metrics['test_mse'] = mean_squared_error(y, y_pred)
            metrics['test_rmse'] = np.sqrt(metrics['test_mse'])
            metrics['test_r2'] = r2_score(y, y_pred)
            metrics['test_mae'] = np.mean(np.abs(y - y_pred))

            logger.info(f"Test MSE: {metrics['test_mse']:.6f}")
            logger.info(f"Test RMSE: {metrics['test_rmse']:.6f}")
            logger.info(f"Test R²: {metrics['test_r2']:.4f}")
            logger.info(f"Test MAE: {metrics['test_mae']:.6f}")

        else:
            y_pred = self.model.predict(X_scaled)
            y_prob = self.model.predict_proba(X_scaled)[:, 1] if hasattr(self.model, 'predict_proba') else None

            metrics['test_accuracy'] = self.model.score(X_scaled, y)
            metrics['test_f1'] = f1_score(y, y_pred, zero_division=0)
            metrics['test_precision'] = precision_score(y, y_pred, zero_division=0)
            metrics['test_recall'] = recall_score(y, y_pred, zero_division=0)

            logger.info(f"Test Accuracy: {metrics['test_accuracy']:.4f}")
            logger.info(f"Test F1: {metrics['test_f1']:.4f}")
            logger.info(f"Test Precision: {metrics['test_precision']:.4f}")
            logger.info(f"Test Recall: {metrics['test_recall']:.4f}")

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction")

        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> Optional[np.ndarray]:
        """
        Get prediction probabilities (classification only).

        Args:
            X: Feature matrix

        Returns:
            Probabilities or None
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction")

        if self.task_type != "classification":
            return None

        if not hasattr(self.model, 'predict_proba'):
            return None

        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance (if model supports it).

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before getting feature importance")

        if not hasattr(self.model, 'feature_importances_'):
            return None

        if self.feature_names is None:
            return None

        importance_dict = {}
        for name, importance in zip(self.feature_names, self.model.feature_importances_):
            importance_dict[name] = float(importance)

        # Sort by importance
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        return importance_dict

    def save(self, filepath: str) -> None:
        """
        Save model to file.

        Args:
            filepath: Path to save model
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before saving")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_type': self.model_type,
            'task_type': self.task_type,
            'threshold': self.threshold
        }

        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")

    def load(self, filepath: str) -> None:
        """
        Load model from file.

        Args:
            filepath: Path to load model from
        """
        model_data = joblib.load(filepath)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.model_type = model_data['model_type']
        self.task_type = model_data['task_type']
        self.threshold = model_data['threshold']
        self.is_trained = True

        logger.info(f"Model loaded from {filepath}")


def train_test_split_temporal(features_df: pd.DataFrame, drifts: Dict[str, float],
                              train_ratio: float = 0.7) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Split data based on entity IDs (simulating temporal split).

    In practice, this would be based on commit indices.
    For now, we use a random split but preserve the interface.

    Args:
        features_df: DataFrame with features
        drifts: Dictionary of drift values
        train_ratio: Ratio of data to use for training

    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    # Get common entities
    common_ids = list(set(features_df.index) & set(drifts.keys()))

    # Sort by entity_id for reproducibility (in practice, sort by commit time)
    common_ids.sort()

    # Split
    split_idx = int(len(common_ids) * train_ratio)
    train_ids = common_ids[:split_idx]
    test_ids = common_ids[split_idx:]

    X_train = features_df.loc[train_ids].values
    X_test = features_df.loc[test_ids].values
    y_train = np.array([drifts[eid] for eid in train_ids])
    y_test = np.array([drifts[eid] for eid in test_ids])

    logger.info(f"Train set: {len(train_ids)} entities")
    logger.info(f"Test set: {len(test_ids)} entities")

    return X_train, X_test, y_train, y_test
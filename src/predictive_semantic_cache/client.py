"""High-level client facade for predictive semantic cache invalidation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import pandas as pd

from .parser.git_helper import GitHelper
from .parser.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
from .extractor.feature_extractor import FeatureExtractor
from .extractor.semantic_modification import compute_source_changed_entities
from .predictor.predictor import DriftPredictor, positive_class_proba

logger = logging.getLogger(__name__)

# Built-in bundled default model path
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "default_drift_predictor.pkl"


class PredictiveCache:
    """High-level facade for predictive semantic cache invalidation across Git revisions.

    Provides a clean, unified API for detecting which code entities (functions, classes)
    experience semantic drift after Git commits and require vector re-indexing.

    Supports:
      1. Default ML (Zero-Config): Auto-loads the bundled pre-trained 50 KB model.
      2. Custom ML: Loads user-supplied .pkl artifact trained on custom commit history.
      3. Graph Heuristics: Deterministic call-graph traversal (changed_only, fixed_hop).

    Example:
        >>> from predictive_semantic_cache import PredictiveCache
        >>> # Default ML (Zero-config out of the box)
        >>> cache = PredictiveCache(repo_path=".")
        >>> stale = cache.get_stale_entities("HEAD~1", "HEAD")
        >>> print(f"Re-embed {len(stale)} entities")

        >>> # Custom model
        >>> cache = PredictiveCache(repo_path=".", model_path="models/custom.pkl")
        >>> stale = cache.get_stale_entities("HEAD~1", "HEAD")
    """

    def __init__(
        self,
        repo_path: Union[str, Path] = ".",
        model_path: Optional[Union[str, Path]] = None,
        strategy: str = "predictive_ml",
        hop_k: int = 1,
        threshold: Optional[float] = None,
    ) -> None:
        """Initialize PredictiveCache.

        Args:
            repo_path: Path to the target Git repository root.
            model_path: Path to custom trained DriftPredictor .pkl artifact.
                If None and strategy is 'predictive_ml', loads the default bundled model.
            strategy: Invalidation strategy: 'predictive_ml', 'changed_only', or 'fixed_hop'.
            hop_k: Maximum hops in the call graph for 'fixed_hop' strategy (default: 1).
            threshold: Probability threshold for marking an entity as stale. If None,
                uses the model's calibrated decision threshold.
        """
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {self.repo_path}")

        self.strategy = strategy.lower()
        self.hop_k = hop_k
        self.threshold = threshold
        self.git_helper = GitHelper(str(self.repo_path))

        # Model initialization
        self.predictor: Optional[DriftPredictor] = None
        self.model_path = model_path

        if self.strategy == "predictive_ml":
            self._init_predictor(model_path)

    def _init_predictor(self, model_path: Optional[Union[str, Path]]) -> None:
        """Load default or custom DriftPredictor artifact."""
        target_path: Path
        if model_path is not None:
            target_path = Path(model_path).resolve()
            if not target_path.exists():
                raise FileNotFoundError(f"Custom model artifact not found at: {target_path}")
            logger.info(f"Loading custom DriftPredictor from {target_path}")
        else:
            target_path = DEFAULT_MODEL_PATH
            if not target_path.exists():
                raise FileNotFoundError(
                    f"Default bundled model not found at {DEFAULT_MODEL_PATH}. "
                    "Ensure package was installed with package data."
                )
            logger.info(f"Loading default bundled DriftPredictor from {target_path}")

        self.predictor = DriftPredictor.load_artifact(str(target_path))
        self.model_path = target_path

    def get_stale_entities(
        self,
        from_commit: str,
        to_commit: str,
    ) -> List[Entity]:
        """Detect entities that experienced semantic drift between two commits.

        Args:
            from_commit: Base Git commit hash or ref (e.g. 'main~1', 'HEAD~1').
            to_commit: Target Git commit hash or ref (e.g. 'main', 'HEAD').

        Returns:
            List of Entity instances requiring re-embedding in the vector store.
        """
        stale_ids = self.get_stale_entity_ids(from_commit, to_commit)
        # Parse current state to get full Entity objects
        curr_parser = TreeSitterRepoParser(str(self.repo_path))
        curr_parser.parse_directory(str(self.repo_path))

        result: List[Entity] = []
        for eid in stale_ids:
            ent = curr_parser.get_entity(eid)
            if ent is not None:
                result.append(ent)
        return result

    def get_stale_entity_ids(
        self,
        from_commit: str,
        to_commit: str,
    ) -> List[str]:
        """Detect entity IDs that experienced semantic drift between two commits.

        Args:
            from_commit: Base Git commit hash or ref.
            to_commit: Target Git commit hash or ref.

        Returns:
            List of unique entity IDs (e.g. 'auth.py::verify_token') requiring re-indexing.
        """
        # 1. Get modified files from git diff
        modified_files = self.git_helper.get_modified_files(from_commit, to_commit)
        if not modified_files:
            logger.info("No files modified between commits. Zero entities stale.")
            return []

        # 2. Parse current directory state
        curr_parser = TreeSitterRepoParser(str(self.repo_path))
        curr_parser.parse_directory(str(self.repo_path))
        all_entity_ids = list(curr_parser.entities.keys())

        if not all_entity_ids:
            return []

        # 3. Compute directly changed entities
        # If we have previous commit in git, extract file contents at previous commit
        prev_parser = self._build_parser_at_commit(from_commit, modified_files)
        directly_changed = compute_source_changed_entities(
            parser_prev=prev_parser,
            parser_curr=curr_parser,
            modified_files=modified_files,
        )

        if self.strategy == "changed_only":
            return sorted(directly_changed)

        if self.strategy == "fixed_hop":
            expanded = set(directly_changed)
            for eid in directly_changed:
                try:
                    expanded.update(curr_parser.get_dependents(eid, max_hops=self.hop_k))
                except Exception as e:
                    logger.debug(f"Could not get dependents for {eid}: {e}")
            return sorted(expanded)

        # Strategy: predictive_ml
        if self.predictor is None:
            raise RuntimeError("Predictor model is not loaded for predictive_ml strategy.")

        # Candidates to evaluate: directly changed + dependents / callers up to 2 hops
        candidates = set(directly_changed)
        for eid in directly_changed:
            try:
                candidates.update(curr_parser.get_dependents(eid, max_hops=2))
            except Exception:
                pass

        if not candidates:
            # If no call-graph dependents found, evaluate all entities that share modified files
            for eid, ent in curr_parser.entities.items():
                if ent.file_path in modified_files:
                    candidates.add(eid)

        if not candidates:
            return sorted(directly_changed)

        extractor = FeatureExtractor(curr_parser, parser_a=prev_parser)
        features: Dict[str, Dict[str, float]] = {}
        candidate_list = list(candidates)

        for eid in candidate_list:
            feats = extractor.extract_features(eid, modified_entities=directly_changed)
            features[eid] = feats

        features_df = pd.DataFrame.from_dict(features, orient="index")

        # Align columns with model features
        if hasattr(self.predictor, "feature_names") and self.predictor.feature_names:
            features_df = features_df.reindex(columns=self.predictor.feature_names, fill_value=0.0)

        X = features_df.values

        # Predict drift probabilities
        if hasattr(self.predictor, "predict_proba"):
            raw_probs = self.predictor.predict_proba(X)
            if raw_probs is not None:
                probs = positive_class_proba(getattr(self.predictor, "model", None), raw_probs)
            else:
                probs = self.predictor.predict(X)
        else:
            probs = self.predictor.predict(X)

        effective_threshold = (
            self.threshold
            if self.threshold is not None
            else getattr(self.predictor, "decision_threshold", 0.5)
        )

        stale: Set[str] = set(directly_changed)
        for eid, prob in zip(candidate_list, probs):
            if prob >= effective_threshold:
                stale.add(eid)

        return sorted(stale)

    def get_stale_summary(
        self,
        from_commit: str,
        to_commit: str,
    ) -> Dict[str, Any]:
        """Return a structured summary of invalidation results.

        Returns a dictionary with total_entities, stale_entities_count,
        reembed_ratio, and the list of stale entity IDs.
        """
        curr_parser = TreeSitterRepoParser(str(self.repo_path))
        curr_parser.parse_directory(str(self.repo_path))
        total = len(curr_parser.entities)

        stale_ids = self.get_stale_entity_ids(from_commit, to_commit)
        stale_count = len(stale_ids)
        ratio = (stale_count / total) if total > 0 else 0.0

        return {
            "from_commit": from_commit,
            "to_commit": to_commit,
            "total_entities": total,
            "stale_count": stale_count,
            "reembed_ratio": ratio,
            "strategy": self.strategy,
            "model_path": str(self.model_path) if self.model_path else None,
            "stale_entity_ids": stale_ids,
        }

    def _build_parser_at_commit(
        self,
        commit_hash: str,
        modified_files: List[str],
    ) -> Optional[TreeSitterRepoParser]:
        """Construct a lightweight TreeSitterRepoParser for files at an earlier commit."""
        try:
            parser = TreeSitterRepoParser(str(self.repo_path))
            for fpath in modified_files:
                if not fpath.endswith(".py"):
                    continue
                content = self.git_helper.get_file_content_at_commit(commit_hash, fpath)
                if content is not None:
                    parser.parse_file_content(fpath, content)
            return parser
        except Exception as e:
            logger.debug(f"Could not build parser at commit {commit_hash}: {e}")
            return None

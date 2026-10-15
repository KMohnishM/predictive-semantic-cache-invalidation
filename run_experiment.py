#!/usr/bin/env python3
"""Main orchestration script for predictive semantic cache invalidation experiment."""


import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import time
import json
import hashlib
from datetime import datetime

import joblib

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parser.git_helper import GitHelper
from parser.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
from embedder.embedding_manager import EmbeddingManager
from embedder.ground_truth import (
    binarize_ground_truth,
    compute_leave_one_out_scores,
    load_ground_truth_queries,
    load_hybrid_ground_truth_queries,
)
from extractor.feature_extractor import FeatureExtractor
from extractor.semantic_modification import (  # noqa: F401
    compute_semantic_modified_entities,
    compute_source_changed_entities,
    normalize_source,
)
from embedder.context_builder import build_contextual_source, extract_signature
from predictor.predictor import DriftPredictor, train_test_split_temporal, positive_class_proba
from evaluator.evaluator import (Evaluator, BaselineAChangedOnly, BaselineBFullReindex,
                       BaselineCFixedHop, BaselineDPageRankPropagation,
                       PredictiveStrategy, WeightedBFSDecayStrategy)
from evaluator.reembed_coverage import reembed_coverage_row, save_reembed_coverage
from visualizer.visualize import Visualizer
from extractor.rsd import RepositoryStateDescriptor
from extractor.gtd import GraphTransitionDescriptor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('experiment.log')
    ]
)
logger = logging.getLogger(__name__)

# Label sources that produce a binary Y_i in ground_truth_history (vs. raw cosine
# drift in drifts_history).
BINARY_LABEL_SOURCES = ("leave_one_out", "hybrid", "embedded_text_changed")

# Bump when parsing, context text, features or labels change, so cached
# datasets built by older code are not reused.
DATASET_CACHE_VERSION = 1


class Experiment:
    """Main experiment orchestrator."""

    def __init__(self, repo_url: str = "https://github.com/psf/black.git",
                 workspace_dir: str = "workspace",
                 num_commits: int = 50,
                 train_ratio: float = 0.7,
                 threshold: float = 0.02,
                 threshold_mode: str = "dynamic",
                 clean_mode: bool = False,
                 context_chunking: bool = False,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 commit_stride: int = 20,
                 parser_mode: str = "ast",
                 device: str = "auto",
                 label_source: str = "cosine_threshold",
                 ground_truth_top_k: int = 10,
                 ground_truth_queries_path: Optional[str] = None,
                 compare_models: bool = False,
                 max_queries_per_entity: int = 5,
                 ref: str = "HEAD",
                 ground_truth_rule: str = "significant",
                 ground_truth_min_queries: int = 5,
                 target_recall: Optional[float] = None,
                 model_type: str = "random_forest",
                 compare_models_exclude: Optional[List[str]] = None,
                 dataset_dir: Optional[str] = "datasets",
                 rebuild_dataset: bool = False):
        """
        Initialize experiment.

        Args:
            repo_url: URL of repository to clone
            workspace_dir: Directory for workspace
            num_commits: Number of commits to analyze
            train_ratio: Ratio of commits to use for training
            threshold: Drift threshold for classification
            threshold_mode: Threshold mode ("fixed" or "dynamic")
            clean_mode: If True, remove comments/docstrings before embedding
            context_chunking: If True, enable call-graph aware contextual chunking
            model_name: HuggingFace model name for embeddings
            commit_stride: Step size between sampled commits
            parser_mode: Parser mode ("ast", "joern_hybrid", "joern_only")
            device: Embedding model device — "auto" (CUDA if available, else CPU),
                "cpu", "cuda", or a specific device string (e.g. "cuda:0")
            label_source: Training label source for the predictor —
                "cosine_threshold" (default, preserves existing behavior:
                raw cosine drift binarized by `threshold`/`threshold_mode`)
                or "leave_one_out" (Y_i from the leave-one-out rank-
                displacement + exact sign-test significance ground truth in
                src/embedder/ground_truth.py — see
                docs/ground_truth_method_comparison.md), or
                "embedded_text_changed" (Y_i = 1 when the entity's embedded
                text — source plus call-graph context — differs between the
                two commits, i.e. its vector would differ from a full
                re-index; the same notion of staleness the benchmark uses). All label
                sources use the exact same features and training loop, so
                a model can be trained on either and compared directly.
            ground_truth_top_k: Top-K window used by the leave_one_out
                label source (ignored for cosine_threshold).
            ground_truth_queries_path: Override path to the curated query
                set used by the leave_one_out label source. Defaults to
                src/benchmarking/data/curated_queries.json. Must be an
                independently-authored query set (see
                src/embedder/ground_truth.py module docstring) — never
                point this at anything derived from this experiment's own
                embedding model.
        """
        if label_source not in ("cosine_threshold",) + BINARY_LABEL_SOURCES:
            raise ValueError(
                f"Unknown label_source: {label_source!r}. Expected "
                f"'cosine_threshold', 'leave_one_out', 'hybrid', or 'embedded_text_changed'."
            )

        self.repo_url = repo_url
        self.workspace_dir = Path(workspace_dir)
        self.num_commits = num_commits
        self.train_ratio = train_ratio
        self.threshold = threshold
        self.threshold_mode = threshold_mode
        self.clean_mode = clean_mode
        self.context_chunking = context_chunking
        self.model_name = model_name
        self.commit_stride = commit_stride
        self.parser_mode = parser_mode
        self.device = device
        self.label_source = label_source
        self.ground_truth_top_k = ground_truth_top_k
        self.ground_truth_queries_path = ground_truth_queries_path
        self.compare_models = compare_models
        self.max_queries_per_entity = max_queries_per_entity
        # Label rule for leave_one_out/hybrid: "significant" (displacement + sign
        # test, needs >= 5 queries) or "any_displacement" (any target query fell
        # out of the top-K).
        self.ground_truth_rule = ground_truth_rule
        self.ground_truth_min_queries = ground_truth_min_queries
        # Recall the predictor's decision threshold must reach out-of-fold
        # (None = F1-optimal threshold).
        self.target_recall = target_recall
        self.model_type = model_type
        # Architectures left out of --compare-models (e.g. svc/knn on large data).
        self.compare_models_exclude = compare_models_exclude or []
        # Built datasets (per-pair features/labels plus the evaluation commits'
        # parsers and embeddings) are cached here and reused by later runs with
        # the same dataset settings, skipping the expensive parse/embed/feature
        # pass. None disables caching.
        self.dataset_dir = Path(dataset_dir) if dataset_dir else None
        self.rebuild_dataset = rebuild_dataset
        # Git ref the sampled commit window ends at (pinned so runs are reproducible
        # and independent of wherever HEAD was left).
        self.ref = ref
        self._original_head: Optional[str] = None
        # Set when this run checks out a commit; a run served entirely from the
        # dataset cache never touches the working tree (so it can run alongside
        # a benchmark on the same checkout) and must not restore it either.
        self._did_checkout = False
        self.joern_session = None

        # Lazily populated by _get_ground_truth_queries(). The curated query set
        # is fixed for the whole experiment, so it is loaded once. In hybrid mode
        # the synthetic supplement depends on which entities exist, so it is
        # rebuilt per snapshot; query embeddings are cached by text so each
        # distinct query is embedded only once.
        self._curated_queries = None
        self._query_text_embeddings: Dict[str, np.ndarray] = {}

        # Paths
        repo_name = Path(self.repo_url.rstrip("/\\")).name
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        self.repo_path = self.workspace_dir / repo_name
        
        # Determine unique results directory name based on configuration and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_str = "contextual" if self.context_chunking else "isolated"
        model_slug = model_name.split("/")[-1]
        dir_name = (
            f"results_{model_slug}_{mode_str}_commits{self.num_commits}"
            f"_stride{self.commit_stride}_clean{self.clean_mode}_{timestamp}"
        )
        self.results_dir = Path("results") / dir_name
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.commit_logs_dir = self.results_dir / "commit_logs"
        self.commit_logs_dir.mkdir(parents=True, exist_ok=True)

        # Components (initialized later)
        self.git_helper = None
        self.repo_parser = None
        self.embedding_manager = None
        self.feature_extractor = None
        self.predictor = None
        self.evaluator = None
        self.visualizer = None

        # Data storage
        self.commits = []
        self.sampled_commits = []
        self.train_commits = []
        self.test_commits = []
        self.embeddings_history = {}  # commit_hash -> embeddings dict
        self.drifts_history = {}  # (commit_a, commit_b) -> drifts dict
        self.ground_truth_history = {}  # (commit_a, commit_b) -> {entity_id: Y_i in {0.0, 1.0}}, binary label sources only
        self.sources_history = {}  # commit_hash -> {entity_id: embedded text}
        self.entity_counts = {}  # commit_hash -> number of embedded entities
        self.features_history = {}  # (commit_a, commit_b) -> features DataFrame
        self.modification_history = {}  # entity_id -> list of commit hashes
        self.previous_drifts = {}  # entity_id -> last drift value
        self.parsers_history = {}  # commit_hash -> TreeSitterRepoParser instance
        self.gtd_history = {}  # (commit_a, commit_b) -> GraphTransitionDescriptor
        self.modified_entities_history = {}  # (commit_a, commit_b) -> semantically modified entity ids

        # Repository State Descriptor — used for stratified train/test split
        self.rsd = RepositoryStateDescriptor()

    def setup(self) -> bool:
        """
        Setup experiment: clone repo and initialize components.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("SETTING UP EXPERIMENT")
        logger.info("=" * 80)

        # Clone repository
        logger.info(f"Cloning repository from {self.repo_url}...")
        self.git_helper = GitHelper(str(self.repo_path))
        if not self.git_helper.clone_repo(self.repo_url, str(self.repo_path)):
            logger.error("Failed to clone repository")
            return False

        # Initialize components
        logger.info("Initializing components...")

        # Initialize repository parser (Tree-sitter native)
        self.repo_parser = TreeSitterRepoParser(str(self.repo_path))
        logger.info("Initialized Tree-sitter RepoParser for repository parsing and graph construction")

        self.embedding_manager = EmbeddingManager(model_name=self.model_name, clean_mode=self.clean_mode,
                                                   device=self.device)
        self.feature_extractor = FeatureExtractor(self.repo_parser)
        self.predictor = DriftPredictor(model_type=self.model_type, task_type="classification",
                                        threshold=self.threshold, target_recall=self.target_recall)
        self.evaluator = Evaluator(self.embedding_manager, self.repo_parser)
        self.visualizer = Visualizer(str(self.results_dir))

        logger.info(f"Setup complete (parser_mode={self.parser_mode}, embedding_device={self.embedding_manager.device})")
        return True

    def harvest_commits(self) -> bool:
        """
        Harvest commit history.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("HARVESTING COMMITS")
        logger.info("=" * 80)

        raw_commit_count = self.num_commits * self.commit_stride
        self.commits = self.git_helper.get_commit_history(count=raw_commit_count, ref=self.ref)
        logger.info(f"Commit window ends at ref {self.ref!r}")

        if len(self.commits) < self.commit_stride + 1:
            logger.error(
                f"Not enough commits found for stride={self.commit_stride}: "
                f"{len(self.commits)} raw commits"
            )
            return False

        # ----------------------------------------------------------------
        # Stratified train/test split using RSD
        # (RSDs are built lazily after build_dataset populates rsd_history;
        #  a first-pass simple split is used here and refined post-dataset-build)
        # We store the split ratio and apply it after RSDs are computed.
        # ----------------------------------------------------------------
        split_idx = int(len(self.commits) * self.train_ratio)
        self.train_commits = self.commits[:split_idx]
        self.test_commits  = self.commits[split_idx:]

        logger.info(f"Total raw commits: {len(self.commits)}")
        logger.info(f"Training commits (preliminary): {len(self.train_commits)}")
        logger.info(f"Test commits (preliminary):     {len(self.test_commits)}")

        return True

    def _extract_signature(self, entity: Entity) -> str:
        """Extract the signature lines from an entity's source code."""
        return extract_signature(entity)

    def _get_contextual_source(self, entity: Entity) -> str:
        """
        Get call-graph aware contextual source code for an entity.
        Delegates to the shared builder also used by the benchmark index
        (src/embedder/context_builder.py) so both pipelines embed identical text.
        """
        if not self.context_chunking:
            return entity.source_code
        return build_contextual_source(
            entity, self.repo_parser, large_context=self.embedding_manager.is_large_context()
        )

    def process_commit(self, commit_hash: str) -> None:
        """
        Process a single commit: parse repo and generate embeddings.

        Args:
            commit_hash: Git commit hash
        """
        logger.info(f"Processing commit {commit_hash[:8]}...")

        # Checkout commit
        self._did_checkout = True
        if not self.git_helper.checkout_commit(commit_hash):
            logger.warning(f"Failed to checkout commit {commit_hash[:8]}, skipping...")
            return

        # Parse repository
        self.repo_parser = TreeSitterRepoParser(str(self.repo_path))
        self.repo_parser.parse_directory(str(self.repo_path))

        # Generate embeddings for all entities
        entities = self.repo_parser.get_all_entities()
        entity_sources = {e.entity_id: self._get_contextual_source(e) for e in entities}

        if entity_sources:
            embeddings = self.embedding_manager.generate_embeddings_batch(entity_sources)
            self.embeddings_history[commit_hash] = embeddings

            logger.info(f"  Parsed {len(entities)} entities, generated {len(embeddings)} embeddings")
        else:
            logger.warning(f"  No entities found in commit {commit_hash[:8]}")
            self.embeddings_history[commit_hash] = {}

    def _get_ground_truth_queries(self, repo_parser=None) -> Tuple[List, Dict[str, np.ndarray]]:
        """
        Return the ground-truth query set and its embeddings (query_id -> vector).

        Curated queries are loaded once. With label_source="hybrid" and a
        ``repo_parser``, synthetic queries are added for that snapshot's entities
        that have no curated query — built from the given snapshot, so entities
        added later in the commit window are covered too.
        """
        if self._curated_queries is None:
            self._curated_queries = load_ground_truth_queries(self.ground_truth_queries_path)
            logger.info(
                f"Loaded {len(self._curated_queries)} curated ground-truth queries "
                f"(label_source={self.label_source}, path={self.ground_truth_queries_path or 'default'})."
            )
            if not self._curated_queries and self.label_source != "hybrid":
                logger.warning(
                    "_get_ground_truth_queries: query set is empty — "
                    "leave_one_out label_source will produce no labels."
                )

        if self.label_source == "hybrid" and repo_parser is not None:
            queries = load_hybrid_ground_truth_queries(
                path=self.ground_truth_queries_path,
                repo_parser=repo_parser,
                max_queries_per_entity=self.max_queries_per_entity,
            )
        else:
            queries = self._curated_queries

        new_texts = {q.query_text for q in queries} - set(self._query_text_embeddings)
        for text in sorted(new_texts):
            self._query_text_embeddings[text] = self.embedding_manager.generate_embedding(
                f"gt_query::{text}", text
            )
        query_embeddings = {q.query_id: self._query_text_embeddings[q.query_text] for q in queries}
        return queries, query_embeddings

    def compute_ground_truth_labels(self, commit_a: str, commit_b: str) -> Dict[str, float]:
        """
        Compute the leave_one_out Y_i label for every entity common to
        commit_a/commit_b's embeddings, using the independent curated query
        set (never run_experiment.py's own drift/docstring-derived
        queries — see src/embedder/ground_truth.py's module docstring).

        Returns entity_id -> float in {0.0, 1.0}, in the same shape as
        drifts_history entries, so train_model() can swap label sources
        without touching feature extraction at all.
        """
        embeddings_a = self.embeddings_history.get(commit_a, {})
        embeddings_b = self.embeddings_history.get(commit_b, {})
        if not embeddings_a or not embeddings_b:
            return {}

        queries, query_embeddings = self._get_ground_truth_queries(self.parsers_history.get(commit_b))
        if not queries:
            return {}

        loo_results = compute_leave_one_out_scores(
            embeddings_before=embeddings_a,
            embeddings_after=embeddings_b,
            queries=queries,
            query_embeddings=query_embeddings,
            top_k=self.ground_truth_top_k,
        )
        gt_labels = binarize_ground_truth(
            loo_results,
            min_nonzero_queries=self.ground_truth_min_queries,
            rule=self.ground_truth_rule,
        )
        return {entity_id: float(label.label) for entity_id, label in gt_labels.items() if label.is_covered}

    def compute_text_changed_labels(self, commit_a: str, commit_b: str) -> Dict[str, float]:
        """
        Y_i = 1.0 when entity i's embedded text (source plus call-graph context,
        exactly what gets embedded) differs between commit_a and commit_b, else
        0.0 — i.e. whether its cached vector would differ from a full re-index.
        Only entities present at both commits are labeled, as for leave_one_out.
        """
        sources_a = self.sources_history.get(commit_a, {})
        sources_b = self.sources_history.get(commit_b, {})
        return {
            entity_id: float(sources_a[entity_id] != text)
            for entity_id, text in sources_b.items()
            if entity_id in sources_a
        }

    def compute_drifts_and_features(self, commit_a: str, commit_b: str) -> Tuple[Dict[str, float], pd.DataFrame]:
        """
        Compute drifts and features between two commits.

        Args:
            commit_a: Earlier commit hash
            commit_b: Later commit hash

        Returns:
            Tuple of (drifts dict, features DataFrame)
        """
        logger.info(f"Computing drifts and features between {commit_a[:8]} and {commit_b[:8]}...")

        # Get embeddings
        embeddings_a = self.embeddings_history.get(commit_a, {})
        embeddings_b = self.embeddings_history.get(commit_b, {})

        if not embeddings_a or not embeddings_b:
            logger.warning(f"Missing embeddings for commits {commit_a[:8]} or {commit_b[:8]}")
            return {}, pd.DataFrame()

        # Compute drifts
        drifts = self.embedding_manager.compute_all_drifts(embeddings_a, embeddings_b)

        # Get modified entities
        modified_files = self.git_helper.get_modified_files(commit_a, commit_b)
        logger.debug(f"Modified files: {modified_files[:5] if len(modified_files) > 5 else modified_files}")

        # Semantically modified entities (AST-normalized, cosmetic changes filtered).
        # Shared with the benchmark's ModelRunner so is_modified means the same
        # thing at train and inference time.
        file_level_count = sum(
            1 for e in self.repo_parser.get_all_entities() if e.file_path in set(modified_files)
        )
        modified_entities = compute_semantic_modified_entities(
            self.parsers_history.get(commit_a), self.repo_parser, modified_files
        )
        logger.info(f"Filtered cosmetic changes: {file_level_count} -> {len(modified_entities)}")
        self.modified_entities_history[(commit_a, commit_b)] = set(modified_entities)

        # Graph Transition Descriptor. "Modified" = code changed (known before
        # re-embedding), NOT embedding drift — drift-derived features would not be
        # available when the trained model is used to decide what to re-embed.
        gtd = GraphTransitionDescriptor()
        gtd.compute(parser_a=self.parsers_history.get(commit_a), parser_b=self.repo_parser,
                    modified_entities=modified_entities)
        self.gtd_history[(commit_a, commit_b)] = gtd

        # Extract features (only for entities in current graph)
        entity_ids = [eid for eid in drifts.keys() if eid in self.repo_parser.get_graph()]
        if not entity_ids:
            logger.warning("No entities found in current graph")
            return {}, pd.DataFrame()

        # Update feature extractor with current graph. git_helper/commits are
        # passed so the diff-stat features are populated, exactly as at inference.
        self.feature_extractor = FeatureExtractor(
            self.repo_parser, git_helper=self.git_helper, commit_a=commit_a, commit_b=commit_b,
            parser_a=self.parsers_history.get(commit_a),
            large_context=self.embedding_manager.is_large_context(),
        )

        features_df = self.feature_extractor.extract_features_batch(
            entity_ids, commit_a, commit_b, modified_entities,
            self.modification_history, self.previous_drifts, self.git_helper,
            gtd=gtd
        )

        # Update modification history
        for entity_id in modified_entities:
            self.feature_extractor.update_modification_history(
                entity_id, commit_b, self.modification_history
            )

        # Update previous drifts
        for entity_id, drift in drifts.items():
            self.previous_drifts[entity_id] = drift

        logger.info(f"  Computed drifts for {len(drifts)} entities")
        logger.info(f"  Modified entities: {len(modified_entities)}")

        return drifts, features_df

    def build_dataset(self) -> bool:
        """
        Build dataset by processing sampled commits and computing drifts/features.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("BUILDING DATASET")
        logger.info("=" * 80)

        # Sample commits at the configured stride and only process those commits.
        self.sampled_commits = self.commits[::self.commit_stride][:self.num_commits]
        if len(self.sampled_commits) < 2:
            logger.error(
                "Not enough sampled commits to build a dataset: "
                f"{len(self.sampled_commits)} sampled commits with stride={self.commit_stride}"
            )
            return False

        # Chronological split point. Only the commits of the evaluation pairs
        # (the last training commit onwards) need their parser and embeddings
        # after the dataset is built; the rest are released as the loop
        # advances, so memory is bounded by the test window, not every sample.
        split_idx = max(1, int(len(self.sampled_commits) * self.train_ratio))
        keep_for_eval = set(self.sampled_commits[split_idx - 1:])

        for i, commit in enumerate(self.sampled_commits):
            logger.info(f"\nProcessing sampled commit {i+1}/{len(self.sampled_commits)} ({commit[:8]})...")
            
            # Checkout commit
            self._did_checkout = True
            if not self.git_helper.checkout_commit(commit):
                logger.warning(f"Failed to checkout commit {commit[:8]}, skipping...")
                continue

            # Parse repository
            self.repo_parser = TreeSitterRepoParser(str(self.repo_path))
            self.repo_parser.parse_directory(str(self.repo_path))
            self.parsers_history[commit] = self.repo_parser

            # Generate embeddings for all entities
            entities = self.repo_parser.get_all_entities()
            entity_sources = {e.entity_id: self._get_contextual_source(e) for e in entities}
            self.sources_history[commit] = entity_sources

            if entity_sources:
                embeddings = self.embedding_manager.generate_embeddings_batch(entity_sources)
                self.embeddings_history[commit] = embeddings
                # The manager's own per-entity cache is only read during
                # evaluation (which resets it), and would otherwise keep every
                # commit's embedding matrix alive.
                self.embedding_manager.embeddings.clear()
                logger.info(f"  Parsed {len(entities)} entities, generated {len(embeddings)} embeddings")
            else:
                logger.warning(f"  No entities found in commit {commit[:8]}")
                self.embeddings_history[commit] = {}
            self.entity_counts[commit] = len(self.embeddings_history[commit])
            if commit in keep_for_eval:
                self._save_snapshot(commit)

            # Compare only sampled neighbors; skip all intermediate commits entirely.
            if i > 0:
                commit_prev = self.sampled_commits[i - 1]
                drifts, features = self.compute_drifts_and_features(commit_prev, commit)

                if drifts and not features.empty:
                    self.drifts_history[(commit_prev, commit)] = drifts
                    self.features_history[(commit_prev, commit)] = features

                    if self.label_source == "embedded_text_changed":
                        gt_labels = self.compute_text_changed_labels(commit_prev, commit)
                        self.ground_truth_history[(commit_prev, commit)] = gt_labels
                    elif self.label_source in BINARY_LABEL_SOURCES:
                        gt_labels = self.compute_ground_truth_labels(commit_prev, commit)
                        self.ground_truth_history[(commit_prev, commit)] = gt_labels
                        if not gt_labels:
                            logger.warning(
                                f"No {self.label_source} ground-truth labels produced for "
                                f"{commit_prev[:8]} -> {commit[:8]} (empty query "
                                f"overlap with this snapshot's entities)."
                            )

                    # Generate training log diagnostic
                    try:
                        modified_files = self.git_helper.get_modified_files(commit_prev, commit)
                        # Same semantic (AST-normalized) definition the features use.
                        modified_entities = sorted(
                            self.modified_entities_history.get((commit_prev, commit), set())
                        )

                        parser_prev = self.parsers_history.get(commit_prev)
                        prev_entities = set(parser_prev.get_graph().nodes()) if (parser_prev and parser_prev.get_graph() is not None) else set()
                        curr_entities = set(self.repo_parser.get_graph().nodes()) if self.repo_parser.get_graph() is not None else set()
                        added_entities = list(curr_entities - prev_entities)
                        removed_entities = list(prev_entities - curr_entities)
                        
                        git_changes = {
                            "added_entities": added_entities,
                            "modified_entities": modified_entities,
                            "removed_entities": removed_entities,
                            "modified_files": modified_files
                        }
                        self._save_commit_diagnostic(
                            commit_a=commit_prev,
                            commit_b=commit,
                            type_label="training",
                            drifts=drifts,
                            features_df=features,
                            git_changes=git_changes
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save training diagnostic for {commit_prev[:8]} -> {commit[:8]}: {e}")

            # ---- Add RSD entry for this commit ----
            self.rsd.add_commit(
                commit_hash=commit,
                repo_parser=self.repo_parser,
                embeddings=self.embeddings_history.get(commit, {}),
                modification_history=self.modification_history,
                previous_drifts=self.previous_drifts,
                commit_index=i,
                total_commits=len(self.sampled_commits)
            )

            if i > 0:
                self._release_commit(self.sampled_commits[i - 1], keep_for_eval)

            # Small delay
            time.sleep(0.1)

        logger.info(
            f"\nDataset built: {len(self.drifts_history)} commit pairs with data "
            f"(stride={self.commit_stride}, sampled_commits={len(self.sampled_commits)})"
        )

        # ---- Finalise split chronologically ----
        logger.info("Building RSDs and finalising chronological train/test split...")
        self.rsd.build_all_rsds()

        self._split_commits()
        logger.info("\nRSD Summary:\n" + self.rsd.summary_table())
        self._save_dataset_cache()

        return True

    def _split_commits(self) -> None:
        """Chronological train/test split of the sampled commits."""
        split_idx = max(1, int(len(self.sampled_commits) * self.train_ratio))
        self.train_commits = self.sampled_commits[:split_idx]
        self.test_commits = self.sampled_commits[split_idx:]
        logger.info(f"Chronological split -> train={len(self.train_commits)}, test={len(self.test_commits)}")

    # ------------------------------------------------------------------
    # Dataset cache
    # ------------------------------------------------------------------

    def _dataset_cache_meta(self) -> Dict:
        """Every setting the built dataset depends on (training-only settings excluded)."""
        sampled = self.commits[::self.commit_stride][:self.num_commits]
        meta = {
            "version": DATASET_CACHE_VERSION,
            "repo_url": self.repo_url,
            "sampled_commits": list(sampled),
            "model_name": self.model_name,
            "context_chunking": self.context_chunking,
            "clean_mode": self.clean_mode,
            "label_source": self.label_source,
        }
        if self.label_source in ("leave_one_out", "hybrid"):
            meta.update(
                ground_truth_queries_path=self.ground_truth_queries_path,
                ground_truth_top_k=self.ground_truth_top_k,
                ground_truth_rule=self.ground_truth_rule,
                ground_truth_min_queries=self.ground_truth_min_queries,
                max_queries_per_entity=self.max_queries_per_entity,
            )
        return meta

    def _dataset_cache_path(self) -> Optional[Path]:
        if self.dataset_dir is None:
            return None
        meta = self._dataset_cache_meta()
        digest = hashlib.sha1(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:10]
        repo_name = Path(self.repo_url.rstrip("/\\")).name.removesuffix(".git")
        model_short = self.model_name.split("/")[-1]
        name = (f"{repo_name}_{meta['sampled_commits'][0][:8]}_n{self.num_commits}_s{self.commit_stride}_"
                f"{model_short}_{'ctx' if self.context_chunking else 'iso'}_{self.label_source}_{digest}")
        return self.dataset_dir / name

    def _save_snapshot(self, commit: str) -> None:
        """Cache one commit's parser and embeddings (needed again at evaluation)."""
        path = self._dataset_cache_path()
        if path is None:
            return
        (path / "snapshots").mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"parser": self.parsers_history[commit], "embeddings": self.embeddings_history[commit]},
            path / "snapshots" / f"{commit}.joblib", compress=3,
        )

    def _save_dataset_cache(self) -> None:
        path = self._dataset_cache_path()
        if path is None:
            return
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "features_history": self.features_history,
            "drifts_history": self.drifts_history,
            "ground_truth_history": self.ground_truth_history,
            "modified_entities_history": self.modified_entities_history,
            "entity_counts": self.entity_counts,
            "modification_history": self.modification_history,
            "previous_drifts": self.previous_drifts,
            "rsd": self.rsd,
        }, path / "dataset.joblib", compress=3)
        meta = self._dataset_cache_meta()
        meta.update(created_at=datetime.now().isoformat(timespec="seconds"),
                    n_pairs=len(self.features_history),
                    ref=self.ref)
        (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        logger.info(f"Dataset cached to {path}")

    def _load_dataset_cache(self) -> bool:
        """Load a cached dataset built with the same settings; False if none."""
        path = self._dataset_cache_path()
        if path is None or self.rebuild_dataset or not (path / "dataset.joblib").exists():
            return False
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        expected = self._dataset_cache_meta()
        if any(meta.get(k) != v for k, v in expected.items()):
            logger.warning(f"Dataset cache {path} does not match the current settings; rebuilding.")
            return False

        logger.info("=" * 80)
        logger.info(f"LOADING CACHED DATASET from {path}")
        logger.info("=" * 80)
        data = joblib.load(path / "dataset.joblib")
        for key, value in data.items():
            setattr(self, key, value)
        self.sampled_commits = expected["sampled_commits"]
        self._split_commits()

        # Parsers/embeddings of the evaluation commits: from the cache, or
        # rebuilt for any the cache lacks (e.g. after lowering train_ratio).
        split_idx = max(1, int(len(self.sampled_commits) * self.train_ratio))
        for commit in self.sampled_commits[split_idx - 1:]:
            snap = path / "snapshots" / f"{commit}.joblib"
            if snap.exists():
                loaded = joblib.load(snap)
                self.parsers_history[commit] = loaded["parser"]
                self.embeddings_history[commit] = loaded["embeddings"]
                continue
            logger.info(f"  Snapshot for {commit[:8]} not cached; parsing and embedding it...")
            self._did_checkout = True
            if not self.git_helper.checkout_commit(commit):
                logger.error(f"Failed to checkout {commit[:8]} for evaluation")
                return False
            parser = TreeSitterRepoParser(str(self.repo_path))
            parser.parse_directory(str(self.repo_path))
            self.repo_parser = parser
            self.parsers_history[commit] = parser
            sources = {e.entity_id: self._get_contextual_source(e) for e in parser.get_all_entities()}
            self.embeddings_history[commit] = (
                self.embedding_manager.generate_embeddings_batch(sources) if sources else {}
            )
            self.embedding_manager.embeddings.clear()
            self._save_snapshot(commit)
        self.repo_parser = self.parsers_history[self.sampled_commits[-1]]
        logger.info(f"Loaded {len(self.features_history)} commit pairs "
                    f"({len(self.train_commits)} train / {len(self.test_commits)} test commits)")
        return True

    def _release_commit(self, commit: str, keep_for_eval: Set[str]) -> None:
        """Free per-commit data once both pairs that use ``commit`` are built."""
        self.sources_history.pop(commit, None)  # only needed for this pair's labels
        if commit not in keep_for_eval:
            self.parsers_history.pop(commit, None)
            self.embeddings_history.pop(commit, None)

    def train_model(self) -> bool:
        """
        Train drift prediction model.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("TRAINING MODEL")
        logger.info("=" * 80)
        logger.info(f"Label source: {self.label_source}")

        if self.label_source in BINARY_LABEL_SOURCES and self.predictor.task_type != "classification":
            logger.error(
                f"label_source='{self.label_source}' produces a binary Y_i label, which is not a "
                "valid regression target. Set task_type='classification' on the predictor, "
                "or use label_source='cosine_threshold' for regression."
            )
            return False

        # Which per-(commit_a, commit_b) label dict to train against — both
        # are entity_id -> float, so everything below is label-source-agnostic.
        label_history = self.ground_truth_history if self.label_source in BINARY_LABEL_SOURCES else self.drifts_history

        if len(self.train_commits) < 2:
            logger.error(
                "Not enough sampled commits to train: "
                f"train={len(self.train_commits)} with stride={self.commit_stride}. "
                "Increase --num-commits or reduce the stride."
            )
            return False

        # Train on every commit pair inside the training commits; evaluate on the
        # pairs that end in a test commit. One chronological split, no re-split.
        all_features, all_labels = self._collect_pairs(self._train_pairs(), label_history)
        test_features, test_labels = self._collect_pairs(self._test_pairs(), label_history)

        if not all_features:
            logger.error(
                "No training data available"
                + (f" ({self.label_source} label_source produced no labels for any training commit "
                   "pair — check query target coverage against this repo's entities)"
                   if self.label_source in BINARY_LABEL_SOURCES else "")
            )
            return False

        # Combine features
        combined_features = pd.concat(all_features, ignore_index=False)
        # Remove duplicate composite rows if any exist
        combined_features = combined_features[~combined_features.index.duplicated(keep='first')]

        logger.info(f"Training on {len(combined_features)} entities with {len(all_labels)} label values")

        if self.label_source in BINARY_LABEL_SOURCES:
            # Y_i is already binary (0.0/1.0) from binarize_ground_truth() — a
            # percentile-based dynamic threshold would be meaningless here.
            # 0.5 cleanly separates the two label values regardless of which
            # one prepare_data()'s `>= threshold` check is applied to.
            self.predictor.threshold = 0.5
            positive_rate = sum(all_labels.values()) / len(all_labels) if all_labels else 0.0
            logger.info(
                f"leave_one_out labels: {sum(all_labels.values()):.0f}/{len(all_labels)} "
                f"({positive_rate:.1%}) positive across combined training data."
            )
        elif self.threshold_mode == "dynamic":
            # Dynamically calculate threshold if configured.
            # Most entities in any given commit pair are untouched (directly or via
            # context) and have exactly-zero drift; including them in the percentile
            # collapses the threshold to ~0 regardless of the percentile chosen. Take
            # the percentile over entities that actually drifted at all instead.
            drift_values = [v for v in all_labels.values() if not np.isnan(v)]
            nonzero_drift_values = [v for v in drift_values if v > 1e-9]
            if nonzero_drift_values:
                self.threshold = float(np.percentile(nonzero_drift_values, 85))
                self.predictor.threshold = self.threshold
                logger.info(
                    f"Dynamically adjusted drift threshold to {self.threshold:.4f} "
                    f"based on 85th percentile of nonzero training drifts "
                    f"({len(nonzero_drift_values)}/{len(drift_values)} rows had any drift)"
                )
            elif drift_values:
                logger.warning(
                    f"All {len(drift_values)} training drift values are ~zero; "
                    f"keeping configured threshold {self.threshold:.4f} instead of a degenerate dynamic one"
                )

        # Prepare data (prepare_data also records the feature column order)
        try:
            X_train, y_train = self.predictor.prepare_data(combined_features, all_labels)
        except ValueError as e:
            logger.error(f"Failed to prepare data: {e}")
            return False

        # Train model on all training pairs
        train_metrics = self.predictor.train(X_train, y_train)

        # Pick the stale/fresh probability cut-off from out-of-fold predictions,
        # grouped by commit pair (row ids are "<pair>::<entity_id>").
        pair_groups = [row_id.split("::")[0] for row_id in self.predictor.last_common_ids]
        self.predictor.fit_decision_threshold(X_train, y_train, pair_groups)

        # Evaluate on the held-out test pairs
        test_metrics = {}
        X_test = y_test = None
        if test_features:
            test_df = pd.concat(test_features, ignore_index=False)
            test_df = test_df[~test_df.index.duplicated(keep='first')]
            try:
                X_test, y_test = self.predictor.prepare_data(test_df, test_labels)
                test_metrics = self.predictor.evaluate(X_test, y_test)
            except ValueError as e:
                logger.warning(f"Could not evaluate on test pairs: {e}")
        else:
            logger.warning("No labelled test commit pairs — skipping held-out evaluation.")

        # Save model artifact bundle
        model_path = self.results_dir / "drift_predictor.pkl"
        self.predictor.training_metadata = {
            "repo_url": self.repo_url,
            "ref": self.ref,
            "model_name": self.model_name,
            "context_chunking": self.context_chunking,
            "large_context": self.embedding_manager.is_large_context(),
            "clean_mode": self.clean_mode,
            "label_source": self.label_source,
            "ground_truth_rule": self.ground_truth_rule,
            "target_recall": self.target_recall,
            "model_type": self.model_type,
            "sampled_commits": list(self.sampled_commits),
            "train_commits": list(self.train_commits),
            "test_commits": list(self.test_commits),
            "trained_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.predictor.save_artifact(str(model_path))

        logger.info(f"Model artifact saved to {model_path}")
        logger.info(f"Test metrics: {test_metrics}")

        # If --compare-models is enabled, train & evaluate all candidate model architectures
        if getattr(self, "compare_models", False) and X_test is not None:
            logger.info("=" * 80)
            logger.info("RUNNING MULTI-MODEL COMPARISON")
            logger.info("=" * 80)
            from predictor.predictor import compare_all_models
            comp_df, predictors_dict = compare_all_models(
                X_train, y_train, X_test, y_test,
                task_type=self.predictor.task_type,
                threshold=self.predictor.threshold,
                feature_names=self.predictor.feature_names,
                target_recall=self.target_recall,
                groups=pair_groups,
                exclude=self.compare_models_exclude,
            )
            comp_csv_path = self.results_dir / "model_comparison.csv"
            comp_df.to_csv(comp_csv_path, index=False)
            logger.info(f"Saved multi-model comparison table to {comp_csv_path}")
            logger.info("\n" + comp_df.to_string())

            if self.visualizer:
                self.visualizer.plot_model_comparison(comp_df, "model_comparison.png")
                self.visualizer.plot_model_roc_pr_curves(predictors_dict, X_test, y_test, "model_pr_curves.png")
                self.visualizer.plot_model_confusion_matrices(predictors_dict, X_test, y_test)

        return True

    def _train_pairs(self) -> List[Tuple[str, str]]:
        """Consecutive sampled-commit pairs entirely inside the training commits."""
        return [(self.train_commits[i - 1], self.train_commits[i]) for i in range(1, len(self.train_commits))]

    def _test_pairs(self) -> List[Tuple[str, str]]:
        """Consecutive sampled-commit pairs ending in a test commit (incl. the train->test boundary pair)."""
        test_set = set(self.test_commits)
        return [
            (self.sampled_commits[i - 1], self.sampled_commits[i])
            for i in range(1, len(self.sampled_commits))
            if self.sampled_commits[i] in test_set
        ]

    def _collect_pairs(self, pairs, label_history) -> Tuple[List[pd.DataFrame], Dict[str, float]]:
        """Features (index prefixed by pair) and labels for the given commit pairs."""
        frames: List[pd.DataFrame] = []
        labels: Dict[str, float] = {}
        for commit_a, commit_b in pairs:
            key = (commit_a, commit_b)
            if key in self.features_history and key in label_history and label_history[key]:
                features_df = self.features_history[key].copy()
                pair_prefix = f"{commit_a[:8]}_{commit_b[:8]}"
                features_df.index = [f"{pair_prefix}::{eid}" for eid in features_df.index]
                frames.append(features_df)
                labels.update({f"{pair_prefix}::{eid}": v for eid, v in label_history[key].items()})
        return frames, labels

    def evaluate_strategies(self) -> Dict:
        """
        Evaluate all cache invalidation strategies on test commits.

        Returns:
            Dictionary with evaluation results
        """
        logger.info("=" * 80)
        logger.info("EVALUATING STRATEGIES")
        logger.info("=" * 80)

        all_strategy_results = {}
        drift_by_distance = {}
        all_predictions = []
        all_labels = []
        reembed_coverage: List[Dict] = []
        self.predictions_export = {}

        # Same label-source switch as train_model() — both dicts are
        # entity_id -> float. Strategy decisions use the model's own decision
        # threshold: 0.5 on predicted probabilities for classification, the drift
        # threshold for regression.
        label_history = self.ground_truth_history if self.label_source in BINARY_LABEL_SOURCES else self.drifts_history

        decision_threshold = (
            self.predictor.decision_threshold if self.predictor.task_type == "classification" else self.threshold
        )
        test_pairs = self._test_pairs()

        # Process each test commit pair (including the train->test boundary pair).
        for i, (commit_a, commit_b) in enumerate(test_pairs, start=1):
            parser_b = self.parsers_history.get(commit_b, self.repo_parser)
            parser_a = self.parsers_history.get(commit_a)

            logger.info(f"\nEvaluating commit pair {i}/{len(test_pairs)}: "
                       f"{commit_a[:8]} -> {commit_b[:8]}")

            # Get labels and features (label_history: see label-source note above)
            key = (commit_a, commit_b)
            if key not in label_history or key not in self.features_history or not label_history[key]:
                logger.warning(f"No data for commit pair {commit_a[:8]} -> {commit_b[:8]}")
                continue

            drifts = label_history[key]
            features_df = self.features_history[key]

            # Prepare data for prediction
            X, y_true = self.predictor.prepare_data(features_df, drifts)
            aligned_ids = self.predictor.last_common_ids

            # Predict drifts / probabilities
            if self.predictor.task_type == "classification":
                y_prob = self.predictor.predict_proba(X)
                y_pred = (
                    positive_class_proba(self.predictor.model, y_prob)
                    if y_prob is not None else self.predictor.predict(X)
                )
                y_pred_class = self.predictor.predict(X)
            else:
                y_pred = self.predictor.predict(X)
                y_pred_class = (y_pred >= self.threshold).astype(int)

            if self.label_source in BINARY_LABEL_SOURCES:
                actual_y_true = np.array([int(drifts.get(eid, 0.0)) for eid in aligned_ids])
            else:
                actual_drifts = self.drifts_history.get((commit_a, commit_b), {})
                actual_y_true = np.array([1 if actual_drifts.get(eid, 0.0) >= self.threshold else 0 for eid in aligned_ids])

            all_predictions.extend(y_pred_class)
            all_labels.extend(actual_y_true)

            # Record predictions for export
            pair_prefix = f"{commit_a[:8]}_{commit_b[:8]}"
            full_pair_prefix = f"{commit_a}_{commit_b}"
            for eid, pred_val in zip(aligned_ids, y_pred):
                self.predictions_export[f"{pair_prefix}::{eid}"] = float(pred_val)
                self.predictions_export[f"{full_pair_prefix}::{eid}"] = float(pred_val)
                self.predictions_export[eid] = float(pred_val)

            # Get ground truth embeddings (at commit_b)
            ground_truth_embeddings = self.embeddings_history.get(commit_b, {})

            # Entities whose own source changed (same definition as the benchmark's changed_only)
            modified_files = self.git_helper.get_modified_files(commit_a, commit_b)
            modified_entities = compute_source_changed_entities(parser_a, parser_b, modified_files)

            # Evaluation queries, chosen independently of the labels
            queries = self._generate_queries(parser_b, seed_key=commit_b)

            # Reset embedding manager's cache to commit_a's embeddings for accurate simulation
            self.embedding_manager.embeddings = self.embeddings_history[commit_a].copy()

            # Set evaluator's repo_parser to the parser of commit_b for accurate graph lookups
            if commit_b in self.parsers_history:
                self.evaluator.repo_parser = self.parsers_history[commit_b]

            # Evaluate all strategies
            strategy_results = self.evaluator.evaluate_all_strategies(
                ground_truth_embeddings=ground_truth_embeddings,
                predicted_drifts={eid: d for eid, d in zip(aligned_ids, y_pred)},
                modified_entities=modified_entities,
                queries=queries,
                threshold=decision_threshold,
                k_values=[5, 10],
                fixed_hop_values=[1, 2]
            )

            # Entities each strategy re-embeds for this pair, and how many of the
            # entities that needed re-embedding (positive label) each one covered.
            predicted = {eid: d for eid, d in zip(aligned_ids, y_pred)}
            strategy_re_embeddings = {
                "changed_only": list(BaselineAChangedOnly().get_entities_to_update(
                    modified_entities, predicted, decision_threshold
                )),
                "full_reindex": list(BaselineBFullReindex().get_entities_to_update(
                    modified_entities, predicted, decision_threshold
                )),
                "fixed_hop_k1": list(BaselineCFixedHop(k=1).get_entities_to_update(
                    modified_entities, predicted, decision_threshold, repo_parser=parser_b
                )),
                "fixed_hop_k2": list(BaselineCFixedHop(k=2).get_entities_to_update(
                    modified_entities, predicted, decision_threshold, repo_parser=parser_b
                )),
                "predictive_ml": list(PredictiveStrategy().get_entities_to_update(
                    modified_entities, predicted, decision_threshold
                )),
                "pagerank_propagation": list(BaselineDPageRankPropagation(top_fraction=0.3).get_entities_to_update(
                    modified_entities, predicted, decision_threshold, repo_parser=parser_b
                )),
                "weighted_bfs_decay": list(WeightedBFSDecayStrategy(threshold=0.05).get_entities_to_update(
                    modified_entities, predicted, decision_threshold, repo_parser=parser_b
                ))
            }
            reembed_coverage.append(reembed_coverage_row(
                commit_a, commit_b,
                needed={eid for eid, y in zip(aligned_ids, actual_y_true) if y == 1},
                labeled=set(aligned_ids),
                strategy_sets=strategy_re_embeddings,
            ))

            # Generate testing log diagnostic
            try:
                invalidation_decisions = {
                    "predicted_stale": [str(eid) for eid, pred in zip(aligned_ids, y_pred_class) if pred == 1],
                    "predicted_fresh": [str(eid) for eid, pred in zip(aligned_ids, y_pred_class) if pred == 0],
                    "raw_predictions": {str(eid): float(val) for eid, val in zip(aligned_ids, y_pred)}
                }

                parser_prev = self.parsers_history.get(commit_a)
                prev_entities = set(parser_prev.get_graph().nodes()) if (parser_prev and parser_prev.get_graph() is not None) else set()
                curr_entities = set(parser_b.get_graph().nodes())
                added_entities = list(curr_entities - prev_entities)
                removed_entities = list(prev_entities - curr_entities)

                git_changes = {
                    "added_entities": added_entities,
                    "modified_entities": list(modified_entities),
                    "removed_entities": removed_entities,
                    "modified_files": modified_files
                }

                self._save_commit_diagnostic(
                    commit_a=commit_a,
                    commit_b=commit_b,
                    type_label="testing",
                    drifts=drifts,
                    features_df=features_df,
                    git_changes=git_changes,
                    invalidation_decisions=invalidation_decisions,
                    strategy_re_embeddings=strategy_re_embeddings,
                    strategy_metrics=strategy_results
                )
            except Exception as e:
                logger.warning(f"Failed to save testing diagnostic for {commit_a[:8]} -> {commit_b[:8]}: {e}")

            # Accumulate results
            for strategy_name, metrics in strategy_results.items():
                if strategy_name not in all_strategy_results:
                    all_strategy_results[strategy_name] = {
                        'recall_at_5':       [],
                        'recall_at_10':      [],
                        'mrr':               [],
                        'ndcg_at_10':        [],
                        'rank_correlation':  [],
                        'update_percentage': [],
                        'entities_updated':  [],
                        'total_entities':    []
                    }

                for metric in ['recall_at_5', 'recall_at_10', 'mrr', 'ndcg_at_10',
                               'rank_correlation', 'update_percentage',
                               'entities_updated', 'total_entities']:
                    if metric in metrics:
                        all_strategy_results[strategy_name][metric].append(metrics[metric])

            # Track drift by distance
            for entity_id, drift in drifts.items():
                distance = self._get_distance_to_modified(entity_id, modified_entities, parser_b)
                if distance is not None:
                    if distance not in drift_by_distance:
                        drift_by_distance[distance] = []
                    drift_by_distance[distance].append(drift)

        # Compute average results
        averaged_results = {}
        for strategy_name, metrics in all_strategy_results.items():
            averaged_results[strategy_name] = {
                metric: np.mean(values) if values else 0.0
                for metric, values in metrics.items()
            }

        logger.info("\n" + "=" * 80)
        logger.info("AVERAGED STRATEGY RESULTS")
        logger.info("=" * 80)
        for strategy_name, metrics in averaged_results.items():
            logger.info(f"\n{strategy_name.upper()}:")
            logger.info(f"  Recall@5:    {metrics.get('recall_at_5',    0):.4f}")
            logger.info(f"  Recall@10:   {metrics.get('recall_at_10',   0):.4f}")
            logger.info(f"  MRR:         {metrics.get('mrr',            0):.4f}")
            logger.info(f"  nDCG@10:     {metrics.get('ndcg_at_10',     0):.4f}")
            logger.info(f"  Update %:    {metrics.get('update_percentage', 0):.2f}%")

        # Export predictions to a JSON file
        predictions_path = self.results_dir / "predictions.json"
        try:
            import json
            with predictions_path.open("w", encoding="utf-8") as f:
                json.dump(self.predictions_export, f, indent=2)
            logger.info(f"Exported continuous predictions to {predictions_path}")
        except Exception as e:
            logger.error(f"Failed to export predictions: {e}")

        return {
            'strategy_results': averaged_results,
            'drift_by_distance': drift_by_distance,
            'all_predictions': all_predictions,
            'all_labels': all_labels,
            'reembed_coverage': reembed_coverage,
        }

    def _extract_docstring_summary(self, source_code: str) -> Optional[str]:
        """Extract the first line of a multi-line or single-line docstring from source code.

        Args:
            source_code: Python entity source code string.

        Returns:
            First line of docstring summary if found, None otherwise.
        """
        import re
        match = re.search(r'"""(.*?)"""', source_code, re.DOTALL)
        if not match:
            match = re.search(r"'''(.*?)'''", source_code, re.DOTALL)
        if match:
            doc = match.group(1).strip()
            first_line = doc.split('\n')[0].strip()
            if len(first_line) > 5:
                return first_line
        return None

    def _generate_queries(self, repo_parser, seed_key: str = "", num_queries: int = 20) -> Dict[str, np.ndarray]:
        """
        Build the evaluation query set for one test commit pair.

        Queries are chosen independently of the labels (selecting by true drift
        would bias the evaluation toward the entities the labels already flag):
          1. Preferred: the independent ground-truth query set (curated/paraphrased),
             restricted to targets that exist at this commit, sampled with a fixed seed.
          2. Fallback: docstring-summary queries for a seeded random sample of
             entities. Entities without a docstring are skipped — no query is ever
             built from the entity's name or file name.

        Returns:
            Dictionary mapping query_id to query embedding
        """
        import zlib
        rng = np.random.default_rng(zlib.crc32(seed_key.encode("utf-8")))
        texts: Dict[str, str] = {}

        try:
            curated, _ = self._get_ground_truth_queries(repo_parser)
        except Exception as exc:
            logger.warning(f"Could not load ground-truth queries for evaluation: {exc}")
            curated = []
        present = [q for q in curated if repo_parser.get_entity(q.target_entity_id) is not None]
        if present:
            picks = rng.choice(len(present), size=min(num_queries, len(present)), replace=False)
            for idx in sorted(picks):
                texts[f"query_{len(texts)}"] = present[idx].query_text
        else:
            entities = sorted(repo_parser.get_all_entities(), key=lambda e: e.entity_id)
            for idx in rng.permutation(len(entities)):
                doc_summary = self._extract_docstring_summary(entities[idx].source_code)
                if doc_summary:
                    texts[f"query_{len(texts)}"] = (
                        f"Which function implements the following functionality: {doc_summary}?"
                    )
                if len(texts) >= num_queries:
                    break

        return {
            qid: self.embedding_manager.generate_embedding(qid, text)
            for qid, text in texts.items()
        }

    def _get_distance_to_modified(self, entity_id: str,
                                   modified_entities: Set[str],
                                   repo_parser=None) -> Optional[int]:
        """
        Get distance from entity to nearest modified entity.

        Args:
            entity_id: Entity identifier
            modified_entities: Set of modified entity IDs

        Returns:
            Distance or None
        """
        if entity_id in modified_entities:
            return 0

        return (repo_parser or self.repo_parser).get_nearest_modified_distance(entity_id, modified_entities)

    def generate_visualizations(self, results: Dict) -> None:
        """
        Generate all visualizations.

        Args:
            results: Dictionary with evaluation results
        """
        logger.info("=" * 80)
        logger.info("GENERATING VISUALIZATIONS")
        logger.info("=" * 80)

        # Re-embed coverage: of the entities that needed re-embedding, how many
        # each strategy re-embedded (tables in reembed_coverage.json/.md).
        if results.get('reembed_coverage'):
            summary = save_reembed_coverage(results['reembed_coverage'], self.results_dir)
            results['reembed_coverage_summary'] = summary
            self.visualizer.plot_reembed_coverage(summary, results['reembed_coverage'])
            for name, s in summary.items():
                logger.info(
                    f"  Re-embed coverage {name:22s}: {s['reembedded_needed']}/{s['needed']} needed "
                    f"({s['coverage']:.2%}), missed {s['missed']}, extra {s['extra']}, "
                    f"re-embedded {s['reembedded_fraction']:.2%} of entities"
                )

        # Drift decay plot
        if results.get('drift_by_distance'):
            self.visualizer.plot_drift_decay(results['drift_by_distance'])

        # Feature importance plot
        feature_importance = self.predictor.get_feature_importance()
        if feature_importance:
            self.visualizer.plot_feature_importance(feature_importance)

        # Strategy comparison
        if results.get('strategy_results'):
            self.visualizer.plot_strategy_comparison(results['strategy_results'])

        # Ranking metrics (MRR + nDCG)
        if results.get('strategy_results'):
            self.visualizer.plot_ranking_metrics(results['strategy_results'])

        # Pareto frontier
        if results.get('strategy_results'):
            pareo_df = self.evaluator.compute_pareto_frontier(results['strategy_results'])
            all_df = self.evaluator.compute_maintenance_cost(results['strategy_results'])
            # Merge with recall data
            all_df = all_df.merge(
                pd.DataFrame([
                    {'strategy': k, 'recall': v.get('recall_at_10', 0)}
                    for k, v in results['strategy_results'].items()
                ]),
                on='strategy'
            )
            self.visualizer.plot_pareto_frontier(pareo_df, all_df)

        # Drift distribution
        if self.drifts_history:
            all_drifts = {}
            for drifts in self.drifts_history.values():
                all_drifts.update(drifts)
            if all_drifts:
                self.visualizer.plot_drift_distribution(all_drifts, self.threshold)

        # Confusion matrix
        if results.get('all_predictions') and results.get('all_labels'):
            self.visualizer.plot_confusion_matrix(
                np.array(results['all_labels']),
                np.array(results['all_predictions'])
            )

        # Summary report
        summary_results = {
            'feature_importance': feature_importance or {},
            'strategy_results': results.get('strategy_results', {})
        }
        self.visualizer.generate_summary_report(summary_results)

        logger.info("Visualizations generated successfully")

    def run(self) -> bool:
        """
        Run the complete experiment.

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        try:
            # Setup
            if not self.setup():
                return False
            self._original_head = self.git_helper.get_checkout_ref()

            # Harvest commits
            if not self.harvest_commits():
                return False

            # Build dataset (or reuse a cached one built with the same settings)
            if not (self._load_dataset_cache() or self.build_dataset()):
                return False

            # Train model
            if not self.train_model():
                return False

            # Evaluate strategies
            results = self.evaluate_strategies()

            # Generate visualizations
            self.generate_visualizations(results)

            # Save results
            self._save_results(results)

            elapsed_time = time.time() - start_time
            logger.info("=" * 80)
            logger.info(f"EXPERIMENT COMPLETED SUCCESSFULLY in {elapsed_time:.2f} seconds")
            logger.info("=" * 80)
            logger.info(f"Results saved to {self.results_dir}")
            logger.info(f"Logs saved to experiment.log")

            return True

        except Exception as e:
            logger.error(f"Experiment failed with error: {e}", exc_info=True)
            return False

        finally:
            # build_dataset checks out each sampled commit; put the repository back
            # where it was so later runs (and the benchmark) are unaffected.
            if self._original_head and self.git_helper and self._did_checkout:
                if self.git_helper.checkout_commit(self._original_head):
                    logger.info(f"Restored repository checkout to {self._original_head}")

    def _save_commit_diagnostic(self, commit_a: str, commit_b: str, type_label: str,
                                 drifts: Dict[str, float], features_df: pd.DataFrame,
                                 git_changes: Dict[str, List[str]],
                                 invalidation_decisions: Optional[Dict[str, List[str]]] = None,
                                 strategy_re_embeddings: Optional[Dict[str, List[str]]] = None,
                                 strategy_metrics: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        """
        Saves a detailed diagnostic log for a commit pair transition (commit_a -> commit_b).
        """
        output_file = self.commit_logs_dir / f"commit_from_{commit_a[:8]}_to_{commit_b[:8]}.json"

        # Serialize features dataframe into a dictionary
        features_dict = {}
        if not features_df.empty:
            features_dict = features_df.to_dict(orient="index")
            # Convert NumPy types in values to native Python types
            for eid, feature_map in list(features_dict.items()):
                features_dict[eid] = {
                    k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                    for k, v in feature_map.items()
                }

        # Extract dependency graph
        parser = self.parsers_history.get(commit_b) or self.repo_parser
        graph_data = {"nodes": [], "edges": []}
        if parser and hasattr(parser, "get_graph") and parser.get_graph() is not None:
            g = parser.get_graph()
            graph_data["nodes"] = list(g.nodes())
            graph_data["edges"] = [list(edge) for edge in g.edges()]

        log_data = {
            "commit_before": commit_a,
            "commit_after": commit_b,
            "type": type_label,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_changes": git_changes,
            "dependency_graph": graph_data,
            "features_matrix": features_dict,
            "cosine_drifts": {k: float(v) for k, v in drifts.items()},
            "invalidation_decisions": invalidation_decisions or {},
            "strategy_re_embeddings": strategy_re_embeddings or {},
            "strategy_metrics": strategy_metrics or {}
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, sort_keys=True)
        logger.info(f"Saved diagnostic log to {output_file}")

    def _save_results(self, results: Dict) -> None:
        """
        Save results to JSON file.

        Args:
            results: Results dictionary
        """
        output_path = self.results_dir / "results.json"

        # Convert numpy arrays to lists for JSON serialization
        serializable_results = {}

        if 'strategy_results' in results:
            serializable_results['strategy_results'] = {}
            for strategy, metrics in results['strategy_results'].items():
                serializable_results['strategy_results'][strategy] = {
                    k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                    for k, v in metrics.items()
                }

        if 'reembed_coverage_summary' in results:
            serializable_results['reembed_coverage'] = results['reembed_coverage_summary']

        if 'drift_by_distance' in results:
            serializable_results['drift_by_distance'] = {
                int(k): [float(v) for v in vals]
                for k, vals in results['drift_by_distance'].items()
            }

        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)

        logger.info(f"Results saved to {output_path}")

        # Ground-truth labels per commit pair (leave_one_out / hybrid), with the
        # semantically modified entities, so labels can be audited after the run.
        if self.ground_truth_history:
            train_pairs = set(self._train_pairs())
            gt_path = self.results_dir / "ground_truth_labels.json"
            with open(gt_path, 'w') as f:
                json.dump([
                    {
                        "commit_before": a,
                        "commit_after": b,
                        "split": "train" if (a, b) in train_pairs else "test",
                        "labels": {eid: int(v) for eid, v in sorted(labels.items())},
                        "modified_entities": sorted(self.modified_entities_history.get((a, b), set())),
                        "entities_total": self.entity_counts.get(b, 0),
                    }
                    for (a, b), labels in self.ground_truth_history.items()
                ], f, indent=2)
            logger.info(f"Ground-truth labels saved to {gt_path}")


def _explicit_cli_dests(parser: argparse.ArgumentParser, argv: Optional[List[str]] = None) -> Set[str]:
    """Destinations the user actually passed on the command line (even if equal to the default)."""
    import copy
    probe = copy.deepcopy(parser)
    for action in probe._actions:
        action.default = argparse.SUPPRESS
    explicit, _ = probe.parse_known_args(argv)
    return set(vars(explicit))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Predictive Semantic Cache Invalidation Experiment"
    )
    parser.add_argument(
        "--repo-url",
        default="https://github.com/psf/black.git",
        help="URL of repository to analyze"
    )
    parser.add_argument(
        "--workspace-dir",
        default="workspace",
        help="Directory for workspace"
    )
    parser.add_argument(
        "--num-commits",
        type=int,
        default=50,
        help="Number of sampled commits to analyze"
    )
    parser.add_argument(
        "--commit-stride",
        type=int,
        default=20,
        help="Step size between sampled commits"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Ratio of commits to use for training"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.02,
        help="Drift threshold for classification"
    )
    parser.add_argument(
        "--clean-mode",
        action="store_true",
        help="Remove comments and docstrings before embedding"
    )
    parser.add_argument(
        "--context-chunking",
        action="store_true",
        help="Enable call-graph aware contextual chunking"
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=None,
        help="Run on subset of commits (for testing)"
    )
    parser.add_argument(
        "--threshold-mode",
        choices=["fixed", "dynamic"],
        default="dynamic",
        help="Whether to use a fixed threshold or compute it dynamically from percentile"
    )
    parser.add_argument(
        "--label-source",
        choices=["cosine_threshold", "leave_one_out", "hybrid", "embedded_text_changed"],
        default="cosine_threshold",
        help=(
            "Predictor training label: 'cosine_threshold' (default), 'leave_one_out' "
            "(curated query rank-displacement), 'embedded_text_changed' (embedded text differs "
            "between commits, i.e. vector differs from a full re-index), or 'hybrid' (curated + synthetic queries "
            "for 100% snapshot entity coverage)"
        )
    )
    parser.add_argument(
        "--ground-truth-top-k",
        type=int,
        default=10,
        help="Top-K window for the leave_one_out label source (ignored otherwise)"
    )
    parser.add_argument(
        "--ground-truth-queries-path",
        type=str,
        default=None,
        help="Override path to the curated query set for leave_one_out (default: "
             "src/benchmarking/data/curated_queries.json)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON configuration file to load options from"
    )
    parser.add_argument(
        "--parser-mode",
        choices=["ast", "joern_hybrid", "joern_only"],
        default="ast",
        help="Parser mode: ast (default), joern_hybrid (AST + Joern CPG features), or joern_only (pure Joern)"
    )
    parser.add_argument(
        "--use-joern",
        action="store_true",
        help="Alias for --parser-mode joern_hybrid"
    )
    parser.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="HuggingFace model name for embeddings"
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Device for the embedding model: auto (CUDA if available, else CPU), cpu, or cuda"
    )
    parser.add_argument(
        "--max-queries-per-entity",
        type=int,
        default=5,
        help="Max synthetic queries per uncovered entity for label_source=hybrid",
    )
    parser.add_argument(
        "--dataset-dir",
        default="datasets",
        help="Where built datasets are cached and reused by runs with the same dataset "
             "settings (empty string disables caching)",
    )
    parser.add_argument(
        "--rebuild-dataset",
        action="store_true",
        help="Ignore any cached dataset and rebuild it (the new build replaces the cache)",
    )
    parser.add_argument(
        "--model-type", "--predictor-model",
        dest="model_type",
        default="random_forest",
        choices=DriftPredictor.SUPPORTED_MODELS,
        help="Predictor model; hist_gradient_boosting and lightgbm are monotonic in the direct change signals",
    )
    parser.add_argument(
        "--target-recall",
        type=float,
        default=None,
        help="Pick the highest decision threshold whose out-of-fold recall reaches this "
             "value (e.g. 0.99) instead of the F1-optimal threshold",
    )
    parser.add_argument(
        "--ground-truth-rule",
        choices=["significant", "any_displacement"],
        default="significant",
        help="Label rule for leave_one_out/hybrid: displacement + sign test, or any target query displaced",
    )
    parser.add_argument(
        "--ground-truth-min-queries",
        type=int,
        default=5,
        help="Min target queries for an entity to be labelled (5 needed for the sign test)",
    )
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git ref (branch, tag, commit or expression like main~200) the sampled window ends at",
    )
    parser.add_argument(
        "--compare-models",
        action="store_true",
        help="Train and compare multiple ML model architectures (Random Forest, Gradient Boosting, HistGB, LightGBM, Extra Trees, Logistic Regression, MLP, SVC, KNN, Decision Tree, Naive Bayes)"
    )
    parser.add_argument(
        "--compare-models-exclude",
        type=lambda s: [m.strip() for m in s.split(",") if m.strip()],
        default=[],
        help="Comma-separated architectures to leave out of --compare-models (e.g. svc,knn on large datasets)",
    )

    args = parser.parse_args()

    # If --config is not specified, auto-load settings.json if it exists
    if not args.config and Path("settings.json").exists():
        args.config = "settings.json"

    # If --config is passed or auto-loaded, load JSON file and merge parameters
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            logger.info(f"Loading configuration from JSON file: {config_path}")
            def strip_json_comments(text: str) -> str:
                """Strip single-line and multi-line comments from JSON text while preserving string literals.

                Args:
                    text: Raw JSON string content.

                Returns:
                    Comment-stripped JSON string ready for parsing.
                """
                result = []
                in_string = False
                escape = False
                i, n = 0, len(text)
                while i < n:
                    char = text[i]
                    if escape:
                        result.append(char)
                        escape = False
                        i += 1
                        continue
                    if char == '\\':
                        result.append(char)
                        escape = True
                        i += 1
                        continue
                    if char == '"':
                        in_string = not in_string
                        result.append(char)
                        i += 1
                        continue
                    if not in_string:
                        if i + 1 < n and text[i:i+2] == '//':
                            while i < n and text[i] not in ('\r', '\n'):
                                i += 1
                            continue
                        if i + 1 < n and text[i:i+2] == '/*':
                            i += 2
                            while i + 1 < n and text[i:i+2] != '*/':
                                i += 1
                            i += 2
                            continue
                    result.append(char)
                    i += 1
                return "".join(result)

            with config_path.open("r", encoding="utf-8") as f:
                raw_content = f.read()
                clean_content = strip_json_comments(raw_content)
                json_config = json.loads(clean_content)
                explicit = _explicit_cli_dests(parser)
                for key, value in json_config.items():
                    if not hasattr(args, key):
                        logger.warning(f"Ignoring unknown key {key!r} in {config_path}")
                        continue
                    if key not in explicit:  # CLI flags always win over the JSON file
                        setattr(args, key, value)

    # Determine final parser mode
    parser_mode = args.parser_mode
    if args.use_joern and parser_mode == "ast":
        parser_mode = "joern_hybrid"

    # Create experiment
    experiment = Experiment(
        repo_url=args.repo_url,
        workspace_dir=args.workspace_dir,
        num_commits=args.num_commits if args.subset is None else args.subset,
        train_ratio=args.train_ratio,
        threshold=args.threshold,
        threshold_mode=args.threshold_mode,
        clean_mode=args.clean_mode,
        context_chunking=args.context_chunking,
        model_name=args.model_name,
        commit_stride=args.commit_stride,
        parser_mode=parser_mode,
        device=args.device,
        label_source=args.label_source,
        ground_truth_top_k=args.ground_truth_top_k,
        ground_truth_queries_path=args.ground_truth_queries_path,
        compare_models=getattr(args, "compare_models", False),
        max_queries_per_entity=args.max_queries_per_entity,
        ref=args.ref,
        ground_truth_rule=args.ground_truth_rule,
        ground_truth_min_queries=args.ground_truth_min_queries,
        target_recall=args.target_recall,
        model_type=args.model_type,
        compare_models_exclude=args.compare_models_exclude,
        dataset_dir=args.dataset_dir or None,
        rebuild_dataset=args.rebuild_dataset,
    )

    # Run experiment
    success = experiment.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
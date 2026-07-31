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

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from git_helper import GitHelper
from repo_parser import RepoParser, Entity
from embedding_manager import EmbeddingManager
from feature_extractor import FeatureExtractor
from predictor import DriftPredictor, train_test_split_temporal
from evaluator import (Evaluator, BaselineAChangedOnly, BaselineBFullReindex,
                       BaselineCFixedHop, BaselineDPageRankPropagation,
                       PredictiveStrategy)
from visualize import Visualizer
from rsd import RepositoryStateDescriptor
from gtd import GraphTransitionDescriptor

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
                 parser_mode: str = "ast"):
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
        """
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
        self.joern_session = None

        # Paths
        self.repo_path = self.workspace_dir / "black"
        
        # Determine unique results directory name based on configuration
        mode_str = "contextual" if self.context_chunking else "isolated"
        model_slug = model_name.split("/")[-1]
        dir_name = (
            f"results_{model_slug}_{mode_str}_commits{self.num_commits}"
            f"_stride{self.commit_stride}_clean{self.clean_mode}"
        )
        self.results_dir = Path("results") / dir_name
        self.results_dir.mkdir(parents=True, exist_ok=True)

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
        self.features_history = {}  # (commit_a, commit_b) -> features DataFrame
        self.modification_history = {}  # entity_id -> list of commit hashes
        self.previous_drifts = {}  # entity_id -> last drift value
        self.parsers_history = {}  # commit_hash -> RepoParser instance
        self.gtd_history = {}  # (commit_a, commit_b) -> GraphTransitionDescriptor

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

        # Initialize Joern session if requested
        if self.parser_mode in ["joern_hybrid", "joern_only"]:
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent / "joern_helper"))
                from joern_interactive import JoernSession
                self.joern_session = JoernSession(str(self.repo_path))
                logger.info(f"Joern session connected successfully for mode: {self.parser_mode}")
            except Exception as e:
                logger.warning(f"Failed to initialize Joern session ({e}). Falling back to AST parser_mode.")
                self.parser_mode = "ast"

        # Initialize repository parser based on parser_mode
        if self.parser_mode == "joern_only" and self.joern_session:
            from joern_repo_parser import JoernRepoParser
            candidate = JoernRepoParser(str(self.repo_path), self.joern_session)

            # Ensure it matches the RepoParser interface expected elsewhere
            required = ("parse_directory", "get_graph", "get_entity", "get_all_entities")
            if all(hasattr(candidate, name) for name in required):
                self.repo_parser = candidate
                logger.info("Using Pure JoernRepoParser for repository parsing and graph construction")
            else:
                logger.warning(
                    "JoernRepoParser does not implement the RepoParser interface; falling back to AST parser."
                )
                self.parser_mode = "ast"
                self.repo_parser = RepoParser(str(self.repo_path))
        else:
            self.repo_parser = RepoParser(str(self.repo_path))
        self.embedding_manager = EmbeddingManager(model_name=self.model_name, clean_mode=self.clean_mode)
        self.feature_extractor = FeatureExtractor(self.repo_parser, joern_session=self.joern_session)
        self.predictor = DriftPredictor(threshold=self.threshold)
        self.evaluator = Evaluator(self.embedding_manager, self.repo_parser)
        self.visualizer = Visualizer(str(self.results_dir))

        logger.info(f"Setup complete (parser_mode={self.parser_mode})")
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
        self.commits = self.git_helper.get_commit_history(count=raw_commit_count)

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
        """
        Extract the signature lines from an entity's source code.
        """
        lines = entity.source_code.splitlines()
        def_idx = -1
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class "):
                def_idx = idx
                break

        if def_idx == -1:
            # Fallback to name-only signature if def/class keyword is not found
            name = entity.entity_id.split("::")[-1]
            return f"def {name}()"

        # Extract signature lines from def_idx until we find the ending colon ':'
        sig_lines = []
        found_colon = False
        for idx in range(def_idx, len(lines)):
            line = lines[idx]
            sig_lines.append(line)
            # Strip trailing comments and whitespace to check for end of signature
            clean_line = line.split('#')[0].rstrip()
            if clean_line.endswith(':'):
                found_colon = True
                break

        if found_colon:
            return "\n".join(sig_lines)
        else:
            return lines[def_idx]

    def _get_contextual_source(self, entity: Entity) -> str:
        """
        Get call-graph aware contextual source code for an entity.
        Appends direct dependencies as valid Python stubs.
        """
        source = entity.source_code
        if not self.context_chunking:
            return source

        # Get direct dependencies (max_hops=1)
        # Note: get_dependencies returns a set of entity IDs.
        deps = self.repo_parser.get_dependencies(entity.entity_id, max_hops=1)
        # Filter out self
        deps = {d for d in deps if d != entity.entity_id}

        if not deps:
            return source

        import hashlib
        import textwrap

        is_large_context = False
        if hasattr(self, 'embedding_manager') and self.embedding_manager and self.embedding_manager.model:
            is_large_context = getattr(self.embedding_manager.model, 'max_seq_length', 512) >= 8192

        stubs = []
        for dep_id in sorted(deps):
            dep_entity = self.repo_parser.get_entity(dep_id)
            if not dep_entity:
                continue

            # Extract signature
            sig = self._extract_signature(dep_entity)
            sig_dedented = textwrap.dedent(sig).strip()
            if not sig_dedented.endswith(':'):
                sig_dedented += ':'

            if is_large_context:
                # Large context window (8k+): include full docstrings & signatures without hashing
                doc = (getattr(dep_entity, 'docstring', '') or '').replace('"""', r'\"\"\"')
                if doc:
                    doc_indented = textwrap.indent(doc, '    ')
                    doc_block = f'    """\n{doc_indented}\n    """\n'
                else:
                    doc_block = ''
                stub = f"{sig_dedented}\n{doc_block}    pass"
            else:
                # Small context window (<8k): use compact MD5 hash stub
                dep_hash = hashlib.md5(dep_entity.source_code.encode('utf-8')).hexdigest()
                stub = f"{sig_dedented}\n    _dep_hash_ = '{dep_hash}'\n    pass"

            stubs.append(stub)

        if stubs:
            context_block = "\n\n# Call Graph Context\n" + "\n\n".join(stubs)
            return source + context_block

        return source

    def process_commit(self, commit_hash: str) -> None:
        """
        Process a single commit: parse repo and generate embeddings.

        Args:
            commit_hash: Git commit hash
        """
        logger.info(f"Processing commit {commit_hash[:8]}...")

        # Checkout commit
        if not self.git_helper.checkout_commit(commit_hash):
            logger.warning(f"Failed to checkout commit {commit_hash[:8]}, skipping...")
            return

        # Rebuild Joern CPG for the current commit disk state
        if self.parser_mode in ["joern_hybrid", "joern_only"] and self.joern_session:
            logger.info("Rebuilding Joern CPG for the checked-out commit...")
            try:
                self.joern_session.rebuild_cpg()
            except Exception as e:
                logger.warning(f"Failed to rebuild Joern CPG: {e}")

        # Parse repository
        if self.parser_mode == "joern_only" and self.joern_session:
            from joern_repo_parser import JoernRepoParser
            self.repo_parser = JoernRepoParser(str(self.repo_path), self.joern_session)
            self.repo_parser.parse_repository()
        else:
            self.repo_parser = RepoParser(str(self.repo_path))
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

        # Compute Graph Transition Descriptor (GTD) with actual drifts
        parser_a = self.parsers_history.get(commit_a)
        parser_b = self.repo_parser
        gtd = GraphTransitionDescriptor()
        gtd.compute(parser_a=parser_a, parser_b=parser_b, drifts=drifts)
        self.gtd_history[(commit_a, commit_b)] = gtd

        # Get modified entities
        modified_files = self.git_helper.get_modified_files(commit_a, commit_b)
        logger.debug(f"Modified files: {modified_files[:5] if len(modified_files) > 5 else modified_files}")

        # Map files to entities
        modified_entities = set()
        for entity_id in drifts.keys():
            entity = self.repo_parser.get_entity(entity_id)
            if entity and entity.file_path in modified_files:
                modified_entities.add(entity_id)

        # Also add entities from modified files
        for entity in self.repo_parser.get_all_entities():
            if entity.file_path in modified_files:
                modified_entities.add(entity.entity_id)
        
        logger.debug(f"Modified entities count: {len(modified_entities)}")

        # Extract features (only for entities in current graph)
        entity_ids = [eid for eid in drifts.keys() if eid in self.repo_parser.get_graph()]
        if not entity_ids:
            logger.warning("No entities found in current graph")
            return {}, pd.DataFrame()

        # Update feature extractor with current graph and optional Joern session
        self.feature_extractor = FeatureExtractor(self.repo_parser, joern_session=self.joern_session)
        
        features_df = self.feature_extractor.extract_features_batch(
            entity_ids, commit_a, commit_b, modified_entities,
            self.modification_history, self.previous_drifts, self.git_helper,
            gtd=gtd, joern_session=self.joern_session
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

        for i, commit in enumerate(self.sampled_commits):
            logger.info(f"\nProcessing sampled commit {i+1}/{len(self.sampled_commits)} ({commit[:8]})...")
            
            # Checkout commit
            if not self.git_helper.checkout_commit(commit):
                logger.warning(f"Failed to checkout commit {commit[:8]}, skipping...")
                continue

            # Parse repository
            self.repo_parser = RepoParser(str(self.repo_path))
            self.repo_parser.parse_directory(str(self.repo_path))
            self.parsers_history[commit] = self.repo_parser

            # Generate embeddings for all entities
            entities = self.repo_parser.get_all_entities()
            entity_sources = {e.entity_id: self._get_contextual_source(e) for e in entities}

            if entity_sources:
                embeddings = self.embedding_manager.generate_embeddings_batch(entity_sources)
                self.embeddings_history[commit] = embeddings
                logger.info(f"  Parsed {len(entities)} entities, generated {len(embeddings)} embeddings")
            else:
                logger.warning(f"  No entities found in commit {commit[:8]}")
                self.embeddings_history[commit] = {}

            # Compare only sampled neighbors; skip all intermediate commits entirely.
            if i > 0:
                commit_prev = self.sampled_commits[i - 1]
                drifts, features = self.compute_drifts_and_features(commit_prev, commit)

                if drifts and not features.empty:
                    self.drifts_history[(commit_prev, commit)] = drifts
                    self.features_history[(commit_prev, commit)] = features

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

            # Small delay
            time.sleep(0.1)

        logger.info(
            f"\nDataset built: {len(self.drifts_history)} commit pairs with data "
            f"(stride={self.commit_stride}, sampled_commits={len(self.sampled_commits)})"
        )

        # ---- Finalise stratified split with RSD ----
        logger.info("Building RSDs and finalising stratified train/test split...")
        self.rsd.build_all_rsds()
        self.train_commits, self.test_commits = self.rsd.stratified_split(
            self.sampled_commits, train_ratio=self.train_ratio, n_clusters=3
        )
        logger.info(f"Stratified split -> train={len(self.train_commits)}, test={len(self.test_commits)}")
        logger.info("\nRSD Summary:\n" + self.rsd.summary_table())

        return True

    def train_model(self) -> bool:
        """
        Train drift prediction model.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("TRAINING MODEL")
        logger.info("=" * 80)

        # Combine features and drifts from training commits
        all_features = []
        all_drifts = {}

        if len(self.train_commits) < 2:
            logger.error(
                "Not enough sampled commits to train: "
                f"train={len(self.train_commits)} with stride={self.commit_stride}. "
                "Increase --num-commits or reduce the stride."
            )
            return False

        for i in range(1, len(self.train_commits)):
            commit_a = self.train_commits[i-1]
            commit_b = self.train_commits[i]

            key = (commit_a, commit_b)
            if key in self.features_history and key in self.drifts_history:
                features_df = self.features_history[key]
                drifts = self.drifts_history[key]

                all_features.append(features_df)
                all_drifts.update(drifts)

        if not all_features:
            logger.error("No training data available")
            return False

        # Combine features
        combined_features = pd.concat(all_features, ignore_index=False)
        # Remove duplicates (keep first occurrence)
        combined_features = combined_features[~combined_features.index.duplicated(keep='first')]

        logger.info(f"Training on {len(combined_features)} entities with {len(all_drifts)} drift values")

        # Dynamically calculate threshold if configured
        if self.threshold_mode == "dynamic":
            drift_values = [v for v in all_drifts.values() if not np.isnan(v)]
            if drift_values:
                self.threshold = float(np.percentile(drift_values, 85))
                self.predictor.threshold = self.threshold
                logger.info(f"Dynamically adjusted drift threshold to {self.threshold:.4f} based on 85th percentile of training drifts")

        # Prepare data
        try:
            X, y = self.predictor.prepare_data(combined_features, all_drifts)
        except ValueError as e:
            logger.error(f"Failed to prepare data: {e}")
            return False

        # Split data
        X_train, X_test, y_train, y_test = train_test_split_temporal(
            combined_features, all_drifts, train_ratio=self.train_ratio
        )

        # Train model
        train_metrics = self.predictor.train(X_train, y_train)

        # Evaluate on test set
        test_metrics = self.predictor.evaluate(X_test, y_test)

        # Save model
        model_path = self.results_dir / "drift_predictor.pkl"
        self.predictor.save(str(model_path))

        logger.info(f"Model saved to {model_path}")
        logger.info(f"Test metrics: {test_metrics}")

        return True

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

        # Process each test commit pair from the sampled commit sequence.
        for i, commit_b in enumerate(self.test_commits):
            if i == 0:
                continue  # Skip first test commit (no previous commit to compare)

            commit_a = self.test_commits[i - 1]

            logger.info(f"\nEvaluating commit pair {i}/{len(self.test_commits)-1}: "
                       f"{commit_a[:8]} -> {commit_b[:8]}")

            # Get drifts and features
            key = (commit_a, commit_b)
            if key not in self.drifts_history or key not in self.features_history:
                logger.warning(f"No data for commit pair {commit_a[:8]} -> {commit_b[:8]}")
                continue

            drifts = self.drifts_history[key]
            features_df = self.features_history[key]

            # Prepare data for prediction
            X, y_true = self.predictor.prepare_data(features_df, drifts)

            # Predict drifts
            y_pred = self.predictor.predict(X)

            # Convert to classification labels
            y_pred_class = (y_pred >= self.threshold).astype(int)
            y_true_class = (y_true >= self.threshold).astype(int)

            all_predictions.extend(y_pred_class)
            all_labels.extend(y_true_class)

            # Get ground truth embeddings (at commit_b)
            ground_truth_embeddings = self.embeddings_history.get(commit_b, {})

            # Get modified entities
            modified_files = self.git_helper.get_modified_files(commit_a, commit_b)
            modified_entities = set()
            for entity_id in drifts.keys():
                entity = self.repo_parser.get_entity(entity_id)
                if entity and entity.file_path in modified_files:
                    modified_entities.add(entity_id)

            # Generate queries from entity docstrings/first lines
            queries = self._generate_queries()

            # Reset embedding manager's cache to commit_a's embeddings for accurate simulation
            self.embedding_manager.embeddings = self.embeddings_history[commit_a].copy()

            # Set evaluator's repo_parser to the parser of commit_b for accurate graph lookups
            if commit_b in self.parsers_history:
                self.evaluator.repo_parser = self.parsers_history[commit_b]

            # Evaluate all strategies
            strategy_results = self.evaluator.evaluate_all_strategies(
                ground_truth_embeddings=ground_truth_embeddings,
                predicted_drifts={eid: d for eid, d in zip(features_df.index, y_pred)},
                modified_entities=modified_entities,
                queries=queries,
                threshold=self.threshold,
                k_values=[5, 10],
                fixed_hop_values=[1, 2]
            )

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
                distance = self._get_distance_to_modified(entity_id, modified_entities)
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

        return {
            'strategy_results': averaged_results,
            'drift_by_distance': drift_by_distance,
            'all_predictions': all_predictions,
            'all_labels': all_labels
        }

    def _generate_queries(self, num_queries: int = 20) -> Dict[str, np.ndarray]:
        """
        Generate search queries from entity docstrings and descriptions.

        Args:
            num_queries: Number of queries to generate

        Returns:
            Dictionary mapping query_id to query embedding
        """
        queries = {}

        entities = self.repo_parser.get_all_entities()

        # Use first N entities as queries (their source code as query)
        for i, entity in enumerate(entities[:num_queries]):
            # Use first few lines of source as query
            source_lines = entity.source_code.split('\n')[:3]
            query_text = ' '.join(source_lines)

            # Generate embedding
            query_embedding = self.embedding_manager.generate_embedding(
                f"query_{i}", query_text
            )
            queries[f"query_{i}"] = query_embedding

        return queries

    def _get_distance_to_modified(self, entity_id: str,
                                   modified_entities: Set[str]) -> Optional[int]:
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

        return self.repo_parser.get_nearest_modified_distance(entity_id, modified_entities)

    def generate_visualizations(self, results: Dict) -> None:
        """
        Generate all visualizations.

        Args:
            results: Dictionary with evaluation results
        """
        logger.info("=" * 80)
        logger.info("GENERATING VISUALIZATIONS")
        logger.info("=" * 80)

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

            # Harvest commits
            if not self.harvest_commits():
                return False

            # Build dataset
            if not self.build_dataset():
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

        if 'drift_by_distance' in results:
            serializable_results['drift_by_distance'] = {
                int(k): [float(v) for v in vals]
                for k, vals in results['drift_by_distance'].items()
            }

        with open(output_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)

        logger.info(f"Results saved to {output_path}")


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

    args = parser.parse_args()

    # If --config is passed, load JSON file and merge parameters
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            logger.info(f"Loading configuration from JSON file: {config_path}")
            import json
            with config_path.open("r", encoding="utf-8") as f:
                json_config = json.load(f)
                for key, value in json_config.items():
                    if hasattr(args, key) and getattr(args, key) == parser.get_default(key):
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
        parser_mode=parser_mode
    )

    # Run experiment
    success = experiment.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
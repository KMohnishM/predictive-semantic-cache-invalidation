"""Evaluator for cache invalidation strategies."""

from typing import Dict, List, Set, Tuple, Optional
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import logging
import time

logger = logging.getLogger(__name__)


class CacheInvalidationStrategy:
    """Base class for cache invalidation strategies."""

    def get_entities_to_update(self, modified_entities: Set[str],
                               predicted_drifts: Dict[str, float],
                               threshold: float = 0.02,
                               **kwargs) -> Set[str]:
        """
        Determine which entities need to be re-embedded.

        Args:
            modified_entities: Set of directly modified entity IDs
            predicted_drifts: Predicted drift scores for all entities
            threshold: Drift threshold for classification
            **kwargs: Additional strategy-specific parameters

        Returns:
            Set of entity IDs to update
        """
        raise NotImplementedError


class BaselineAChangedOnly(CacheInvalidationStrategy):
    """Baseline A: Re-embed only directly modified nodes."""

    def get_entities_to_update(self, modified_entities: Set[str],
                               predicted_drifts: Dict[str, float],
                               threshold: float = 0.02,
                               **kwargs) -> Set[str]:
        return modified_entities.copy()


class BaselineBFullReindex(CacheInvalidationStrategy):
    """Baseline B: Re-embed all nodes (ground truth)."""

    def get_entities_to_update(self, modified_entities: Set[str],
                               predicted_drifts: Dict[str, float],
                               threshold: float = 0.02,
                               **kwargs) -> Set[str]:
        return set(predicted_drifts.keys())


class BaselineCFixedHop(CacheInvalidationStrategy):
    """Baseline C: Re-embed modified nodes + dependents within K hops."""

    def __init__(self, k: int = 1):
        """
        Initialize fixed-hop strategy.

        Args:
            k: Number of hops to propagate
        """
        self.k = k

    def get_entities_to_update(self, modified_entities: Set[str],
                               predicted_drifts: Dict[str, float],
                               threshold: float = 0.02,
                               **kwargs) -> Set[str]:
        repo_parser = kwargs.get('repo_parser')
        if not repo_parser:
            return modified_entities.copy()

        entities_to_update = modified_entities.copy()

        # Add dependents within K hops
        for modified_id in modified_entities:
            dependents = repo_parser.get_dependents(modified_id, max_hops=self.k)
            entities_to_update.update(dependents)

        return entities_to_update


class PredictiveStrategy(CacheInvalidationStrategy):
    """Proposed strategy: Re-embed nodes predicted to have drift >= threshold."""

    def get_entities_to_update(self, modified_entities: Set[str],
                               predicted_drifts: Dict[str, float],
                               threshold: float = 0.02,
                               **kwargs) -> Set[str]:
        return {
            entity_id for entity_id, drift in predicted_drifts.items()
            if drift >= threshold
        }


class Evaluator:
    """Evaluates cache invalidation strategies."""

    def __init__(self, embedding_manager, repo_parser):
        """
        Initialize evaluator.

        Args:
            embedding_manager: EmbeddingManager instance
            repo_parser: RepoParser instance
        """
        self.embedding_manager = embedding_manager
        self.repo_parser = repo_parser

    def compute_recall_at_k(self, retrieved: List[str], ground_truth: List[str],
                            k: int = 5) -> float:
        """
        Compute Recall@K.

        Args:
            retrieved: List of retrieved entity IDs (ranked)
            ground_truth: List of relevant entity IDs
            k: Number of top results to consider

        Returns:
            Recall@K score
        """
        if not ground_truth:
            return 0.0

        top_k = retrieved[:k]
        relevant_retrieved = set(top_k) & set(ground_truth)
        return len(relevant_retrieved) / len(ground_truth)

    def compute_spearman_correlation(self, rankings1: Dict[str, float],
                                     rankings2: Dict[str, float]) -> float:
        """
        Compute Spearman's rank correlation between two rankings.

        Args:
            rankings1: First ranking (entity_id -> score)
            rankings2: Second ranking (entity_id -> score)

        Returns:
            Spearman correlation coefficient
        """
        # Get common entities
        common_ids = set(rankings1.keys()) & set(rankings2.keys())

        if len(common_ids) < 2:
            return 0.0

        # Extract scores in same order
        scores1 = [rankings1[eid] for eid in common_ids]
        scores2 = [rankings2[eid] for eid in common_ids]

        # Compute correlation
        correlation, _ = spearmanr(scores1, scores2)

        return correlation if not np.isnan(correlation) else 0.0

    def evaluate_strategy(self, strategy: CacheInvalidationStrategy,
                          ground_truth_embeddings: Dict[str, np.ndarray],
                          predicted_drifts: Dict[str, float],
                          modified_entities: Set[str],
                          queries: Dict[str, np.ndarray],
                          threshold: float = 0.02,
                          k_values: List[int] = [5, 10]) -> Dict[str, float]:
        """
        Evaluate a single cache invalidation strategy.

        Args:
            strategy: Cache invalidation strategy to evaluate
            ground_truth_embeddings: Embeddings after full re-indexing
            predicted_drifts: Predicted drift scores
            modified_entities: Set of directly modified entities
            queries: Dictionary mapping query_id to query embedding
            threshold: Drift threshold
            k_values: List of K values for Recall@K

        Returns:
            Dictionary of evaluation metrics
        """
        start_time = time.time()

        # Determine which entities to update
        entities_to_update = strategy.get_entities_to_update(
            modified_entities, predicted_drifts, threshold,
            repo_parser=self.repo_parser
        )

        # Create strategy embeddings (only update selected entities)
        strategy_embeddings = {}
        for entity_id, embedding in ground_truth_embeddings.items():
            if entity_id in entities_to_update:
                strategy_embeddings[entity_id] = embedding
            else:
                # Use old embedding (simulated by not updating)
                old_embedding = self.embedding_manager.get_embedding(entity_id)
                if old_embedding is not None:
                    strategy_embeddings[entity_id] = old_embedding
                else:
                    strategy_embeddings[entity_id] = embedding

        # Compute retrieval metrics
        metrics = {}
        metrics['entities_updated'] = len(entities_to_update)
        metrics['total_entities'] = len(ground_truth_embeddings)
        metrics['update_percentage'] = len(entities_to_update) / len(ground_truth_embeddings) * 100

        # Recall@K for each query
        for k in k_values:
            recall_scores = []
            for query_id, query_embedding in queries.items():
                # Get ground truth top-k
                gt_results = self.embedding_manager.find_similar_entities(
                    query_embedding, ground_truth_embeddings, top_k=k
                )
                gt_ids = [eid for eid, _ in gt_results]

                # Get strategy top-k
                strategy_results = self.embedding_manager.find_similar_entities(
                    query_embedding, strategy_embeddings, top_k=k
                )
                strategy_ids = [eid for eid, _ in strategy_results]

                # Compute recall
                recall = self.compute_recall_at_k(strategy_ids, gt_ids, k=k)
                recall_scores.append(recall)

            metrics[f'recall_at_{k}'] = np.mean(recall_scores)

        # Rank correlation
        # Get full rankings for ground truth and strategy
        gt_rankings = {}
        strategy_rankings = {}

        for query_id, query_embedding in queries.items():
            gt_results = self.embedding_manager.find_similar_entities(
                query_embedding, ground_truth_embeddings, top_k=len(ground_truth_embeddings)
            )
            for rank, (eid, score) in enumerate(gt_results):
                gt_rankings[eid] = gt_rankings.get(eid, 0.0) + score

            strategy_results = self.embedding_manager.find_similar_entities(
                query_embedding, strategy_embeddings, top_k=len(strategy_embeddings)
            )
            for rank, (eid, score) in enumerate(strategy_results):
                strategy_rankings[eid] = strategy_rankings.get(eid, 0.0) + score

        metrics['rank_correlation'] = self.compute_spearman_correlation(
            gt_rankings, strategy_rankings
        )

        # Timing
        end_time = time.time()
        metrics['evaluation_time'] = end_time - start_time

        return metrics

    def evaluate_all_strategies(self,
                                ground_truth_embeddings: Dict[str, np.ndarray],
                                predicted_drifts: Dict[str, float],
                                modified_entities: Set[str],
                                queries: Dict[str, np.ndarray],
                                threshold: float = 0.02,
                                k_values: List[int] = [5, 10],
                                fixed_hop_values: List[int] = [1, 2]) -> Dict[str, Dict[str, float]]:
        """
        Evaluate all cache invalidation strategies.

        Args:
            ground_truth_embeddings: Embeddings after full re-indexing
            predicted_drifts: Predicted drift scores
            modified_entities: Set of directly modified entities
            queries: Dictionary mapping query_id to query embedding
            threshold: Drift threshold
            k_values: List of K values for Recall@K
            fixed_hop_values: List of K values for fixed-hop strategy

        Returns:
            Dictionary mapping strategy name to metrics
        """
        results = {}

        # Baseline A: Changed only
        logger.info("Evaluating Baseline A (Changed Only)...")
        strategy_a = BaselineAChangedOnly()
        results['baseline_a_changed_only'] = self.evaluate_strategy(
            strategy_a, ground_truth_embeddings, predicted_drifts,
            modified_entities, queries, threshold, k_values
        )

        # Baseline B: Full re-indexing
        logger.info("Evaluating Baseline B (Full Re-indexing)...")
        strategy_b = BaselineBFullReindex()
        results['baseline_b_full_reindex'] = self.evaluate_strategy(
            strategy_b, ground_truth_embeddings, predicted_drifts,
            modified_entities, queries, threshold, k_values
        )

        # Baseline C: Fixed-hop
        for k in fixed_hop_values:
            logger.info(f"Evaluating Baseline C (Fixed-Hop K={k})...")
            strategy_c = BaselineCFixedHop(k=k)
            results[f'baseline_c_fixed_hop_k{k}'] = self.evaluate_strategy(
                strategy_c, ground_truth_embeddings, predicted_drifts,
                modified_entities, queries, threshold, k_values
            )

        # Proposed: Predictive
        logger.info("Evaluating Proposed Strategy (Predictive)...")
        strategy_pred = PredictiveStrategy()
        results['proposed_predictive'] = self.evaluate_strategy(
            strategy_pred, ground_truth_embeddings, predicted_drifts,
            modified_entities, queries, threshold, k_values
        )

        return results

    def compute_maintenance_cost(self, strategies_results: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """
        Compute maintenance cost metrics across strategies.

        Args:
            strategies_results: Results from evaluate_all_strategies

        Returns:
            DataFrame with maintenance cost metrics
        """
        cost_data = []

        for strategy_name, metrics in strategies_results.items():
            cost_data.append({
                'strategy': strategy_name,
                'entities_updated': metrics.get('entities_updated', 0),
                'total_entities': metrics.get('total_entities', 0),
                'update_percentage': metrics.get('update_percentage', 0),
                'evaluation_time': metrics.get('evaluation_time', 0)
            })

        return pd.DataFrame(cost_data)

    def compute_pareto_frontier(self, strategies_results: Dict[str, Dict[str, float]],
                                recall_metric: str = 'recall_at_10') -> pd.DataFrame:
        """
        Compute Pareto frontier for trade-off analysis.

        Args:
            strategies_results: Results from evaluate_all_strategies
            recall_metric: Which recall metric to use

        Returns:
            DataFrame with Pareto-optimal strategies
        """
        data = []

        for strategy_name, metrics in strategies_results.items():
            data.append({
                'strategy': strategy_name,
                'recall': metrics[recall_metric],
                'update_percentage': metrics['update_percentage'],
                'entities_updated': metrics['entities_updated']
            })

        df = pd.DataFrame(data)

        # Find Pareto-optimal points (maximize recall, minimize update_percentage)
        pareto_optimal = []

        for i, row in df.iterrows():
            is_pareto = True
            for j, other_row in df.iterrows():
                if i != j:
                    # Check if other dominates this point
                    if (other_row['recall'] >= row['recall'] and
                        other_row['update_percentage'] <= row['update_percentage'] and
                        (other_row['recall'] > row['recall'] or
                         other_row['update_percentage'] < row['update_percentage'])):
                        is_pareto = False
                        break

            if is_pareto:
                pareto_optimal.append(i)

        return df.loc[pareto_optimal].sort_values('update_percentage')
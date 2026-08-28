"""Feature extractor for computing structural and evolution features."""

from typing import Dict, List, Set, Optional, Tuple, TYPE_CHECKING
import numpy as np
import networkx as nx
import pandas as pd
import logging

if TYPE_CHECKING:
    try:
        from core.gtd import GraphTransitionDescriptor
    except ImportError:
        from src.core.gtd import GraphTransitionDescriptor

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extracts features for drift prediction."""

    def __init__(self, repo_parser, git_helper=None, commit_a=None, commit_b=None):
        """
        Initialize feature extractor.

        Args:
            repo_parser: RepoParser or TreeSitterRepoParser instance with dependency graph
            git_helper: GitHelper instance (optional, for caching diff stats)
            commit_a: Earlier commit hash (optional)
            commit_b: Later commit hash (optional)
        """
        self.repo_parser = repo_parser
        self.graph = repo_parser.get_graph()
        self.undirected_graph = self.graph.to_undirected()

        # Precompute structural metrics once per graph/commit
        try:
            self.pagerank = nx.pagerank(self.graph, alpha=0.85)
        except Exception as e:
            logger.warning(f"Failed to compute PageRank: {e}")
            self.pagerank = {}

        try:
            self.closeness = nx.closeness_centrality(self.graph)
        except Exception as e:
            logger.warning(f"Failed to compute closeness centrality: {e}")
            self.closeness = {}

        try:
            self.betweenness = nx.betweenness_centrality(self.graph)
        except Exception as e:
            logger.warning(f"Failed to compute betweenness centrality: {e}")
            self.betweenness = {}

        # Precompute diff stats for all files in this commit pair
        self.diff_stats_cache = {}
        if git_helper and commit_a and commit_b:
            try:
                self.diff_stats_cache = git_helper.get_all_files_diff_stats(commit_a, commit_b)
            except Exception as e:
                logger.warning(f"Failed to precompute file diff stats: {e}")

        # Personalised PageRank impact scores (seeded on modified entities)
        self._ppr_cache: Optional[Dict[str, float]] = None
        self._ppr_seed: Optional[frozenset] = None

    def _get_structural_features(self, entity_id: str) -> Dict[str, float]:
        """Extract structural features from the dependency graph."""
        if entity_id not in self.graph:
            return {
                'out_degree': 0.0,
                'in_degree': 0.0,
                'pagerank': 0.0,
                'closeness': 0.0,
                'betweenness': 0.0
            }

        return {
            'out_degree': float(self.graph.out_degree(entity_id)),
            'in_degree': float(self.graph.in_degree(entity_id)),
            'pagerank': self.pagerank.get(entity_id, 0.0),
            'closeness': self.closeness.get(entity_id, 0.0),
            'betweenness': self.betweenness.get(entity_id, 0.0)
        }

    def _get_evolution_features(self, entity_id: str,
                                modified_entities: Set[str]) -> Dict[str, float]:
        """Extract hop-distance change propagation features."""
        features = {
            'is_modified': 1.0 if entity_id in modified_entities else 0.0,
            'distance_to_modified_directed': 999.0,
            'distance_to_modified_undirected': 999.0,
            'modified_dependents_count': 0.0,
            'modified_dependencies_count': 0.0
        }

        if not modified_entities or entity_id not in self.graph:
            return features

        if entity_id in modified_entities:
            features['distance_to_modified_directed'] = 0.0
            features['distance_to_modified_undirected'] = 0.0
            return features

        try:
            reverse_graph = self.graph.reverse()
            directed_dists = []
            for mod_id in modified_entities:
                if mod_id in reverse_graph:
                    try:
                        d = nx.shortest_path_length(reverse_graph, source=entity_id, target=mod_id)
                        directed_dists.append(d)
                    except nx.NetworkXNoPath:
                        pass
            if directed_dists:
                features['distance_to_modified_directed'] = float(min(directed_dists))
        except Exception as e:
            logger.warning(f"Error computing directed distance for {entity_id}: {e}")

        min_undirected = self.repo_parser.get_nearest_modified_distance(entity_id, modified_entities)
        if min_undirected is not None:
            features['distance_to_modified_undirected'] = float(min_undirected)

        try:
            callers = set(self.graph.predecessors(entity_id))
            features['modified_dependents_count'] = float(len(callers.intersection(modified_entities)))
        except Exception:
            pass

        try:
            callees = set(self.graph.successors(entity_id))
            features['modified_dependencies_count'] = float(len(callees.intersection(modified_entities)))
        except Exception:
            pass

        return features

    def _get_pagerank_impact_feature(self, entity_id: str,
                                     modified_entities: Set[str]) -> Dict[str, float]:
        """Compute Personalised PageRank (PPR) seeded on modified entities."""
        current_seed = frozenset(modified_entities.intersection(self.graph.nodes()))

        if self._ppr_seed != current_seed or self._ppr_cache is None:
            self._ppr_seed = current_seed
            if not current_seed or self.graph.number_of_nodes() == 0:
                self._ppr_cache = {}
            else:
                weight = 1.0 / len(current_seed)
                personalization = {node: (weight if node in current_seed else 0.0)
                                   for node in self.graph.nodes()}
                try:
                    self._ppr_cache = nx.pagerank(self.graph, alpha=0.85, personalization=personalization)
                except Exception as e:
                    logger.warning(f"Failed to compute Personalised PageRank: {e}")
                    self._ppr_cache = {}

        return {'pagerank_impact': self._ppr_cache.get(entity_id, 0.0)}

    def _get_commit_features(self, entity_id: str, commit_a: str, commit_b: str,
                             modified_entities: Set[str], git_helper) -> Dict[str, float]:
        """Extract diff metrics for the file containing entity_id."""
        features = {
            'file_lines_added': 0.0,
            'file_lines_deleted': 0.0,
            'entity_size': 0.0,
            'entity_modification_size': 0.0
        }

        entity = self.repo_parser.get_entity(entity_id)
        if not entity:
            return features

        features['entity_size'] = float(entity.end_lineno - entity.lineno + 1)

        file_path = entity.file_path
        if file_path in self.diff_stats_cache:
            stats = self.diff_stats_cache[file_path]
            features['file_lines_added'] = float(stats['added'])
            features['file_lines_deleted'] = float(stats['deleted'])

        if entity_id in modified_entities and file_path in self.diff_stats_cache:
            features['entity_modification_size'] = float(
                self.diff_stats_cache[file_path]['added'] + self.diff_stats_cache[file_path]['deleted']
            )

        return features

    def _get_historical_features(self, entity_id: str,
                                 modification_history: Dict[str, List[str]],
                                 previous_drifts: Dict[str, float]) -> Dict[str, float]:
        """Extract historical features for an entity."""
        features = {
            'modification_frequency': 0.0,
            'previous_drift': 0.0
        }

        if entity_id in modification_history:
            features['modification_frequency'] = float(len(modification_history[entity_id]))

        if entity_id in previous_drifts:
            features['previous_drift'] = float(previous_drifts[entity_id])

        return features

    def _get_gtd_features(self, entity_id: str, gtd=None) -> Dict[str, float]:
        """Extract Graph Transition Descriptor (GTD) features for entity_id."""
        if gtd is None:
            return {
                "gtd_change_class": 0.0,
                "gtd_local_edges_added": 0.0,
                "gtd_local_edges_removed": 0.0,
                "gtd_local_edge_churn": 0.0,
            }
        return gtd.get_entity_features(entity_id)

    def _get_code_metrics_features(self, entity_id: str, modified_entities: Set[str]) -> Dict[str, float]:
        """Extract native code complexity and topological graph features."""
        is_mod = 1.0 if entity_id in modified_entities else 0.0
        
        # Calculate real topological graph metrics
        data_flow_dist = 10.0
        modified_deps = 0.0
        taint_score = is_mod

        if entity_id in self.graph:
            # Shortest path from any modified entity to entity_id
            min_dist = float('inf')
            for mod_ent in modified_entities:
                if mod_ent in self.graph:
                    try:
                        # Path from mod_ent (source of change) to entity_id (dependent)
                        d = nx.shortest_path_length(self.graph, source=mod_ent, target=entity_id)
                        min_dist = min(min_dist, d)
                        modified_deps += 1.0
                        taint_score = 1.0
                    except nx.NetworkXNoPath:
                        pass
            if min_dist != float('inf'):
                data_flow_dist = float(min_dist)

        if hasattr(self.repo_parser, "get_code_metrics"):
            ts_metrics = self.repo_parser.get_code_metrics(entity_id)
            return {
                "cyclomatic_complexity": ts_metrics.get("cyclomatic_complexity", 1.0),
                "ast_node_count": ts_metrics.get("ast_node_count", 0.0),
                "max_nesting_depth": ts_metrics.get("max_nesting_depth", 0.0),
                "data_flow_distance": data_flow_dist,
                "modified_data_deps_count": modified_deps,
                "taint_reachability_score": taint_score,
            }

        entity = self.repo_parser.get_entity(entity_id)
        if not entity or not entity.source_code:
            return {
                "cyclomatic_complexity": 1.0,
                "ast_node_count": 0.0,
                "max_nesting_depth": 0.0,
                "data_flow_distance": data_flow_dist,
                "modified_data_deps_count": modified_deps,
                "taint_reachability_score": taint_score,
            }

        try:
            import ast
            code = entity.source_code
            tree = ast.parse(code)

            branches = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp)))
            cyclomatic_complexity = float(1 + branches)
            node_count = float(len(list(ast.walk(tree))))

            def _calc_nesting(node, current_depth=0):
                max_d = current_depth
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                        max_d = max(max_d, _calc_nesting(child, current_depth + 1))
                    else:
                        max_d = max(max_d, _calc_nesting(child, current_depth))
                return max_d

            max_depth = float(_calc_nesting(tree))

            return {
                "cyclomatic_complexity": cyclomatic_complexity,
                "ast_node_count": node_count,
                "max_nesting_depth": max_depth,
                "data_flow_distance": data_flow_dist,
                "modified_data_deps_count": modified_deps,
                "taint_reachability_score": taint_score,
            }
        except Exception:
            return {
                "cyclomatic_complexity": 1.0,
                "ast_node_count": 0.0,
                "max_nesting_depth": 0.0,
                "data_flow_distance": data_flow_dist,
                "modified_data_deps_count": modified_deps,
                "taint_reachability_score": taint_score,
            }

    def extract_features(self, entity_id: str, commit_a: str, commit_b: str,
                         modified_entities: Set[str],
                         modification_history: Dict[str, List[str]],
                         previous_drifts: Dict[str, float],
                         git_helper,
                         gtd=None) -> Dict[str, float]:
        """Extract all features for an entity."""
        features = {}
        features.update(self._get_structural_features(entity_id))
        features.update(self._get_evolution_features(entity_id, modified_entities))
        features.update(self._get_pagerank_impact_feature(entity_id, modified_entities))
        features.update(self._get_commit_features(entity_id, commit_a, commit_b, modified_entities, git_helper))
        features.update(self._get_historical_features(entity_id, modification_history, previous_drifts))
        features.update(self._get_gtd_features(entity_id, gtd))
        features.update(self._get_code_metrics_features(entity_id, modified_entities))
        return features

    def extract_features_batch(self, entity_ids: List[str], commit_a: str, commit_b: str,
                               modified_entities: Set[str],
                               modification_history: Dict[str, List[str]],
                               previous_drifts: Dict[str, float],
                               git_helper,
                               gtd=None) -> pd.DataFrame:
        """Extract features for multiple entities."""
        # Retrieve or compute fallback global GTD features
        if gtd is not None and hasattr(gtd, "get_global_features"):
            global_feats = gtd.get_global_features()
        else:
            try:
                from core.gtd import GraphTransitionDescriptor
            except ImportError:
                from src.core.gtd import GraphTransitionDescriptor
            dummy = GraphTransitionDescriptor()
            dummy.compute(nx.DiGraph(), nx.DiGraph(), {})
            global_feats = {k: 0.0 for k in dummy.get_global_features()}

        features_list = []

        for entity_id in entity_ids:
            features = self.extract_features(
                entity_id, commit_a, commit_b, modified_entities,
                modification_history, previous_drifts, git_helper, gtd=gtd
            )
            if global_feats:
                features.update(global_feats)
            features['entity_id'] = entity_id
            features_list.append(features)

        df = pd.DataFrame(features_list)
        df.set_index('entity_id', inplace=True)
        return df

    def update_modification_history(self, entity_id: str, commit_hash: str,
                                    modification_history: Dict[str, List[str]]) -> None:
        """Update modification history for an entity."""
        if entity_id not in modification_history:
            modification_history[entity_id] = []
        modification_history[entity_id].append(commit_hash)
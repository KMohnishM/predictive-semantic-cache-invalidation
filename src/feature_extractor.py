"""Feature extractor for computing structural and evolution features."""

from typing import Dict, List, Set, Optional, Tuple
import numpy as np
import networkx as nx
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extracts features for drift prediction."""

    def __init__(self, repo_parser, git_helper=None, commit_a=None, commit_b=None):
        """
        Initialize feature extractor.

        Args:
            repo_parser: RepoParser instance with dependency graph
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

    def _get_structural_features(self, entity_id: str) -> Dict[str, float]:
        """
        Extract structural features from the dependency graph.

        Args:
            entity_id: Entity identifier

        Returns:
            Dictionary of structural features
        """
        features = {}

        if entity_id not in self.graph:
            return {
                'out_degree': 0.0,
                'in_degree': 0.0,
                'pagerank': 0.0,
                'closeness': 0.0,
                'betweenness': 0.0
            }

        # Degree features
        features['out_degree'] = float(self.graph.out_degree(entity_id))
        features['in_degree'] = float(self.graph.in_degree(entity_id))

        # Centrality features (precomputed)
        features['pagerank'] = self.pagerank.get(entity_id, 0.0)
        features['closeness'] = self.closeness.get(entity_id, 0.0)
        features['betweenness'] = self.betweenness.get(entity_id, 0.0)

        return features

    def _get_evolution_features(self, entity_id: str,
                                modified_entities: Set[str]) -> Dict[str, float]:
        """
        Extract evolution and propagation features.

        Args:
            entity_id: Entity identifier
            modified_entities: Set of directly modified entity IDs

        Returns:
            Dictionary of evolution features
        """
        features = {}

        # Check if entity exists in graph
        if entity_id not in self.graph:
            return {
                'distance_to_modified_directed': -1.0,
                'distance_to_modified_undirected': -1.0,
                'modified_dependents_count': 0.0,
                'modified_dependencies_count': 0.0
            }

        # Find minimum distance to any modified node
        min_directed_distance = None
        min_undirected_distance = None

        for modified_id in modified_entities:
            # Skip if modified entity not in graph
            if modified_id not in self.graph:
                continue

            # Directed distance (downstream)
            try:
                dist = nx.shortest_path_length(self.graph, entity_id, modified_id)
                if min_directed_distance is None or dist < min_directed_distance:
                    min_directed_distance = dist
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

            # Undirected distance
            try:
                dist = nx.shortest_path_length(self.undirected_graph, entity_id, modified_id)
                if min_undirected_distance is None or dist < min_undirected_distance:
                    min_undirected_distance = dist
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        features['distance_to_modified_directed'] = float(min_directed_distance) if min_directed_distance is not None else -1.0
        features['distance_to_modified_undirected'] = float(min_undirected_distance) if min_undirected_distance is not None else -1.0

        # Number of directly modified nodes in transitive dependents
        try:
            dependents = self.repo_parser.get_dependents(entity_id)
            modified_dependents = dependents & modified_entities
            features['modified_dependents_count'] = float(len(modified_dependents))
        except Exception:
            features['modified_dependents_count'] = 0.0

        # Number of directly modified nodes in transitive dependencies
        try:
            dependencies = self.repo_parser.get_dependencies(entity_id)
            modified_dependencies = dependencies & modified_entities
            features['modified_dependencies_count'] = float(len(modified_dependencies))
        except Exception:
            features['modified_dependencies_count'] = 0.0

        return features

    def _get_commit_features(self, entity_id: str, commit_a: str, commit_b: str,
                             modified_entities: Set[str], git_helper) -> Dict[str, float]:
        """
        Extract commit-related features.

        Args:
            entity_id: Entity identifier
            commit_a: Earlier commit hash
            commit_b: Later commit hash
            modified_entities: Set of directly modified entity IDs
            git_helper: GitHelper instance

        Returns:
            Dictionary of commit features
        """
        features = {}

        entity = self.repo_parser.get_entity(entity_id)
        if not entity:
            return {
                'file_lines_added': 0.0,
                'file_lines_deleted': 0.0,
                'entity_size': 0.0,
                'entity_modification_size': 0.0
            }

        # File-level changes (using cached diff stats)
        diff_stats = self.diff_stats_cache.get(entity.file_path, {"added": 0.0, "deleted": 0.0})
        features['file_lines_added'] = float(diff_stats['added'])
        features['file_lines_deleted'] = float(diff_stats['deleted'])

        # Entity size
        features['entity_size'] = float(len(entity.source_code))

        # Entity modification size (if directly modified)
        if entity_id in modified_entities:
            # Get old version of entity
            old_source = git_helper.get_file_content_at_commit(commit_a, entity.file_path)
            if old_source:
                try:
                    import ast
                    old_tree = ast.parse(old_source)
                    # Parse entity parts to match class scope
                    parts = entity_id.split('::')
                    class_name = parts[1] if len(parts) == 3 else None
                    func_name = parts[-1]

                    target_node = None
                    if class_name:
                        # Find the class first
                        for node in old_tree.body:
                            if isinstance(node, ast.ClassDef) and node.name == class_name:
                                # Find the method inside the class
                                for subnode in node.body:
                                    if isinstance(subnode, ast.FunctionDef) and subnode.name == func_name:
                                        target_node = subnode
                                        break
                                break
                    else:
                        # Find top-level function
                        for node in old_tree.body:
                            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                                target_node = node
                                break

                    if target_node:
                        old_lines = old_source.split('\n')
                        start = target_node.lineno - 1
                        end = target_node.end_lineno if hasattr(target_node, 'end_lineno') else start + 1
                        old_entity_source = "\n".join(old_lines[start:end])
                        features['entity_modification_size'] = float(
                            abs(len(entity.source_code) - len(old_entity_source))
                        )
                    else:
                        features['entity_modification_size'] = 0.0
                except Exception:
                    features['entity_modification_size'] = 0.0
            else:
                features['entity_modification_size'] = 0.0
        else:
            features['entity_modification_size'] = 0.0

        return features

    def _get_historical_features(self, entity_id: str,
                                  modification_history: Dict[str, List[str]],
                                  previous_drifts: Dict[str, float]) -> Dict[str, float]:
        """
        Extract historical features.

        Args:
            entity_id: Entity identifier
            modification_history: Dictionary mapping entity_id to list of commit hashes
            previous_drifts: Dictionary mapping entity_id to previous drift values

        Returns:
            Dictionary of historical features
        """
        features = {}

        # Modification frequency (volatility)
        mod_count = len(modification_history.get(entity_id, []))
        features['modification_frequency'] = float(mod_count)

        # Previous drift
        features['previous_drift'] = previous_drifts.get(entity_id, 0.0)

        return features

    def extract_features(self, entity_id: str, commit_a: str, commit_b: str,
                         modified_entities: Set[str],
                         modification_history: Dict[str, List[str]],
                         previous_drifts: Dict[str, float],
                         git_helper) -> Dict[str, float]:
        """
        Extract all features for an entity.

        Args:
            entity_id: Entity identifier
            commit_a: Earlier commit hash
            commit_b: Later commit hash
            modified_entities: Set of directly modified entity IDs
            modification_history: Historical modification data
            previous_drifts: Previous drift values
            git_helper: GitHelper instance

        Returns:
            Dictionary of all features
        """
        features = {}

        # Structural features
        features.update(self._get_structural_features(entity_id))

        # Evolution features
        features.update(self._get_evolution_features(entity_id, modified_entities))

        # Commit features
        features.update(self._get_commit_features(entity_id, commit_a, commit_b, modified_entities, git_helper))

        # Historical features
        features.update(self._get_historical_features(
            entity_id, modification_history, previous_drifts
        ))

        return features

    def extract_features_batch(self, entity_ids: List[str], commit_a: str, commit_b: str,
                               modified_entities: Set[str],
                               modification_history: Dict[str, List[str]],
                               previous_drifts: Dict[str, float],
                               git_helper) -> pd.DataFrame:
        """
        Extract features for multiple entities.

        Args:
            entity_ids: List of entity identifiers
            commit_a: Earlier commit hash
            commit_b: Later commit hash
            modified_entities: Set of directly modified entity IDs
            modification_history: Historical modification data
            previous_drifts: Previous drift values
            git_helper: GitHelper instance

        Returns:
            DataFrame with features for all entities
        """
        features_list = []

        for entity_id in entity_ids:
            features = self.extract_features(
                entity_id, commit_a, commit_b, modified_entities,
                modification_history, previous_drifts, git_helper
            )
            features['entity_id'] = entity_id
            features_list.append(features)

        df = pd.DataFrame(features_list)
        df.set_index('entity_id', inplace=True)

        return df

    def update_modification_history(self, entity_id: str, commit_hash: str,
                                    modification_history: Dict[str, List[str]]) -> None:
        """
        Update modification history for an entity.

        Args:
            entity_id: Entity identifier
            commit_hash: Commit hash
            modification_history: Historical modification data (modified in place)
        """
        if entity_id not in modification_history:
            modification_history[entity_id] = []

        modification_history[entity_id].append(commit_hash)
"""LlamaIndex integration module for predictive semantic cache invalidation.

Provides:
- CodeGraphNodeParser: Custom LlamaIndex NodeParser extracting AST entities and
  embedding call-graph relationships (callers/callees) into node metadata.
- PredictiveCacheFilter: Custom LlamaIndex TransformComponent acting as an ingestion
  filter that evaluates code nodes through the trained DriftPredictor ML model,
  routing only stale nodes for re-embedding while preserving fresh cached nodes.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Union, Any
import logging

import pandas as pd
import numpy as np

from ..parser.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
from ..extractor.feature_extractor import FeatureExtractor
from ..predictor.predictor import DriftPredictor, positive_class_proba

logger = logging.getLogger(__name__)

# Check if llama_index is available
try:
    from llama_index.core.node_parser import BaseNodeParser
    from llama_index.core.schema import BaseNode, TextNode, TransformComponent, NodeRelationship, RelatedNodeInfo
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False

    # Standalone drop-in mock implementation for environments without llama-index installed
    class BaseNode:
        """Fallback BaseNode representation when llama-index is not installed."""
        def __init__(self, id_: Optional[str] = None, text: str = "", metadata: Optional[Dict[str, Any]] = None, **kwargs):
            self.id_ = id_ or kwargs.get("id", "")
            self.text = text
            self.metadata = metadata or {}
            self.relationships: Dict[str, Any] = {}

        def __repr__(self) -> str:
            return f"TextNode(id_={self.id_!r}, metadata={self.metadata!r})"

    class TextNode(BaseNode):
        """Fallback TextNode representation when llama-index is not installed."""
        pass

    class BaseNodeParser:
        """Fallback BaseNodeParser representation when llama-index is not installed."""
        def __init__(self, **kwargs):
            pass

        def get_nodes_from_documents(self, documents: Sequence[Any], **kwargs) -> Sequence[BaseNode]:
            return self._parse_nodes(documents, **kwargs)

        def _parse_nodes(self, nodes: Sequence[Any], show_progress: bool = False, **kwargs) -> Sequence[BaseNode]:
            raise NotImplementedError

    class TransformComponent:
        """Fallback TransformComponent representation when llama-index is not installed."""
        def __init__(self, **kwargs):
            pass

        def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
            raise NotImplementedError


# =========================================================================
# 1. Custom LlamaIndex CodeGraph Node Parser
# =========================================================================
class CodeGraphNodeParser(BaseNodeParser):
    """
    Custom LlamaIndex Node Parser.
    Parses a codebase using TreeSitterRepoParser and creates LlamaIndex TextNodes
    with call-graph callers/callees relationships attached as metadata.
    """

    def __init__(self, repo_path: str, **kwargs):
        super().__init__(**kwargs)
        self.repo_path = os.path.abspath(repo_path)
        self.repo_parser = TreeSitterRepoParser(self.repo_path)

    def parse_repository(self) -> List[TextNode]:
        """Directly parses the repository and returns call-graph TextNodes."""
        logger.info(f"[CodeGraphNodeParser] Analyzing codebase structure at {self.repo_path}...")
        self.repo_parser.parse_directory(self.repo_path)
        G = self.repo_parser.get_graph()

        cpg_nodes: List[TextNode] = []
        for entity_id, entity in self.repo_parser.entities.items():
            callers = list(G.predecessors(entity_id)) if entity_id in G else []
            callees = list(G.successors(entity_id)) if entity_id in G else []

            metadata = {
                "file_path": entity.file_path,
                "entity_type": entity.entity_type,
                "lineno": entity.lineno,
                "end_lineno": entity.end_lineno,
                "callers": callers,
                "callees": callees,
                "cpg_id": entity_id,
            }

            node = TextNode(
                text=entity.source_code,
                id_=entity_id,
                metadata=metadata,
            )

            if LLAMA_INDEX_AVAILABLE:
                # Optionally link parent/child relations in LlamaIndex schema
                try:
                    rel_map = {}
                    if callers:
                        rel_map[NodeRelationship.PARENT] = [
                            RelatedNodeInfo(node_id=c) for c in callers
                        ]
                    if callees:
                        rel_map[NodeRelationship.CHILD] = [
                            RelatedNodeInfo(node_id=c) for c in callees
                        ]
                    node.relationships = rel_map
                except Exception as e:
                    logger.debug(f"Could not attach formal NodeRelationships: {e}")

            cpg_nodes.append(node)

        logger.info(f"[CodeGraphNodeParser] Extracted {len(cpg_nodes)} call-graph nodes.")
        return cpg_nodes

    def _parse_nodes(self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs) -> Sequence[BaseNode]:
        """Parses source documents into call-graph aware TextNodes."""
        return self.parse_repository()


# =========================================================================
# 2. Custom LlamaIndex Predictive Invalidation Filter
# =========================================================================
class PredictiveCacheFilter(TransformComponent):
    """
    Custom LlamaIndex Ingestion Transformation.
    Filters the incoming sequence of nodes, retaining only those predicted
    stale by the DriftPredictor model for re-embedding.
    """

    def __init__(
        self,
        predictor_or_path: Union[str, Path, DriftPredictor],
        repo_parser: TreeSitterRepoParser,
        modified_entities: Optional[Set[str]] = None,
        threshold: Optional[float] = None,
        previous_parser: Optional[TreeSitterRepoParser] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.repo_parser = repo_parser
        # Parser for the previously indexed commit. Required for the
        # call-graph-context features (own_source_changed,
        # context_stub_changed_count, modified_member_count); without it they
        # are all 0 and recall drops (about 87% vs 100% on psf/black test pairs).
        self.previous_parser = previous_parser
        self.modified_entities = set(modified_entities or [])
        self.threshold = threshold

        if isinstance(predictor_or_path, (str, Path)):
            self.model_path = os.path.abspath(str(predictor_or_path))
            self.predictor = DriftPredictor.load_artifact(self.model_path)
        elif isinstance(predictor_or_path, DriftPredictor):
            self.model_path = None
            self.predictor = predictor_or_path
        else:
            raise TypeError(f"Expected model path or DriftPredictor instance, got {type(predictor_or_path)}")

    def set_modified_entities(self, modified_entities: Set[str]) -> None:
        """Update the set of modified entities for a new commit cycle."""
        self.modified_entities = set(modified_entities)

    def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        """
        Filters incoming nodes, returning only the subset requiring re-embedding.
        Fresh nodes bypass neural re-embedding entirely.
        """
        if not nodes:
            return []

        logger.info(f"[PredictiveCacheFilter] Scanning {len(nodes)} nodes for semantic cache drifts...")

        if self.previous_parser is None:
            logger.warning(
                "[PredictiveCacheFilter] No previous_parser supplied: call-graph-context "
                "features will be zero and recall will be lower. Pass the parser of the "
                "previously indexed commit."
            )
        extractor = FeatureExtractor(self.repo_parser, parser_a=self.previous_parser)

        features: Dict[str, Dict[str, float]] = {}
        for node in nodes:
            entity_id = getattr(node, "id_", None) or getattr(node, "id", "")
            cpg_id = node.metadata.get("cpg_id", entity_id) if hasattr(node, "metadata") else entity_id
            feats = extractor.extract_features(cpg_id, modified_entities=self.modified_entities)
            features[entity_id] = feats

        features_df = pd.DataFrame.from_dict(features, orient="index")

        # Align feature columns with predictor training schema if available
        if hasattr(self.predictor, "feature_names") and self.predictor.feature_names:
            features_df = features_df.reindex(columns=self.predictor.feature_names, fill_value=0.0)

        X = features_df.values

        # Predict drift probabilities / decision scores
        if hasattr(self.predictor, "predict_proba"):
            raw_probs = self.predictor.predict_proba(X)
            if raw_probs is not None:
                probabilities = positive_class_proba(getattr(self.predictor, "model", None), raw_probs)
            else:
                probabilities = self.predictor.predict(X)
        elif hasattr(self.predictor, "predict"):
            probabilities = self.predictor.predict(X)
        else:
            raise RuntimeError("Predictor does not support predict_proba or predict")

        effective_threshold = (
            self.threshold
            if self.threshold is not None
            else getattr(self.predictor, "decision_threshold", 0.5)
        )

        dirty_nodes: List[BaseNode] = []
        for node, prob in zip(nodes, probabilities):
            entity_id = getattr(node, "id_", None) or getattr(node, "id", "")
            # Node is dirty if directly modified or predicted stale
            if entity_id in self.modified_entities or prob >= effective_threshold:
                dirty_nodes.append(node)

        logger.info(
            f"[PredictiveCacheFilter] Cache Invalidation: {len(nodes)} total -> "
            f"{len(dirty_nodes)} marked stale (re-embed), {len(nodes) - len(dirty_nodes)} cached fresh."
        )
        return dirty_nodes


# =========================================================================
# 3. Convenience Pipeline Builder
# =========================================================================
def build_predictive_ingestion_pipeline(
    repo_path: str,
    predictor_or_path: Union[str, Path, DriftPredictor],
    modified_entities: Optional[Set[str]] = None,
    threshold: Optional[float] = None,
    previous_parser: Optional[TreeSitterRepoParser] = None,
) -> Dict[str, Any]:
    """
    Constructs the pair of CodeGraphNodeParser and PredictiveCacheFilter
    configured for the specified repository.
    """
    node_parser = CodeGraphNodeParser(repo_path=repo_path)
    cache_filter = PredictiveCacheFilter(
        predictor_or_path=predictor_or_path,
        repo_parser=node_parser.repo_parser,
        modified_entities=modified_entities,
        threshold=threshold,
        previous_parser=previous_parser,
    )
    return {
        "node_parser": node_parser,
        "cache_filter": cache_filter,
    }

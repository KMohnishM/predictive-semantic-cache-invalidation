import os
import sys
import pickle
import pandas as pd
from typing import List, Sequence, Set, Dict

# Check if llama_index is available
try:
    from llama_index.core.node_parser import BaseNodeParser
    from llama_index.core.schema import BaseNode, TextNode, TransformComponent
except ImportError:
    # Fallback placeholders if not installed yet (to allow file creation)
    class BaseNodeParser: pass
    class TransformComponent: pass
    class BaseNode: pass
    class TextNode: pass

from repo_parser import RepoParser
from feature_extractor import FeatureExtractor

# =========================================================================
# 1. Custom LlamaIndex CodeGraph Node Parser
# =========================================================================
class CodeGraphNodeParser(BaseNodeParser):
    """
    Custom LlamaIndex Node Parser.
    Parses a codebase using RepoParser and creates LlamaIndex TextNodes
    with call-graph callers/callees relationships attached as metadata.
    """
    def __init__(self, repo_path: str, **kwargs):
        # BaseNodeParser inherits from Pydantic BaseModel in LlamaIndex
        super().__init__(**kwargs)
        self.repo_path = os.path.abspath(repo_path)
        self.repo_parser = RepoParser(self.repo_path)
        
    def _parse_nodes(self, nodes: Sequence[BaseNode], show_progress: bool = False) -> Sequence[BaseNode]:
        """Parses source documents into call-graph aware TextNodes."""
        # 1. Run RepoParser to construct the call graph
        print(f"[CodeGraphNodeParser] Analyzing codebase structure at {self.repo_path}...")
        self.repo_parser.parse_directory(self.repo_path)
        G = self.repo_parser.get_graph()
        
        cpg_nodes = []
        
        # 2. Convert RepoParser entities to LlamaIndex TextNode objects
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
                "cpg_id": entity_id
            }
            
            # Create the actual LlamaIndex TextNode
            node = TextNode(
                text=entity.source_code,
                id_=entity_id,
                metadata=metadata
            )
            cpg_nodes.append(node)
            
        print(f"[CodeGraphNodeParser] Extracted {len(cpg_nodes)} call-graph nodes.")
        return cpg_nodes

# =========================================================================
# 2. Custom LlamaIndex Predictive Invalidation Filter
# =========================================================================
class PredictiveCacheFilter(TransformComponent):
    """
    Custom LlamaIndex Ingestion Transformation.
    Filters the incoming sequence of nodes, retaining only those predicted
    stale by the DriftPredictor Random Forest model.
    """
    def __init__(self, model_path: str, repo_parser: RepoParser, modified_entities: Set[str], **kwargs):
        super().__init__(**kwargs)
        self.model_path = os.path.abspath(model_path)
        self.repo_parser = repo_parser
        self.modified_entities = modified_entities
        
        # Load pre-trained classifier
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)

    def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
        """Filters out fresh nodes, returning only the nodes requiring re-embedding."""
        if not nodes:
            return []
            
        print(f"[PredictiveCacheFilter] Scanning {len(nodes)} nodes for semantic cache drifts...")
        
        # 1. Initialize FeatureExtractor with current call graph
        extractor = FeatureExtractor(self.repo_parser)
        
        # 2. Extract 25 features for all nodes relative to the git changes
        features = {}
        for node in nodes:
            entity_id = node.id_
            # Use metadata or ID to identify node in graph
            cpg_id = node.metadata.get("cpg_id", entity_id)
            feats = extractor.extract_features(cpg_id, self.modified_entities)
            features[entity_id] = feats
            
        features_df = pd.DataFrame.from_dict(features, orient='index')
        X = features_df.values
        
        # 3. Predict drift probabilities using Random Forest
        probabilities = self.model.predict_proba(X)[:, 1] if hasattr(self.model, "predict_proba") else self.model.predict(X)
        
        # 4. Filter nodes
        dirty_nodes = []
        for idx, (node, prob) in enumerate(zip(nodes, probabilities)):
            entity_id = node.id_
            # Node is dirty if directly modified or predicted stale (prob >= 50%)
            if entity_id in self.modified_entities or prob >= 0.5:
                dirty_nodes.append(node)
                
        print(f"[PredictiveCacheFilter] Cache Invalidation Filter: {len(nodes)} -> {len(dirty_nodes)} nodes selected for re-embedding.")
        return dirty_nodes

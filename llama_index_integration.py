"""LlamaIndex integration module for predictive semantic cache invalidation.

(Backward-compatibility module; re-exports from predictive_semantic_cache.integrations.llama_index)
"""

import sys
import types
from pathlib import Path

# Ensure src/ is on sys.path if not installed
_src_path = str(Path(__file__).resolve().parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import predictive_semantic_cache.integrations.llama_index as _orig_mod
from predictive_semantic_cache.integrations.llama_index import (
    CodeGraphNodeParser,
    PredictiveCacheFilter,
    build_predictive_ingestion_pipeline,
    BaseNode,
    TextNode,
    LLAMA_INDEX_AVAILABLE,
    FeatureExtractor,
    TreeSitterRepoParser,
    Entity,
    DriftPredictor,
    positive_class_proba,
)

class _CompatibilityModule(types.ModuleType):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if hasattr(_orig_mod, name):
            setattr(_orig_mod, name, value)

sys.modules[__name__].__class__ = _CompatibilityModule

__all__ = [
    "CodeGraphNodeParser",
    "PredictiveCacheFilter",
    "build_predictive_ingestion_pipeline",
    "BaseNode",
    "TextNode",
    "LLAMA_INDEX_AVAILABLE",
    "FeatureExtractor",
    "TreeSitterRepoParser",
    "Entity",
    "DriftPredictor",
    "positive_class_proba",
]

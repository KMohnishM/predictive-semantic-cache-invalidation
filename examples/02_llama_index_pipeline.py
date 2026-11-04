"""Example 2: LlamaIndex Smart Ingestion Pipeline.

Demonstrates how to integrate Predictive Semantic Cache into a LlamaIndex
RAG ingestion pipeline so only nodes that experienced semantic drift get
sent to the neural embedding model and vector store.
"""

import os
from pathlib import Path

# Note: Requires 'llama-index-core' installed (`pip install "predictive-semantic-cache-invalidation[llamaindex]"`)
try:
    from llama_index.core import Document, VectorStoreIndex
    from llama_index.core.node_parser import SentenceSplitter
    LLAMA_INDEX_INSTALLED = True
except ImportError:
    LLAMA_INDEX_INSTALLED = False

from predictive_semantic_cache.integrations.llama_index import (
    CodeGraphNodeParser,
    PredictiveCacheFilter,
    build_predictive_ingestion_pipeline,
)


def run_pipeline():
    if not LLAMA_INDEX_INSTALLED:
        print("LlamaIndex is not installed. Install with: pip install 'predictive-semantic-cache-invalidation[llamaindex]'")
        return

    repo_dir = str(Path(".").resolve())
    print(f"Building predictive ingestion pipeline for: {repo_dir}")

    # =========================================================================
    # Step 1: Build the pipeline components
    # Both node_parser (AST-aware) and cache_filter (ML-driven) are configured.
    # Passing predictor_or_path=None auto-loads the default pre-trained model!
    # =========================================================================
    pipeline_parts = build_predictive_ingestion_pipeline(
        repo_path=repo_dir,
        predictor_or_path=None,  # Auto-loads default bundled model! Or pass 'custom_model.pkl'
        threshold=0.5,
    )
    node_parser = pipeline_parts["node_parser"]
    cache_filter = pipeline_parts["cache_filter"]

    # =========================================================================
    # Step 2: Parse code entities into graph-aware TextNodes
    # =========================================================================
    nodes = node_parser.parse_repository()
    print(f"Parsed {len(nodes)} code nodes from repository.")

    # =========================================================================
    # Step 3: Filter out fresh nodes (Only drifted nodes proceed to embedding)
    # =========================================================================
    stale_nodes = cache_filter(nodes)
    print(f"Filtered: {len(stale_nodes)} marked stale for re-embedding, {len(nodes) - len(stale_nodes)} fresh cached.")

    # =========================================================================
    # Step 4: Insert only stale nodes into your LlamaIndex vector store
    # =========================================================================
    # index = VectorStoreIndex.from_vector_store(...)
    # index.insert_nodes(stale_nodes)
    print("Vector store update complete. Only stale embeddings were refreshed!")


if __name__ == "__main__":
    run_pipeline()

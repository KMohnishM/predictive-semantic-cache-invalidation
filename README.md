# Predictive Semantic Cache Invalidation (`predictive-semantic-cache`)

[![PyPI Version](https://img.shields.io/pypi/v/predictive-semantic-cache.svg)](https://pypi.org/project/predictive-semantic-cache/)
[![Python Versions](https://img.shields.io/pypi/pyversions/predictive-semantic-cache.svg)](https://pypi.org/project/predictive-semantic-cache/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Predictive Semantic Cache Invalidation** is an intelligent caching and re-indexing framework for Retrieval-Augmented Generation (RAG) and semantic code search systems.

When codebases evolve across Git commits, naively re-embedding every entity or file incurs prohibitive LLM and embedding API costs. Conversely, re-embedding only directly touched files ignores ripple effects in dependent call graphs. `predictive-semantic-cache` solves this by using **Tree-Sitter AST call graphs**, **structural drift feature extraction**, and **calibrated machine learning** (LightGBM, Random Forest, HistGradientBoosting) to predict which code entities' semantic representations have drifted enough to require cache invalidation.

---

## Key Features

- 🌲 **Tree-Sitter AST & Call-Graph Parser**: Multi-language parsing of classes, methods, functions, and call relationships without requiring full compiler environments.
- 📐 **Graph & Evolution Feature Extraction**: Computes structural metrics (centrality, degree, depth), evolutionary stats (churn, diff size, modification frequency), and Graph Transition Descriptors (GTD).
- 🤖 **ML Drift Prediction**: Supports LightGBM, Random Forest, HistGradientBoosting, and ExtraTrees with recall-calibrated decision thresholds to ensure stale entities are never missed.
- 🦙 **Drop-in LlamaIndex Integration**: Custom `CodeGraphNodeParser` and `PredictiveCacheFilter` transformation components that fit directly into standard LlamaIndex ingestion pipelines.
- 📊 **Comprehensive Benchmarking Suite**: CLI and reporting utilities to evaluate retrieval retention vs. full re-indexing and update cost.

---

## Installation

### Core (Lightweight)
```bash
pip install predictive-semantic-cache
```

### With LlamaIndex Integration
```bash
pip install "predictive-semantic-cache[llamaindex]"
```

### With LightGBM Support
```bash
pip install "predictive-semantic-cache[lightgbm]"
```

### All Dependencies (Benchmarking, Evaluation & Embeddings)
```bash
pip install "predictive-semantic-cache[all]"
```

---

## Quickstart

### 1. LlamaIndex Ingestion Pipeline

Integrate predictive cache invalidation directly into your LlamaIndex ingestion flow:

```python
from predictive_semantic_cache import (
    CodeGraphNodeParser,
    PredictiveCacheFilter,
    DriftPredictor,
)
from llama_index.core import Document
from llama_index.core.ingestion import IngestionPipeline

# 1. Parse repository into call-graph-aware nodes
node_parser = CodeGraphNodeParser(repo_path="./my-repo")
nodes = node_parser.parse_repository()

# 2. Load trained drift predictor
predictor = DriftPredictor.load_artifact("path/to/drift_predictor.pkl")

# 3. Create cache filter that retains only drifted nodes for re-embedding
cache_filter = PredictiveCacheFilter(
    predictor_or_path=predictor,
    repo_parser=node_parser.repo_parser,
    modified_entities={"my_module::MyClass::modified_method"},
)

# 4. Pipeline routes only stale nodes to the embedding model
pipeline = IngestionPipeline(
    transformations=[cache_filter]
)
nodes_to_reembed = pipeline.run(nodes=nodes)
print(f"Total nodes: {len(nodes)} -> Re-embedding only: {len(nodes_to_reembed)}")
```

---

### 2. Standalone Code Graph & AST Parsing

```python
from predictive_semantic_cache import TreeSitterRepoParser

# Initialize parser on a target repository
parser = TreeSitterRepoParser(repo_path="./my-repo")
parser.parse_directory("./my-repo")

# Access extracted entities (classes, functions, methods)
for entity_id, entity in parser.entities.items():
    print(f"Entity: {entity_id} ({entity.entity_type}) at {entity.file_path}:{entity.lineno}")

# Query caller/callee relationships
graph = parser.get_graph()
callers = list(graph.predecessors("my_module::func_a"))
callees = list(graph.successors("my_module::func_a"))
```

---

### 3. Extract Features and Predict Drift

```python
from predictive_semantic_cache import FeatureExtractor, DriftPredictor

# Extract structural and evolutionary features
extractor = FeatureExtractor(repo_parser=parser, parser_a=previous_parser)
features = extractor.extract_features(
    entity_id="my_module::func_a",
    modified_entities={"my_module::func_b"}
)

# Load predictor and evaluate drift
predictor = DriftPredictor.load_artifact("drift_predictor.pkl")
is_stale = predictor.predict([list(features.values())])[0]
print(f"Should invalidate cache: {bool(is_stale)}")
```

---

## Benchmarking CLI

The package bundles a reproducible retrieval benchmark CLI to measure staleness cost and retrieval fidelity (Lost@k, MRR, NDCG):

```bash
predictive-cache-benchmark --repo-path ./my-repo --num-commits 10 --strategies predictive_ml,changed_only,full_reindex
```

---

## Publishing to PyPI

To build and publish a new version:

```bash
# 1. Install build tools
pip install build twine

# 2. Build distribution packages
python -m build

# 3. Check distribution packages
twine check dist/*

# 4. Upload to TestPyPI (optional verification)
twine upload --repository testpypi dist/*

# 5. Upload to Production PyPI
twine upload dist/*
```

---

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

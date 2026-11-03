# API Reference Overview

This section contains the comprehensive API reference for all public classes, methods, and functions in `predictive-semantic-cache`.

## Core Modules

| Module | Description | Key Classes / Functions |
| :--- | :--- | :--- |
| [**Client Facade**](client.md) | High-level 5-line invalidation client | `PredictiveCache` |
| [**Code Parser**](parser.md) | Tree-Sitter AST & Git history parsing | `TreeSitterRepoParser`, `Entity`, `GitHelper` |
| [**Feature Extractor**](extractor.md) | Graph & evolutionary feature extraction | `FeatureExtractor`, `GraphTransitionDescriptor`, `RepositoryStateDescriptor` |
| [**ML Drift Predictor**](predictor.md) | Machine learning models & temporal splitting | `DriftPredictor`, `positive_class_proba`, `train_test_split_temporal` |
| [**Framework Integrations**](integrations.md) | LlamaIndex & Vector DB pipeline connectors | `CodeGraphNodeParser`, `PredictiveCacheFilter`, `build_predictive_ingestion_pipeline` |
| [**Embedding & Context**](embedder.md) | Contextual chunking & ground truth | `build_contextual_source`, `load_ground_truth_queries` |
| [**Evaluator & Baselines**](evaluator.md) | Cache retention & retrieval metrics | `Evaluator`, `BaselineAChangedOnly`, `BaselineCFixedHop` |
| [**Benchmarking Suite**](benchmarking.md) | Reproducible benchmarking engine | `run_benchmark`, `BenchmarkConfig`, `ModelRunner` |

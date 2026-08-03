# Predictive Semantic Cache Invalidation - Pipeline Run-Book

This document provides a detailed setup and execution guide for the **Predictive Semantic Cache Invalidation** pipeline and the standalone **Retrieval Quality Benchmarking** pipeline.

---

## 1. Overall System Architecture & Workflow

Here is the complete end-to-end data flow showing how both pipelines interact:

```mermaid
flowchart TD
    A["Git Repository Evolution (C_t -> C_t+1)"] --> B[Joern CPG Server]
    
    subgraph "Pipeline 1: Model Training & Invalidation (run_experiment.py)"
    B -->|"JoernRepoParser"| C[Extract Call Graph G]
    B -->|"CFG + PDG Features"| D[FeatureExtractor]
    D -->|"25 Tabular Features"| E[Random Forest Classifier]
    A -->|"Actual Cosine Drift Labels y"| E
    E -->|"Predict Drift >= Dynamic Threshold"| F["Save predictions.json & model.joblib"]
    end

    subgraph "Pipeline 2: Search Quality Benchmarking (benchmark_runner.py)"
    A -->|"checkout snapshot"| G[Snapshot Builder]
    F -->|"predictions.json"| H["decide_updated_entities - strategy_runner.py"]
    G -->|"Extract Code Snapshot"| I["Index Builder - index_builder.py"]
    H -->|"Identify Stale Nodes"| I
    I -->|"Selective Updates"| J["Candidate Selective Index (I_candidate)"]
    I -->|"Full Re-index"| K["Ground-Truth Baseline Index (I_baseline)"]
    
    J & K --> L["Embedding Comparator: Cosine Sim / Drift"]
    J & K --> M["Search Query Engine: Recall@K, MRR, nDCG"]
    end

    L & M --> N["Output report: summary_report.md"]
```

---

## 2. Environment Setup

### 2.1 Python Virtual Environment
Initialize and configure your Python dependencies:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
./venv/Scripts/Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2.2 Joern Code Property Graph Server
If running in Joern mode (`joern_hybrid` or `joern_only`), you must have Joern installed on your system path and start the local CPG query server:

```powershell
# Starts the Joern CPGQL query server on localhost:8080 (in a separate terminal)
joern --server 
```
Running for a configurable port
```powershell
# Starts the Joern CPGQL query server on localhost:<port-number> (in a separate terminal)
joern --server --server-port <port-number>
```

Run the joern server on a manually configured port 8081
```powershell
# Starts the Joern CPGQL query server on localhost:8081 (in a separate terminal)
joern --server --server-port 8081
```

---

## 3. Pipeline 1: Model Training & Drift Prediction (`run_experiment.py`)

This pipeline replays Git history, extracts features, calculates actual embedding cosine drift, and trains a Random Forest model to predict future stale cache nodes.

### 3.1 CLI Arguments Reference
*   `--config`: Path to a JSON configuration file (e.g. `config.example.json`). If provided, command line arguments override settings loaded from this file.
*   `--repo-url`: Git repository URL to clone (default: `https://github.com/psf/black.git`).
*   `--workspace-dir`: Workspace directory name (default: `workspace`).
*   `--num-commits`: Number of commits to process in the train-test sequence.
*   `--commit-stride`: Step size between processed commits.
*   `--parser-mode`: Repository parsing strategy:
    *   `ast`: Direct Python AST nodes (default).
    *   `joern_hybrid`: AST for dependency graphs, Joern server for CPG feature harvesting.
    *   `joern_only`: Pure Joern CPG construction and call graph extraction.
*   `--model-name`: Name of the SentenceTransformer model (e.g. `sentence-transformers/all-MiniLM-L6-v2` or `microsoft/unixcoder-base`).
*   `--threshold`: The drift threshold above which an entity is marked as "stale" (default: `0.02`).

### 3.2 Running the Pipeline

#### A. Standard Python AST Parsing (No Joern Required)
```powershell
./venv/Scripts/python.exe run_experiment.py --parser-mode ast --num-commits 30 --model-name sentence-transformers/all-MiniLM-L6-v2
```

#### B. Joern-Backed Hybrid Mode
```powershell
# Joern server must be running at localhost:8080
./venv/Scripts/python.exe run_experiment.py --parser-mode joern_hybrid --num-commits 15 --model-name sentence-transformers/all-MiniLM-L6-v2
```

#### C. Using a Configuration JSON File
```powershell
./venv/Scripts/python.exe run_experiment.py --config config.example.json
```

### 3.3 Output Artifacts
The training run outputs:
*   `predictions.json`: A mapping of entity IDs to boolean predictions (`true` = stale, re-embed; `false` = fresh, reuse cache).
*   `results/`: Directory containing performance plots, trained model weight files (`model.joblib`), and training logs.

---

## 4. Pipeline 2: Standalone Search Quality Benchmarking (`benchmark_runner.py`)

This pipeline runs search queries against the selective vector index (built using predictions from Pipeline 1) and compares search ranking degradation against a ground-truth baseline re-index.

### 4.1 CLI Arguments Reference
*   `--config`: Path to a JSON benchmarking config (e.g. `benchmark_config.example.json`).
*   `--repo-path`: Path to the local git checkout folder (default: `workspace/black`).
*   `--output-dir`: Base folder to store evaluation results (default: `benchmark_runs`).
*   `--num-commits`: Number of commit snapshots to evaluate.
*   `--strategies`: Comma-separated list of invalidation strategies to compare. Options:
    *   `full_reindex`: Re-embed all entities on every commit (100% cost, baseline safety).
    *   `changed_only`: Re-embed only entities that have direct source code edits.
    *   `fixed_hop`: Re-embed direct changes and immediate caller/callee files.
    *   `weighted_bfs_decay`: Multiplicative graph-decay impact propagation (threshold=0.05).
    *   `predictive_ml`: Use cache updates predicted by your trained ML model.
*   `--predictions-path`: Path to the `predictions.json` file generated by Pipeline 1.
*   `--query-mode`: Search query sources:
    *   `synthetic`: Automatically generated docstring/function description query cases (default).
    *   `curated`: Load user-defined test queries from a CSV/JSON file.
    *   `hybrid`: Merge synthetic and curated queries.

### 4.2 Running the Benchmark

#### A. Compare All Cache Invalidation Strategies Side-by-Side
```powershell
./venv/Scripts/python.exe benchmark_runner.py --repo-path workspace/black --query-mode synthetic --num-commits 5 --strategies changed_only,fixed_hop,predictive_ml,full_reindex --predictions-path predictions.json
```

#### B. Using a Benchmarking Configuration File
```powershell
./venv/Scripts/python.exe benchmark_runner.py --config benchmark_config.example.json
```

### 4.3 Output Artifacts
Artifacts are stored under `benchmark_runs/<run_id>/`:
*   `benchmark_config.json`: The active runtime configuration.
*   `per_query_results.jsonl`: Detailed per-query results containing baseline rank, selective rank, scores, and deltas.
*   `summary_metrics.json`: High-level metrics for the run.
*   `summary_report.md`: A detailed Markdown report containing a **Strategy Performance Comparison Table** and a **Direct Embedding Quality Table**.

---

## 5. Verification Test Suite

Verify your installation and run the suite of unit/smoke tests:

```powershell
./venv/Scripts/python.exe -m unittest discover -s tests -p 'test_benchmark_*.py'
```

---

## 6. Advanced Integrations & Logging

### 6.1 AST Cosmetic Filter
To save API cost and clean up model training noise, the pipeline uses a node-level AST filter:
*   We compile code snippets into Abstract Syntax Trees using Python's `ast` module.
*   We compare `ast.dump(ast.parse(old_code))` against `ast.dump(ast.parse(new_code))`.
*   If they are identical, the edit was purely cosmetic (whitespaces, docstrings, or comments). The entity is automatically removed from `modified_entities` and does not trigger updates.

### 6.2 Commit-Pair Diagnostic Logging
Each commit transition $(C_t \rightarrow C_{t+1})$ produces a detailed diagnostic log file `results/<dir_name>/commit_logs/commit_from_<commit_a>_to_<commit_b>.json` containing:
1.  **`git_changes`**: Added, modified (semantic only), and removed entity IDs.
2.  **`dependency_graph`**: Full call graph topological nodes and edges at that commit state.
3.  **`features_matrix`**: The exact matrix of 25 features calculated for all entities in the repository.
4.  **`cosine_drifts`**: Ground-truth actual embedding drift values.
5.  **`invalidation_decisions`**: Model predictions and stale/fresh decisions.
6.  **`strategy_re_embeddings`**: Lists of entities re-embedded under all evaluated strategies (including `weighted_bfs_decay`).
7.  **`strategy_metrics`**: Evaluation search scores (Recall@K, MRR, nDCG) for each strategy.


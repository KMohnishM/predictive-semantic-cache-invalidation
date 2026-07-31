# Predictive Semantic Cache Invalidation under Repository Evolution

This repository contains a research prototype for **Predictive Semantic Cache Invalidation**. The system models software repositories as dependency call graphs, replays historical Git commits sequentially, computes semantic drift in entity embeddings, and trains a machine learning model to selectively re-embed only the entities that are predicted to become semantically stale.

### Quick Start: Benchmarking

Run the standalone benchmarking pipeline from the repository root with the local virtual environment Python:

```powershell
./venv/Scripts/python.exe benchmark_runner.py --repo-path . --output-dir benchmark_runs --num-commits 2 --query-mode synthetic --max-queries-per-entity 1
```

Run the benchmark tests with:

```powershell
./venv/Scripts/python.exe -m unittest discover -s tests -p 'test_benchmark_*.py'
```

---

## 1. Research Problem Statement

Modern Large Language Model (LLM)-based software engineering assistants rely on repository-scale vector databases to provide contextual retrieval (Retrieval-Augmented Generation, code search, auto-completion). As a repository evolves through Git commits, localized code modifications can alter the semantics of dependent functions, classes, or modules downstream without introducing direct textual changes to those entities.

Current index maintenance strategies fall into two extremes:
* **Local Update Strategy (Baseline A)**: Only directly modified entities are re-embedded. This ignores semantic changes propagated through dependencies, leading to **semantic staleness** in retrieval.
* **Full Repository Re-indexing (Baseline B)**: Every entity is re-embedded after each commit. This preserves semantic consistency but is computationally expensive and scales poorly.

**Research Objective**: Solve $\min_{S} C(S)$ subject to $Q(S) \ge Q_{Full} - \varepsilon$, where $C(S)$ is the embedding maintenance cost, $Q(S)$ is the retrieval quality, and $\varepsilon$ is an acceptable degradation threshold.

---

## 2. Proposed Architecture & Implementation

The framework runs in a sequential pipeline across Git history, extracting features and measuring actual drift to evaluate cache invalidation strategies:

```
          Repository Update
                  ↓
       Dependency Graph Update  (AST-based Call Graph parsing)
                  ↓
            Impact Analysis
                  ↓
       Semantic Drift Prediction (Random Forest Classifier/Regressor)
                  ↓
             Re-Embedding       (SentenceTransformer all-MiniLM-L6-v2)
                  ↓
         Vector Database Update (Selective Cache Invalidation)
```

### Key Modules (`src/`)
* **`git_helper.py`**: Interfaces with Git to checkout commits, extract diffs, and query modified files. Handles carriage return (CRLF) sanitation for Windows compatibility.
* **`repo_parser.py`**: Uses Python's `ast` module to extract classes, functions, and methods. Resolves cross-file import names to construct a directed repository Call Graph $G=(V,E)$ using `networkx`.
* **`embedding_manager.py`**: Generates embeddings for code snippets using local `sentence-transformers` and computes semantic drift: $D(v) = 1 - \cos(E_t(v), E_{t+1}(v))$.
* **`feature_extractor.py`**: Harvests structural features (PageRank, Centralities, Degrees), propagation features (shortest path distance to modified nodes), and commit characteristics (file lines changed, edit sizes).
* **`predictor.py`**: Trains machine learning models (Random Forest, Gradient Boosting, Linear models) on temporal train/test splits of commit history to predict semantic drift.
* **`evaluator.py`**: Simulates and compares cache maintenance policies (Changed-Only, Full Reindex, Fixed-Hop, and Proposed Predictive) measuring Recall@K and Spearman Rank Correlation.
* **`visualize.py`**: Generates plots summarizing drift distribution, propagation decay, feature importances, and the Pareto frontier (Retrieval quality vs. Maintenance cost).

### Performance Optimizations
* **Single-Pass Replay**: Combines parsing, embedding, and feature extraction into a single chronological loop, reducing Git checkouts and parses by **65%**.
* **Centrality Precomputation**: Calculates PageRank, closeness centrality, and betweenness centrality once per graph instead of per-node, optimizing complexity from $O(|V|^2)$ to $O(|V|)$.
* **Diff Stats Caching**: Gathers lines added/deleted for all modified files in a single fast subprocess call per commit pair, avoiding hundreds of individual Git subprocess spawns.

---

## 3. Setup & Installation

### Prerequisites
* Python 3.8+ (tested on Python 3.12)
* Git installed and configured in your system path

### Installation
1. Clone this repository (or copy the files to your workspace).
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

Dependencies include:
* `networkx`: call graph representation
* `sentence-transformers`: code embedding generation
* `scikit-learn`: predictive ML models
* `numpy`, `pandas`: data structures & processing
* `matplotlib`, `seaborn`: visualization plots
* `scipy`: rank correlation metrics

---

## 4. How to Run the Experiment

The pipeline runs automatically on the official **[`psf/black`](https://github.com/psf/black)** repository.

### Run on a Test Subset
To test the pipeline quickly (harvesting the last 10 commits, splitting 7 for training and 3 for evaluation):
```bash
python run_experiment.py --subset 10
```

### Run Full Experiment
To run the full experiment on the last 50 commits (this will clone the repository to `workspace/black` and execute end-to-end):
```bash
python run_experiment.py --num-commits 50
```

### Command Line Options
* `--repo-url`: Git URL of the repository to analyze (defaults to `https://github.com/psf/black.git`).
* `--workspace-dir`: Folder to clone the repository (defaults to `workspace`).
* `--num-commits`: Number of commits to replay.
* `--train-ratio`: Split ratio for training commits (defaults to `0.7`).
* `--threshold`: Cosine drift threshold $\theta$ above which a node is flagged as stale (defaults to `0.02`).
* `--clean-mode`: Strip comments and docstrings from Python files using AST before embedding (defaults to `False`).

---

## 5. Experiment Outputs

The experiment saves all visual charts and performance summaries to the `results/` directory:
* **`summary_report.txt`**: Detailed text report of model scores, top feature importances, and strategy recall comparisons.
* **`feature_importance.png`**: Bar chart showing which structural features (e.g., PageRank) predict drift.
* **`drift_decay.png`**: Drift magnitude plotted against graph distance (hops) to modified nodes.
* **`pareto_frontier.png`**: Retrieval quality (Recall@10) vs. Index update percentage, showing the optimal frontier.
* **`strategy_comparison.png`**: Side-by-side comparison of Recall@5, Recall@10, and Rank Correlation across all baselines.
* **`results.json`**: Raw serialized metric outputs.

---

## 6. Benchmarking Pipeline

This repository also includes a standalone benchmarking pipeline under `src/benchmarking/`. The benchmark is separate from the main experiment and is meant to answer a different question:

> How closely does a selective re-embedding strategy preserve retrieval behavior compared with a full repository re-index?

### What the benchmark does

The benchmark runs the repository through a commit-based evaluation loop and compares two indexing modes on the same query set:

1. **Full re-index baseline**: all entities are embedded again for the later commit snapshot.
2. **Selective update candidate**: only a subset of entities is updated, while the remaining embeddings are reused.

For each sampled commit pair, the benchmark:

1. Builds a repository snapshot for the commit before and the commit after.
2. Samples entities and generates query cases.
3. Builds a full baseline index for the later snapshot.
4. Builds a selective index that reuses cached embeddings where possible.
5. Retrieves results for every query against both indices.
6. Computes retrieval-fidelity metrics and freshness/cached-retention checks.
7. Writes JSON, JSONL, and markdown artifacts into a dedicated benchmark run directory.

The current implementation is a standalone scaffold and is intentionally isolated from the main experiment pipeline.

### Benchmark flow

The flow is implemented in the following modules:

* `benchmark_runner.py`: top-level entrypoint for running the benchmark from the repository root.
* `src/benchmarking/runner.py`: orchestrates the benchmark end to end.
* `src/benchmarking/repository_snapshot.py`: builds commit-specific repository snapshots without mutating the working tree.
* `src/benchmarking/commit_sampler.py`: selects deterministic commit pairs.
* `src/benchmarking/query_sources.py`: generates synthetic queries or loads curated queries.
* `src/benchmarking/index_builder.py`: builds baseline and selective retrieval indices.
* `src/benchmarking/metrics.py`: computes ranking, freshness, and cache-preservation metrics.
* `src/benchmarking/serialization.py`: writes run artifacts to disk.
* `src/benchmarking/reporting.py`: generates the human-readable summary report.

### How to run the benchmark

Run the benchmark from the repository root with the local virtual environment Python:

```powershell
./venv/Scripts/python.exe benchmark_runner.py --repo-path . --output-dir benchmark_runs --num-commits 2 --query-mode synthetic --max-queries-per-entity 1
```

Common options:

* `--repo-path`: local git checkout to benchmark.
* `--output-dir`: root directory for benchmark outputs.
* `--num-commits`: number of recent commits to sample.
* `--commit-stride`: stride used when sampling commit pairs.
* `--sampling-mode`: `adjacent`, `stride`, or `manual`.
* `--query-mode`: `synthetic`, `curated`, or `hybrid`.
* `--curated-queries-path`: optional JSON or CSV file for curated query cases.
* `--model-name`: sentence-transformers model used for embeddings.
* `--clean-mode`: strip comments and docstrings before embedding.
* `--top-k-values`: comma-separated K values used by the retrieval metrics.

The run will create a directory such as `benchmark_runs/benchmark_v1.0_seed13_<commit>_<commit>/` containing:

* `benchmark_config.json`
* `commit_pairs.json`
* `queries.json`
* `per_query_results.jsonl`
* `summary_metrics.json`
* `summary_report.md`

### How to test the benchmark

Run the benchmark test suite with `unittest`:

```powershell
./venv/Scripts/python.exe -m unittest discover -s tests -p 'test_benchmark_*.py'
```

The benchmark tests cover:

* Configuration parsing and normalization.
* Deterministic commit sampling.
* Synthetic query generation and curated query loading.
* Commit-aware repository snapshot extraction.
* Retrieval metrics and artifact serialization.
* A smoke test that runs the full pipeline on a temporary git repository.

### Notes on current behavior

* The benchmark is isolated from `run_experiment.py` and does not change the existing experiment outputs.
* The first run may load the embedding model weights from Hugging Face.
* Benchmark outputs are ignored by Git via `benchmark_runs/` in `.gitignore`.

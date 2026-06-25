# Predictive Semantic Cache Invalidation under Repository Evolution

This repository contains a research prototype for **Predictive Semantic Cache Invalidation**. The system models software repositories as dependency call graphs, replays historical Git commits sequentially, computes semantic drift in entity embeddings, and trains a machine learning model to selectively re-embed only the entities that are predicted to become semantically stale.

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

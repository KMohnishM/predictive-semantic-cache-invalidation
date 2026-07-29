# Benchmarking Pipeline

This package contains the standalone benchmarking pipeline for retrieval-fidelity evaluation.

The benchmark is not the same as the main experiment in the repository root. The main experiment measures drift prediction and maintenance cost; the benchmark measures whether a selective re-embedding policy preserves retrieval behavior compared with a full re-index.

## What the benchmark does

For each sampled commit pair, the benchmark:

1. Builds a repository snapshot for the commit before and the commit after.
2. Generates or loads query cases that target repository entities.
3. Builds a full re-index baseline for the later snapshot.
4. Builds a selective candidate index that reuses cached embeddings for unchanged entities where possible.
5. Runs the same queries against both indices.
6. Compares the selective ranking against the baseline ranking.
7. Computes freshness and cache-preservation checks.
8. Writes run artifacts and a markdown summary report.

## Package modules

* `config.py` - command-line argument parsing and benchmark configuration.
* `commit_sampler.py` - deterministic commit-pair sampling.
* `repository_snapshot.py` - commit-aware parsing of Python entities without checking out the tree.
* `query_sources.py` - synthetic query generation and curated query loading.
* `dataset_builder.py` - joins commit pairs and queries into evaluation rows.
* `index_builder.py` - builds baseline and selective retrieval indices.
* `strategy_runner.py` - decides which entities are refreshed in the selective path.
* `metrics.py` - computes ranking and fidelity metrics.
* `serialization.py` - writes JSON, JSONL, and config artifacts.
* `reporting.py` - writes the summary markdown report.
* `runner.py` - end-to-end orchestration.
* `cli.py` - package-level CLI entrypoint.

## Run the benchmark

From the repository root:

```powershell
./venv/Scripts/python.exe benchmark_runner.py --repo-path . --output-dir benchmark_runs --num-commits 2 --query-mode synthetic --max-queries-per-entity 1
```

Useful flags:

* `--repo-path`: local git repository to benchmark.
* `--output-dir`: output root for benchmark runs.
* `--num-commits`: number of recent commits to sample.
* `--commit-stride`: spacing between sampled commit pairs.
* `--sampling-mode`: `adjacent`, `stride`, or `manual`.
* `--query-mode`: `synthetic`, `curated`, or `hybrid`.
* `--curated-queries-path`: path to a JSON or CSV file with manual queries.
* `--model-name`: embedding model.
* `--clean-mode`: remove comments and docstrings before embedding.
* `--top-k-values`: retrieval K values as a comma-separated list.

## Run tests

Run the benchmark tests with the repository venv:

```powershell
./venv/Scripts/python.exe -m unittest discover -s tests -p 'test_benchmark_*.py'
```

The current test suite covers:

* Config parsing.
* Commit sampling.
* Query generation/loading.
* Repository snapshot parsing from commit content.
* Retrieval metrics.
* Artifact serialization.
* End-to-end smoke execution.

## Output structure

Each benchmark run writes a directory named like `benchmark_v1.0_seed13_<before>_<after>` under the configured output root. The directory contains:

* `benchmark_config.json`
* `commit_pairs.json`
* `queries.json`
* `per_query_results.jsonl`
* `summary_metrics.json`
* `summary_report.md`

## Current implementation note

The benchmark pipeline is intentionally isolated from the main experiment code. It can be extended in phases without affecting `run_experiment.py` or the existing results layout.

## Detailed explanation

### Architecture & Pipeline Overview

The benchmarking pipeline evaluates retrieval fidelity when employing a selective cache invalidation policy compared against a full re-index baseline.

```
                      [Git Repository & Commits]
                                  │
                                  ▼
                     [1. Commit Pair Sampler]
                      (adjacent / stride)
                                  │
                                  ▼
           ┌──────────────────────────────────────────────┐
           │ 2. Git Entity Snapshotter (AST AST-walk)     │
           │    - before_snapshot  (Commit A)             │
           │    - after_snapshot   (Commit B)             │
           └──────────────────────┬───────────────────────┘
                                  │
            ┌─────────────────────┴─────────────────────┐
            ▼                                           ▼
[3. Query Builder]                         [4. Strategy Runner]
(Synthetic / Curated)                      Identifies changed entity IDs
            │                                           │
            │                                           ▼
            │                              [5. Index Snapshot Builder]
            │                              - Baseline Index: Re-embeds all B entities
            │                              - Selective Index: Embeds changed B entities,
            │                                reuses cached vectors from A
            └─────────────────────┬─────────────────────┘
                                  │
                                  ▼
                       [6. Dual Top-K Retrieval]
                 Queries ran against both Indices
                                  │
                                  ▼
                   [7. Fidelity & Metric Evaluator]
             Recall@K, MRR, NDCG@K, Freshness & Cache Preservation
                                  │
                                  ▼
               [8. Serialization & Report Generator]
            JSON, JSONL & Summary Markdown Artifacts
```

### Module Breakdown & Data Flow

1. **Commit Sampling (`commit_sampler.py`)**
   - Extracts commit history via `GitHelper`.
   - Supports `adjacent` sampling (pairing commit $i$ with $i+1$) and `stride` sampling (spacing commit pairs by `commit_stride`).

2. **Zero-Checkout AST Snapshotting (`repository_snapshot.py`)**
   - Lists Python source files at a specific commit hash using `git ls-tree -r --name-only <commit_hash>`.
   - Fetches file content directly via `git show <commit_hash>:<file_path>` without checking out working tree files.
   - Parses AST via Python `ast` module to extract top-level functions, classes, and class methods.
   - Assigns unique canonical IDs formatted as `file_path::Class::method` or `file_path::function`.

3. **Query Dataset Construction (`query_sources.py`, `dataset_builder.py`)**
   - **Synthetic queries**: Automatically generated from entities in the target commit snapshot with templates targeting entity descriptions and location questions.
   - **Curated queries**: Loaded from custom JSON or CSV files containing hand-crafted benchmark evaluation cases.
   - Pairs query cases with commit transitions into evaluation dataset rows.

4. **Selective Re-Embedding & Dual Indexing (`index_builder.py`, `strategy_runner.py`)**
   - **Baseline Index**: Computes fresh vector embeddings for all entities present in the target commit (`commit_after`).
   - **Selective Index**: Identifies modified files between `commit_before` and `commit_after` via `git diff`. For modified or new entities, fresh embeddings are generated; for unchanged entities, vector embeddings are reused directly from the previous commit's cached index.

5. **Retrieval & Metric Evaluation (`metrics.py`, `runner.py`)**
   - Evaluates queries against both baseline and selective index snapshots using cosine similarity search in `EmbeddingManager`.
   - Calculates ranking metrics:
     - **Recall@K**: Indicates whether the ground-truth target entity is retrieved within top $K$.
     - **MRR (Mean Reciprocal Rank)**: Computes $1 / \text{rank}$ for target entity retrieval.
     - **NDCG@K**: Discounted Cumulative Gain accounting for ranking position.
     - **Rank & Score Deltas**: Differences in rank position and similarity scores between selective and baseline indices.
   - Verifies **Freshness Pass** (retrieval accuracy for modified entities) and **Cache Preservation Pass** (retrieval stability for unchanged cached entities).

6. **Artifact Persistence (`serialization.py`, `reporting.py`)**
   - Serializes complete evaluation details to `<output_dir>/benchmark_v<version>_seed<seed>_<before>_<after>/`:
     - `benchmark_config.json`: Run parameters and settings.
     - `commit_pairs.json`: Evaluated commit pairs.
     - `queries.json`: Test query cases.
     - `per_query_results.jsonl`: Line-by-line detailed retrieval results.
     - `summary_metrics.json`: Aggregate performance metrics and pass criteria status.
     - `summary_report.md`: Human-readable summary report.
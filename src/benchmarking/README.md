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
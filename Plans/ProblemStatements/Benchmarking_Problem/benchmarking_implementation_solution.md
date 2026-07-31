# Benchmarking Implementation Solution

## 1. Objective

Build a reproducible benchmarking pipeline that measures how closely a selective re-embedding strategy matches a full repository re-index in retrieval behavior.

The benchmark must answer this question:

What is the smallest set of repository entities that must be re-embedded after a code change so that retrieval quality remains close to a full re-index?

The benchmark must evaluate retrieval quality, not embedding quality alone. It must compare the same query set under two modes:

- Full re-index baseline: all entities are re-embedded after a commit change.
- Selective re-embedding candidate: only a smaller subset of entities is re-embedded.

The benchmark must prove two things:

- Queries targeting changed code return the latest snapshot and do not surface stale cached content.
- Queries targeting unchanged code still return the correct cached content.

The benchmark must be reproducible, deterministic, and fully isolated from the existing experiment pipeline.

## 2. Design Principles

1. Isolation first

   The benchmark implementation must live in new Python files and must not interfere with the current experiment flow, training flow, or evaluation code.

2. Deterministic execution

   The same repo revision, commit window, query set, and configuration must produce the same benchmark outputs.

3. Full comparability

   The benchmark must always evaluate selective results against a full re-index baseline for the same queries and same repository state.

4. Query-level traceability

   Every benchmark result must be traceable back to the exact query, target entity, commit transition, and evaluation mode.

5. Reproducible artifacts

   The benchmark must persist raw records, aggregate scores, and summary reports so the run can be reproduced and audited later.

## 3. Scope Boundaries

### In scope

- Separate benchmark package and entrypoint.
- Deterministic query generation.
- Optional curated query set support.
- Full re-index baseline evaluation.
- Selective re-embedding evaluation.
- Retrieval metrics and fidelity metrics.
- Per-query artifact persistence.
- Summary report generation.
- Benchmark-only tests.

### Out of scope for the first implementation

- Changing the current experiment orchestration in `run_experiment.py`.
- Rewriting the current predictive drift pipeline.
- Replacing the current evaluator used by the existing experiment.
- Changing the current model training pipeline.

The benchmark should consume existing repository parsing and embedding utilities when needed, but it must not couple itself to the current experiment lifecycle.

## 4. High-Level Architecture

The benchmark should be implemented as a separate module tree, for example:

- `src/benchmarking/`
  - `__init__.py`
  - `config.py`
  - `dataset.py`
  - `commit_sampler.py`
  - `query_builder.py`
  - `index_builder.py`
  - `strategy_runner.py`
  - `metrics.py`
  - `reporting.py`
  - `serialization.py`
  - `cli.py`

A separate top-level entrypoint may also be used if preferred, for example:

- `benchmark_runner.py`

The core requirement is that benchmark code remains isolated from the existing runtime path used by the main experiment.

## 5. Component Responsibilities

### 5.1 `config.py`

Defines all benchmark configuration in one place.

Responsibilities:

- Repository URL or local repository path.
- Commit range or sampled commit list.
- Query source mode.
- Output directory.
- Embedding model selection.
- Strategy selection.
- Top-K values for retrieval metrics.
- Random seed.
- Whether curated queries are enabled.
- Whether to write JSON, CSV, and markdown reports.

The benchmark configuration must be serializable and written into the output directory for each run.

### 5.2 `dataset.py`

Builds the benchmark dataset for one run.

Responsibilities:

- Load the repository snapshot at each commit transition.
- Resolve changed entities and unchanged entities.
- Attach metadata required for evaluation.
- Create a stable dataset of query cases.

Dataset records should include at least:

- `commit_before`
- `commit_after`
- `entity_id`
- `entity_name`
- `entity_type`
- `file_path`
- `change_kind`
- `query_text`
- `query_source`
- `expected_target_snapshot`
- `expected_behavior`
- `is_changed_entity`
- `is_unchanged_entity`

### 5.3 `commit_sampler.py`

Selects the commit transitions that will be benchmarked.

Responsibilities:

- Deterministic sampling of commit pairs.
- Optional adjacent-only mode.
- Optional stride mode.
- Optional manual commit list mode.
- Reproducible ordering of sampled transitions.

Sampling must be controlled by a seed and must produce the same sampled transitions across runs when inputs are unchanged.

### 5.4 `query_builder.py`

Constructs the exact query set used in the benchmark.

Responsibilities:

- Generate synthetic queries from repository entities.
- Load curated queries from a file if provided.
- Normalize query text for consistent comparison.
- Attach query labels and target metadata.

The query builder should support two sources:

1. Synthetic queries

   These are derived from repository content and metadata. They must be deterministic and reproducible.

2. Curated queries

   These are manually authored queries stored in a file such as JSON or CSV. This allows stronger realism while preserving traceability.

Query categories should include at least:

- Changed entity queries.
- Unchanged entity queries.
- Freshness validation queries.
- Cache preservation queries.

### 5.5 `index_builder.py`

Builds the baseline and selective indices for each commit transition.

Responsibilities:

- Build full re-index embeddings for the after-commit snapshot.
- Build selective embeddings for only the chosen updated entities.
- Retain previous embeddings for unchanged entities when the strategy allows caching.
- Provide a uniform interface so both strategies can be queried the same way.

This module must define the benchmark’s index abstraction so retrieval evaluation does not depend on implementation details.

### 5.6 `strategy_runner.py`

Executes the benchmarked re-embedding strategy.

Responsibilities:

- Accept the set of changed entities and any strategy-specific metadata.
- Decide which entities to re-embed.
- Produce the selective update set.
- Record the percentage of the repository that was updated.
- Record the exact entity identifiers selected for refresh.

This module should be strategy-agnostic so additional benchmark strategies can be added later without redesign.

### 5.7 `metrics.py`

Computes retrieval and fidelity metrics.

Responsibilities:

- Compare selective retrieval rankings against full re-index rankings.
- Compute category-wise metrics.
- Compute freshness pass/fail checks.
- Compute cache preservation pass/fail checks.
- Aggregate results across queries and commit transitions.

Recommended metrics:

- Recall@K for K in {1, 5, 10}.
- MRR.
- nDCG@K.
- Rank correlation such as Spearman.
- Exact target-hit rate.
- Freshness success rate.
- Cache retention success rate.
- Delta versus full re-index baseline.

The metric layer must distinguish between ranking agreement and semantic correctness.

### 5.8 `serialization.py`

Writes benchmark data to disk.

Responsibilities:

- Persist raw per-query rows.
- Persist aggregate scores.
- Persist configuration and seed values.
- Persist commit sampling metadata.
- Persist evaluation timestamp and repository revision.

Recommended file outputs:

- `benchmark_config.json`
- `commit_pairs.json`
- `queries.json`
- `per_query_results.jsonl`
- `summary_metrics.json`
- `summary_report.md`
- Optional CSV exports for analysis in spreadsheets.

### 5.9 `reporting.py`

Produces human-readable benchmark reports.

Responsibilities:

- Summarize benchmark configuration.
- Explain the benchmark protocol.
- Report per-category performance.
- Highlight where selective re-embedding diverges from full re-index.
- Report the smallest entity subset that satisfies the benchmark threshold, if that search is enabled.

Report content should explicitly state whether the candidate strategy preserved retrieval behavior for changed and unchanged code.

### 5.10 `cli.py`

Provides the benchmark command line interface.

Responsibilities:

- Parse arguments.
- Load configuration.
- Run the benchmark pipeline.
- Exit with a reproducible artifact directory.

This CLI should be the primary entrypoint for running the benchmark.

## 6. Reproducibility Requirements

The benchmark should be reproducible from a clean checkout and a fixed environment.

### Required controls

- Fixed repository revision or commit range.
- Fixed random seed.
- Fixed embedding model version.
- Fixed commit sampling strategy.
- Fixed query set version.
- Fixed output directory naming convention.
- Fixed metric definitions and K values.

### Required metadata

Every benchmark run must save:

- The repository URL or local path.
- The repository commit hash used as the starting point.
- The sampled commit transitions.
- The exact query source file or generation parameters.
- The embedding model name.
- The strategy name.
- The seed.
- The benchmark version number.

### Reproducibility rule

If any of the above inputs change, the benchmark run must be considered a different benchmark instance and written to a separate output directory.

## 7. Evaluation Protocol

### 7.1 Baseline run

For each sampled commit transition:

1. Re-embed the full repository snapshot after the commit change.
2. Run the same query set against the full re-index index.
3. Record the ranking results and baseline metrics.

### 7.2 Selective run

For the same commit transition:

1. Re-embed only the subset selected by the benchmark strategy.
2. Reuse cached embeddings for untouched entities.
3. Run the same query set against the selective index.
4. Record the ranking results and selective metrics.

### 7.3 Comparison rule

Compare the selective run against the full re-index baseline query by query.

The comparison must answer:

- Did the query about changed code retrieve the latest content?
- Did the query about unchanged code preserve the correct cached content?
- How far did the selective ranking drift from the baseline ranking?

### 7.4 Acceptance rule

A strategy is acceptable only if it stays close to the baseline across all query categories and does not fail freshness or cache-preservation checks beyond the allowed tolerance.

The tolerance should be configurable.

## 8. Query Design

The benchmark should support at least two query modes.

### 8.1 Synthetic query mode

Synthetic queries are generated from repository entities.

Recommended behavior:

- Build queries from entity names, docstrings, function signatures, class names, and file paths.
- Ensure deterministic generation through seeded templates.
- Include changed and unchanged entities.
- Keep a stable mapping from each query to its intended target entity.

Examples of synthetic query templates:

- "What does `<entity_name>` do after the latest commit?"
- "Where is `<function_name>` implemented in the updated version?"
- "What changed in `<file_path>` after the commit?"
- "Which module depends on `<entity_name>` in the current snapshot?"

### 8.2 Curated query mode

Curated queries are manually authored and stored separately.

Recommended format:

- JSON is preferred for strict reproducibility and validation.
- CSV is acceptable if the schema is simple.

Each curated query should include:

- `query_id`
- `query_text`
- `target_entity_id`
- `target_entity_name`
- `commit_after`
- `category`
- `expected_behavior`
- `notes`

Curated queries should be optional, not required for the first benchmark release.

## 9. Output Schema

The benchmark output directory should contain a stable structure such as:

- `benchmark_runs/<run_id>/`
  - `benchmark_config.json`
  - `commit_pairs.json`
  - `queries.json`
  - `per_query_results.jsonl`
  - `summary_metrics.json`
  - `summary_report.md`
  - `plots/`
  - `logs/`

### Per-query record fields

Each row should include at least:

- `run_id`
- `commit_before`
- `commit_after`
- `query_id`
- `query_text`
- `query_source`
- `category`
- `target_entity_id`
- `target_entity_name`
- `expected_behavior`
- `baseline_rank`
- `selective_rank`
- `baseline_score`
- `selective_score`
- `top_k_hit_baseline`
- `top_k_hit_selective`
- `freshness_pass`
- `cache_preservation_pass`
- `rank_delta`
- `score_delta`
- `updated_entity_fraction`
- `strategy_name`

### Aggregate record fields

The summary JSON should include:

- `total_queries`
- `changed_query_count`
- `unchanged_query_count`
- `baseline_metrics`
- `selective_metrics`
- `metric_deltas`
- `freshness_success_rate`
- `cache_preservation_success_rate`
- `candidate_update_fraction`
- `benchmark_passed`

## 10. Modular Separation From Existing Logic

The benchmark implementation must not modify the current experiment path in a way that changes its behavior.

### Required separation rules

1. New benchmark code must live in new files.
2. Benchmark code must use separate classes and functions.
3. Benchmark code must have its own CLI entrypoint.
4. Benchmark output paths must not overlap with the current `results/` convention unless explicitly configured.
5. Existing experiment modules should only be imported as read-only dependencies, not patched into benchmark control flow.

### Preferred dependency direction

- Benchmark modules may call existing parsing or embedding utilities.
- Existing experiment modules should not import benchmark modules.

This keeps the benchmark modular and prevents accidental interference with the current pipeline.

## 11. Suggested Implementation Order

### Phase 1: Scaffolding

- Create `src/benchmarking/`.
- Add the benchmark config object.
- Add the CLI entrypoint.
- Add output directory creation.

### Phase 2: Dataset and query generation

- Implement deterministic commit sampling.
- Implement synthetic query generation.
- Implement curated query loading.
- Implement query labels and target metadata.

### Phase 3: Index and strategy execution

- Implement full re-index baseline building.
- Implement selective re-embedding indexing.
- Implement a uniform retrieval interface.

### Phase 4: Metrics

- Implement ranking agreement metrics.
- Implement freshness checks.
- Implement cache preservation checks.
- Implement aggregate metric summaries.

### Phase 5: Persistence and reporting

- Write per-query JSONL artifacts.
- Write summary JSON artifacts.
- Generate markdown summary reports.
- Add plots if needed.

### Phase 6: Validation

- Add benchmark unit tests.
- Add output schema tests.
- Add a smoke test for a small repo or small commit window.

## 12. Test Strategy

The benchmark should have dedicated tests that do not depend on the existing end-to-end experiment.

### Minimum tests

1. Query labeling test

   Verify that synthetic and curated queries receive the correct category and target metadata.

2. Commit sampling test

   Verify that the same seed produces the same sampled transitions.

3. Metric test

   Verify that baseline and selective rankings produce the expected metric values on a small toy example.

4. Serialization test

   Verify that all required fields exist in the output JSONL and summary JSON.

5. Smoke benchmark test

   Verify that a small benchmark run completes and writes artifacts.

### Test constraints

- Tests should use small fixtures.
- Tests should not require the full main repository replay.
- Tests should not mutate the current experiment results directory.

## 13. Success Criteria

The benchmark implementation is successful if it can:

- Reproduce the same benchmark run from the same inputs.
- Compare selective re-embedding against full re-index on the same queries.
- Show that changed-code queries retrieve the latest snapshot.
- Show that unchanged-code queries still retrieve cached information correctly.
- Persist enough metadata to audit and rerun the benchmark later.
- Operate through a separate modular code path without interfering with the existing experiment logic.

## 14. Recommended First Deliverable

The first implementation should be a minimal but complete benchmark skeleton with these capabilities:

- Separate benchmark package.
- Separate CLI.
- Deterministic query set.
- Full vs selective evaluation.
- JSONL result persistence.
- Markdown summary generation.
- Smoke test coverage.

Once that skeleton is stable, curated query support, advanced plots, and strategy sweeps can be added as incremental extensions.

## 15. Notes on Practical Reproducibility

To keep the benchmark truly reproducible, the run should record both code and environment details.

Recommended environment details:

- Python version.
- Dependency lock or requirements snapshot.
- Embedding model identifier.
- OS and platform.
- Git commit of the benchmark code itself.

Recommended run manifest fields:

- `benchmark_version`
- `repo_url`
- `repo_commit`
- `benchmark_seed`
- `query_source_version`
- `strategy_name`
- `embedding_model_name`
- `output_dir`

If possible, the benchmark should refuse to run when required fields are missing rather than silently proceeding with partial metadata.

## 16. Final Recommendation

Implement the benchmark as a standalone, modular pipeline under a new Python package and keep the current experiment logic untouched. Use full re-index as the baseline, selective re-embedding as the candidate strategy, and measure retrieval fidelity at the query level with explicit freshness and cache-preservation checks.

That design gives you a reproducible benchmark that can answer the original problem statement without coupling it to the current training and drift-evaluation workflow.

## 17. Concrete File-By-File Implementation Plan

This section turns the design into an exact implementation map. The benchmark should be added as new files only, with no behavioral changes to the existing experiment modules.

### 17.1 New package layout

Create a new package at `src/benchmarking/` with the following files:

- `src/benchmarking/__init__.py`
- `src/benchmarking/types.py`
- `src/benchmarking/config.py`
- `src/benchmarking/commit_sampler.py`
- `src/benchmarking/query_sources.py`
- `src/benchmarking/dataset_builder.py`
- `src/benchmarking/index_builder.py`
- `src/benchmarking/strategy_runner.py`
- `src/benchmarking/metrics.py`
- `src/benchmarking/serialization.py`
- `src/benchmarking/reporting.py`
- `src/benchmarking/runner.py`
- `src/benchmarking/cli.py`

If query logic grows, split `query_sources.py` into `query_sources/synthetic.py` and `query_sources/curated.py` later, but keep the first release simple unless the file becomes large.

### 17.2 File responsibilities and logic flow

#### `src/benchmarking/types.py`

Define the data contracts used everywhere else.

Recommended dataclasses or typed dicts:

- `BenchmarkConfig`
- `CommitPair`
- `QueryCase`
- `IndexSnapshot`
- `StrategyDecision`
- `PerQueryResult`
- `BenchmarkSummary`

This file should contain no I/O and no repository access. It only defines schema and keeps all benchmark modules aligned on the same field names.

#### `src/benchmarking/config.py`

Own all benchmark settings and defaults.

Logic:

1. Parse benchmark arguments.
2. Resolve repo path, output path, seed, commit sampling mode, query mode, and strategy selection.
3. Normalize defaults into a single config object.
4. Freeze the config before execution so the run is reproducible.

This file should also provide a `load_config()` or `build_config()` function that the CLI and runner can share.

#### `src/benchmarking/commit_sampler.py`

Select commit transitions deterministically.

Logic:

1. Read the full commit history for the target repository.
2. Apply the selected sampling mode:
   - adjacent only
   - fixed stride
   - explicit commit list
3. Produce ordered commit pairs.
4. Record the sampling seed and sampling policy.

The output should be a list of `CommitPair` records and should not mutate any repo state.

#### `src/benchmarking/query_sources.py`

Generate or load the queries used by the benchmark.

Logic:

1. For synthetic mode, derive queries from repository entities and their metadata.
2. For curated mode, load the query set from a checked-in JSON or CSV file.
3. Attach `target_entity_id`, `target_entity_name`, `query_category`, `expected_behavior`, and `query_source`.
4. Normalize query text so identical inputs always produce identical benchmark rows.

This file should provide a single public API such as `build_queries(...)` that returns a list of `QueryCase` objects.

#### `src/benchmarking/dataset_builder.py`

Turn commit pairs and query cases into benchmark-ready evaluation cases.

Logic:

1. Load repository state for the `before` and `after` commit.
2. Identify changed entities and unchanged entities.
3. Join query targets to the exact entity snapshot being evaluated.
4. Emit evaluation rows that link query text, entity target, commit pair, and expected behavior.

This file is the main bridge between repository metadata and benchmark evaluation.

#### `src/benchmarking/index_builder.py`

Build the two retrieval worlds that the benchmark compares.

Logic:

1. Build the full re-index baseline for the after-commit snapshot.
2. Build the selective index by applying the chosen update set only.
3. Reuse cached embeddings for untouched entities when the strategy permits.
4. Expose one retrieval interface so baseline and selective modes can be queried identically.

This file should not contain benchmark scoring logic. It should only produce searchable indices and their metadata.

#### `src/benchmarking/strategy_runner.py`

Decide which entities get refreshed in the selective path.

Logic:

1. Accept the changed entity set and repository context.
2. Apply the selected benchmark strategy.
3. Return the entity IDs to update.
4. Record the size of the refreshed subset relative to the repository size.

This file should remain strategy-agnostic so future benchmark strategies can be added without changing the pipeline.

#### `src/benchmarking/metrics.py`

Score the retrieval results.

Logic:

1. Compare the baseline ranking with the selective ranking for each query.
2. Compute ranking metrics at K.
3. Compute freshness pass/fail for changed-code queries.
4. Compute cache-preservation pass/fail for unchanged-code queries.
5. Aggregate results across all queries and commit pairs.

This is the only module that should know how the benchmark declares success or failure.

#### `src/benchmarking/serialization.py`

Persist the benchmark outputs.

Logic:

1. Create the run directory.
2. Write the frozen config.
3. Write sampled commit pairs.
4. Write query definitions.
5. Write one JSONL row per evaluated query.
6. Write aggregate summary JSON.

This module should enforce the output schema so the benchmark stays reproducible over time.

#### `src/benchmarking/reporting.py`

Generate the human-readable report.

Logic:

1. Load the serialized benchmark results.
2. Summarize the benchmark protocol.
3. Report per-category metrics.
4. Highlight failures where selective retrieval diverges from the full re-index baseline.
5. Emit a markdown summary file and optional plots.

#### `src/benchmarking/runner.py`

Orchestrate the benchmark end to end.

Logic:

1. Load config.
2. Sample commit pairs.
3. Build queries.
4. Build the evaluation dataset.
5. Run baseline and selective retrieval.
6. Score the results.
7. Serialize artifacts.
8. Generate the report.

This should be the single orchestration layer for the new benchmark package.

#### `src/benchmarking/cli.py`

Expose the benchmark as a separate command.

Logic:

1. Parse command-line arguments.
2. Build the config.
3. Instantiate the runner.
4. Execute the benchmark.
5. Exit with the artifact location.

The CLI should be the only supported entrypoint for normal benchmark execution.

### 17.3 Recommended supporting files

Add benchmark-only test files in a separate test area, for example:

- `tests/test_benchmark_config.py`
- `tests/test_benchmark_query_sources.py`
- `tests/test_benchmark_commit_sampler.py`
- `tests/test_benchmark_metrics.py`
- `tests/test_benchmark_serialization.py`
- `tests/test_benchmark_runner_smoke.py`

If the repository currently prefers a different test layout, mirror that convention, but keep the benchmark tests isolated from the existing smoke test.

### 17.4 Exact implementation order

1. Create `src/benchmarking/types.py` and `src/benchmarking/config.py` first so every later file shares the same schema.
2. Add `src/benchmarking/commit_sampler.py` and `src/benchmarking/query_sources.py` so the benchmark can produce deterministic inputs.
3. Add `src/benchmarking/dataset_builder.py` and `src/benchmarking/index_builder.py` so baseline and selective retrieval can be run on the same cases.
4. Add `src/benchmarking/strategy_runner.py` and `src/benchmarking/metrics.py` so the benchmark can compare candidate strategies against the baseline.
5. Add `src/benchmarking/serialization.py` and `src/benchmarking/reporting.py` so every run writes auditable artifacts.
6. Add `src/benchmarking/runner.py` and `src/benchmarking/cli.py` last so the full pipeline becomes executable from one command.
7. Add the benchmark tests only after the output schema is stable.

### 17.5 Logic boundaries that must not be crossed

- The existing `run_experiment.py` should remain untouched by the benchmark unless a later integration step explicitly decides to expose the benchmark from the old CLI.
- The existing `src/evaluator.py` should not be rewritten in place. The benchmark should use its own evaluator logic so it can define retrieval fidelity without changing the current experiment semantics.
- The benchmark should not share output directories with the current experiment run unless that is explicitly configured.
- The benchmark should not depend on the current training flow to produce its results.

### 17.6 Concrete run sequence

For one benchmark invocation, the control flow should be:

1. `cli.py` parses arguments.
2. `config.py` freezes the run config.
3. `commit_sampler.py` produces commit pairs.
4. `query_sources.py` produces query cases.
5. `dataset_builder.py` joins commits, queries, and entity metadata.
6. `index_builder.py` builds the full re-index baseline.
7. `strategy_runner.py` selects the selective refresh set.
8. `index_builder.py` builds the selective index.
9. `metrics.py` compares the retrieval results.
10. `serialization.py` writes JSON, JSONL, and config artifacts.
11. `reporting.py` writes the markdown report and any plots.

That sequence is the recommended implementation contract for the first version.

## 17. Concrete File-By-File Implementation Plan

This section turns the design into an exact implementation map. The benchmark should be added as new files only, with no behavioral changes to the existing experiment modules.

### 17.1 New package layout

Create a new package at `src/benchmarking/` with the following files:

- `src/benchmarking/__init__.py`
- `src/benchmarking/types.py`
- `src/benchmarking/config.py`
- `src/benchmarking/commit_sampler.py`
- `src/benchmarking/query_sources.py`
- `src/benchmarking/dataset_builder.py`
- `src/benchmarking/index_builder.py`
- `src/benchmarking/strategy_runner.py`
- `src/benchmarking/metrics.py`
- `src/benchmarking/serialization.py`
- `src/benchmarking/reporting.py`
- `src/benchmarking/runner.py`
- `src/benchmarking/cli.py`

If query logic grows, split `query_sources.py` into `query_sources/synthetic.py` and `query_sources/curated.py` later, but keep the first release simple unless the file becomes large.

### 17.2 File responsibilities and logic flow

#### `src/benchmarking/types.py`

Define the data contracts used everywhere else.

Recommended dataclasses or typed dicts:

- `BenchmarkConfig`
- `CommitPair`
- `QueryCase`
- `IndexSnapshot`
- `StrategyDecision`
- `PerQueryResult`
- `BenchmarkSummary`

This file should contain no I/O and no repository access. It only defines schema and keeps all benchmark modules aligned on the same field names.

#### `src/benchmarking/config.py`

Own all benchmark settings and defaults.

Logic:

1. Parse benchmark arguments.
2. Resolve repo path, output path, seed, commit sampling mode, query mode, and strategy selection.
3. Normalize defaults into a single config object.
4. Freeze the config before execution so the run is reproducible.

This file should also provide a `load_config()` or `build_config()` function that the CLI and runner can share.

#### `src/benchmarking/commit_sampler.py`

Select commit transitions deterministically.

Logic:

1. Read the full commit history for the target repository.
2. Apply the selected sampling mode:
   - adjacent only
   - fixed stride
   - explicit commit list
3. Produce ordered commit pairs.
4. Record the sampling seed and sampling policy.

The output should be a list of `CommitPair` records and should not mutate any repo state.

#### `src/benchmarking/query_sources.py`

Generate or load the queries used by the benchmark.

Logic:

1. For synthetic mode, derive queries from repository entities and their metadata.
2. For curated mode, load the query set from a checked-in JSON or CSV file.
3. Attach `target_entity_id`, `target_entity_name`, `query_category`, `expected_behavior`, and `query_source`.
4. Normalize query text so identical inputs always produce identical benchmark rows.

This file should provide a single public API such as `build_queries(...)` that returns a list of `QueryCase` objects.

#### `src/benchmarking/dataset_builder.py`

Turn commit pairs and query cases into benchmark-ready evaluation cases.

Logic:

1. Load repository state for the `before` and `after` commit.
2. Identify changed entities and unchanged entities.
3. Join query targets to the exact entity snapshot being evaluated.
4. Emit evaluation rows that link query text, entity target, commit pair, and expected behavior.

This file is the main bridge between repository metadata and benchmark evaluation.

#### `src/benchmarking/index_builder.py`

Build the two retrieval worlds that the benchmark compares.

Logic:

1. Build the full re-index baseline for the after-commit snapshot.
2. Build the selective index by applying the chosen update set only.
3. Reuse cached embeddings for untouched entities when the strategy permits.
4. Expose one retrieval interface so baseline and selective modes can be queried identically.

This file should not contain benchmark scoring logic. It should only produce searchable indices and their metadata.

#### `src/benchmarking/strategy_runner.py`

Decide which entities get refreshed in the selective path.

Logic:

1. Accept the changed entity set and repository context.
2. Apply the selected benchmark strategy.
3. Return the entity IDs to update.
4. Record the size of the refreshed subset relative to the repository size.

This file should remain strategy-agnostic so future benchmark strategies can be added without changing the pipeline.

#### `src/benchmarking/metrics.py`

Score the retrieval results.

Logic:

1. Compare the baseline ranking with the selective ranking for each query.
2. Compute ranking metrics at K.
3. Compute freshness pass/fail for changed-code queries.
4. Compute cache-preservation pass/fail for unchanged-code queries.
5. Aggregate results across all queries and commit pairs.

This is the only module that should know how the benchmark declares success or failure.

#### `src/benchmarking/serialization.py`

Persist the benchmark outputs.

Logic:

1. Create the run directory.
2. Write the frozen config.
3. Write sampled commit pairs.
4. Write query definitions.
5. Write one JSONL row per evaluated query.
6. Write aggregate summary JSON.

This module should enforce the output schema so the benchmark stays reproducible over time.

#### `src/benchmarking/reporting.py`

Generate the human-readable report.

Logic:

1. Load the serialized benchmark results.
2. Summarize the benchmark protocol.
3. Report per-category metrics.
4. Highlight failures where selective retrieval diverges from the full re-index baseline.
5. Emit a markdown summary file and optional plots.

#### `src/benchmarking/runner.py`

Orchestrate the benchmark end to end.

Logic:

1. Load config.
2. Sample commit pairs.
3. Build queries.
4. Build the evaluation dataset.
5. Run baseline and selective retrieval.
6. Score the results.
7. Serialize artifacts.
8. Generate the report.

This should be the single orchestration layer for the new benchmark package.

#### `src/benchmarking/cli.py`

Expose the benchmark as a separate command.

Logic:

1. Parse command-line arguments.
2. Build the config.
3. Instantiate the runner.
4. Execute the benchmark.
5. Exit with the artifact location.

The CLI should be the only supported entrypoint for normal benchmark execution.

### 17.3 Recommended supporting files

Add benchmark-only test files in a separate test area, for example:

- `tests/test_benchmark_config.py`
- `tests/test_benchmark_query_sources.py`
- `tests/test_benchmark_commit_sampler.py`
- `tests/test_benchmark_metrics.py`
- `tests/test_benchmark_serialization.py`
- `tests/test_benchmark_runner_smoke.py`

If the repository currently prefers a different test layout, mirror that convention, but keep the benchmark tests isolated from the existing smoke test.

### 17.4 Exact implementation order

1. Create `src/benchmarking/types.py` and `src/benchmarking/config.py` first so every later file shares the same schema.
2. Add `src/benchmarking/commit_sampler.py` and `src/benchmarking/query_sources.py` so the benchmark can produce deterministic inputs.
3. Add `src/benchmarking/dataset_builder.py` and `src/benchmarking/index_builder.py` so baseline and selective retrieval can be run on the same cases.
4. Add `src/benchmarking/strategy_runner.py` and `src/benchmarking/metrics.py` so the benchmark can compare candidate strategies against the baseline.
5. Add `src/benchmarking/serialization.py` and `src/benchmarking/reporting.py` so every run writes auditable artifacts.
6. Add `src/benchmarking/runner.py` and `src/benchmarking/cli.py` last so the full pipeline becomes executable from one command.
7. Add the benchmark tests only after the output schema is stable.

### 17.5 Logic boundaries that must not be crossed

- The existing `run_experiment.py` should remain untouched by the benchmark unless a later integration step explicitly decides to expose the benchmark from the old CLI.
- The existing `src/evaluator.py` should not be rewritten in place. The benchmark should use its own evaluator logic so it can define retrieval fidelity without changing the current experiment semantics.
- The benchmark should not share output directories with the current experiment run unless that is explicitly configured.
- The benchmark should not depend on the current training flow to produce its results.

### 17.6 Concrete run sequence

For one benchmark invocation, the control flow should be:

1. `cli.py` parses arguments.
2. `config.py` freezes the run config.
3. `commit_sampler.py` produces commit pairs.
4. `query_sources.py` produces query cases.
5. `dataset_builder.py` joins commits, queries, and entity metadata.
6. `index_builder.py` builds the full re-index baseline.
7. `strategy_runner.py` selects the selective refresh set.
8. `index_builder.py` builds the selective index.
9. `metrics.py` compares the retrieval results.
10. `serialization.py` writes JSON, JSONL, and config artifacts.
11. `reporting.py` writes the markdown report and any plots.

That sequence is the recommended implementation contract for the first version.

# Codebase Audit — `feature/Benchmark-Polish`

**Date:** 2026-10-10
**Scope:** All tracked Python code (`src/`, `run_experiment.py`, `benchmark_runner.py`, `scripts/`) and the query data files. Existing `.md` docs were **not** used as a source of truth.
**Method:** Every file was read directly. Pyflakes was run over all files. The parser bugs (#9, #10, #11) were confirmed with small runnable tests.

Severity guide:
- **Critical:** the benchmark/training results are not trustworthy until fixed.
- **High:** real bugs that distort reported numbers.
- **Medium:** correctness or reproducibility problems with smaller impact.
- **Low:** cleanup.

---

## Critical — the current results are unreliable

### 1. Training features leak the label
- **Where:** [run_experiment.py:604-610](../run_experiment.py), [src/extractor/gtd.py:276](../src/extractor/gtd.py)
- **Problem:** The graph-change (GTD) features are computed from the embedding drift of the *same* commit pair being labelled. `gtd_change_class = 3` whenever drift > 0. Global features (`sm_mean_drift`, `sm_drift_variance`, …) also come from this drift.
- **Impact:**
  - Under `cosine_threshold`, drift > 0 is almost the label itself.
  - Under `leave_one_out`, drift > 0 is a precondition for a positive label.
  - In real use, drift can't be known without re-embedding, which is the very cost the predictor is meant to avoid.
- **Fix:** Drop drift-derived features from the GTD inputs, or use drift from the *previous* pair only.

### 2. The benchmark feeds the model different features from training (train/serve skew)
- **Where:** [src/benchmarking/model_runner.py:127](../src/benchmarking/model_runner.py), [:140-148](../src/benchmarking/model_runner.py); compare with [run_experiment.py:629-643](../run_experiment.py)
- **Problem:**
  - At benchmark time, `gtd=None`, `modification_history={}` and `previous_drifts={}`. Every GTD, history and previous-drift feature is therefore 0, although they were non-zero in training.
  - `modified_entities` means different things:
    - **Training:** the entity's normalized AST changed (cosmetic changes are filtered out).
    - **Benchmark:** any entity in a touched file.
- **Impact:** The model is scored on input data it never saw in training, so `predictive_ml` results don't measure the trained model.
- **Fix:** Use one shared feature-building function for training and inference. Use the same definition of "modified" in both. Drop features that can't be computed at inference time.

### 3. Two different contextual embedding representations
- **Where:** [run_experiment.py:423-491](../run_experiment.py) (training) vs [src/benchmarking/index_builder.py:58-76](../src/benchmarking/index_builder.py) (benchmark)
- **Problem:**
  - Training appends signature stubs plus a one-line context for each callee.
  - The benchmark appends `Depends on <name> (ver: <md5>): <doc>`.
  - The MD5 hash changes on *any* callee edit, including whitespace or comments. This forces every caller's vector to change.
- **Impact:** The "indirect drift" gap ("Min Cosine Sim = 0.9988" for `changed_only` vs 1.0000 for `fixed_hop`) comes from the hash string, not from a real change in meaning. It favours propagation-based strategies by construction. The ground-truth labels also come from a different representation from the one evaluated.
- **Fix:** Use one shared context builder in both pipelines. Remove the version hash, or justify it explicitly.

### 4. The statistical test does not affect the label
- **Where:** [src/embedder/ground_truth.py:303-307](../src/embedder/ground_truth.py)
- **Problem:** The label is `displaced_query_count >= 1 and pos_count >= 1`. `p_val` is computed but never used, and `alpha` is ignored. Also, `displaced >= 1` already implies `pos_count >= 1`, so the label is simply "any displacement".
- **Also:**
  - The module docstring says entities with fewer than **3** queries are uncovered, but `DEFAULT_MIN_QUERIES = 5` ([:227](../src/embedder/ground_truth.py)).
  - Dead code: the first `displaced_mask` at [:124-125](../src/embedder/ground_truth.py) is overwritten at [:140](../src/embedder/ground_truth.py).
- **Fix:** Apply `p_val < alpha` in the label rule, or update the documentation and claims. Reconcile the minimum-query count.

### 5. `benchmark_settings.json` is never loaded
- **Where:** [src/benchmarking/config.py:198](../src/benchmarking/config.py), [benchmark_runner.py](../benchmark_runner.py)
- **Problem:** `load_config` reads JSON only when `--config` is passed. Nothing passes it, and nothing references `benchmark_settings.json`.
- **Impact:** `python benchmark_runner.py` runs with the defaults:
  - `query_mode=hybrid` and `curated_queries.json`
  - `commit_stride=1`
  - no `model_path`, so `predictive_ml` silently falls back to `changed_only`

  Even with `--config benchmark_settings.json`, the referenced `results/results_all-MiniLM-L6-v2_contextual_commits10_stride20_cleanFalse_20261008_203709/drift_predictor.pkl` does not exist locally, because `results/` is gitignored.
- **Fix:** Auto-load `benchmark_settings.json`, or document `--config`. Fail loudly when `model_path` is set but missing, instead of only warning.

### 6. The `black` query set is neither sanitized nor fully covered
- **Where:** [scripts/build_black_sanitized_dataset.py:117-124](../scripts/build_black_sanitized_dataset.py), `src/benchmarking/data/curated_queries_black_sanitized_5x.json`
- **Findings (measured on the file):**
  - **Ambiguous queries:** 130 distinct query texts map to more than one target, e.g. "Which component coordinates init?" goes to 3 different `__init__` methods. These are guaranteed misses for every strategy.
  - **Docstring copies:** 3 of the 7 templates paste the docstring word for word, and that docstring is part of the embedded entity text. This is lexical leakage that makes retrieval close to trivial.
  - **Name leakage:** the name-based templates use the identifier split into words ("visit default", "init", "is …"). The sanitizer blocks only the exact full name.
  - **Coverage:**
    - 280 of 687 targets have fewer than 5 queries (min 3), so they are uncovered under `DEFAULT_MIN_QUERIES=5`.
    - The file covers 687 entities, not the claimed 729.
  - **Repo side effect:** the script runs `checkout_commit("main")` on `workspace/black`.
- **Fix:**
  - Remove multi-target texts.
  - Paraphrase the docstring queries instead of copying them.
  - Block identifier tokens, not only the full name.
  - Make sure every target has at least 5 queries.

---

## High — bugs that distort reported numbers

### 7. Update cost is taken from the first commit pair only
- **Where:** [src/benchmarking/runner.py:461-471](../src/benchmarking/runner.py)
- **Problem:** The loop `break`s on the first comparison for the strategy.
- **Fix:** Average `updated_fraction` across all pairs, or sum updated and total counts across pairs.

### 8. Entities added after the first pair are never tracked
- **Where:** [src/benchmarking/strategy_runner.py:31-37](../src/benchmarking/strategy_runner.py), [src/benchmarking/model_runner.py:109](../src/benchmarking/model_runner.py), [src/benchmarking/cache_tracker.py:91-98](../src/benchmarking/cache_tracker.py)
- **Problem:**
  - `_get_stateful_changed_entities` uses `get_all_anchors().get(eid, "")` and skips empty anchors.
  - `ModelRunner` defaults missing anchors to `current_commit`, which gives a score of 0.
  - New entities get embedded once (because they are missing from the cache) but are never registered with the tracker.
- **Impact:** Later edits to those entities are never re-embedded by any selective strategy.
- **Fix:** Register newly appearing entities with anchor = `commit_after` when they are first embedded.

### 9. `fixed_hop` misses dependents (depth-limited DFS)
- **Where:** [src/parser/tree_sitter_repo_parser.py:582](../src/parser/tree_sitter_repo_parser.py), and `get_dependencies` at [:592](../src/parser/tree_sitter_repo_parser.py)
- **Problem:** `nx.dfs_preorder_nodes(..., depth_limit=k)` does not find all nodes within k hops. A node first reached through a longer path is not expanded again through a shorter one.
- **Verified:** For a graph where `a3` is 2 hops from `t`, DFS returned `{a1, a2, t}` while BFS returned `{a1, a2, a3, t}`.
- **Fix:** Use `nx.single_source_shortest_path_length(reverse_graph, eid, cutoff=k)`.

### 10. Calls are credited to the wrong method
- **Where:** [src/parser/tree_sitter_repo_parser.py:396-401](../src/parser/tree_sitter_repo_parser.py)
- **Problem:** The caller is resolved as the first entity ID in the file ending in `::<name>`, ignoring the enclosing class.
- **Verified:** With `A.__init__` calling `helper_a` and `B.__init__` calling `helper_b`, the graph contained `A::__init__ → helper_a` and `A::__init__ → helper_b`. `B::__init__` had no edges.
- **Impact:** Corrupts the call graph, `fixed_hop`, contextual embeddings, graph features and synthetic caller queries. Very common names (`__init__`, `visit_*`, `__repr__`) are affected.
- **Fix:** Track the current class during the scan and build the ID with `_get_entity_id(file, class, name)`.

### 11. `param_count` counts punctuation
- **Where:** [src/parser/tree_sitter_repo_parser.py:159](../src/parser/tree_sitter_repo_parser.py)
- **Verified:** `def f()` gives 2, `def f(x, y)` gives 5.
- **Impact:** This is a model feature, and every function gets `param:signature_args` in semantic coverage.
- **Fix:** Count only `named_children`, excluding `self` and `cls` if desired.

### 12. "Changed" means any entity in a touched file
- **Where:** [src/benchmarking/runner.py:225-228](../src/benchmarking/runner.py), [src/benchmarking/strategy_runner.py:44-47](../src/benchmarking/strategy_runner.py)
- **Impact:**
  - Unchanged functions in an edited file are labelled `changed_entity` / `latest_snapshot` and re-embedded by `changed_only`.
  - Both the freshness and cache-preservation splits are distorted.
- **Fix:** Compare entity source between snapshots (normalized AST, as Pipeline A does).

### 13. MRR and rank agreement count misses
- **Where:** [src/benchmarking/runner.py:335-342](../src/benchmarking/runner.py), [:437-449](../src/benchmarking/runner.py), [src/common/retrieval_metrics.py:60](../src/common/retrieval_metrics.py)
- **Problem:**
  - Only the top 10 is retrieved, so a miss gets rank 11 and still adds 1/11 to MRR.
  - Two misses (11 == 11) count as "rank agreement".
  - nDCG uses a hard-coded 10 instead of `top_k`.
- **Fix:** Retrieve the full ranking (as the ground-truth code does), or give misses an MRR of 0 and exclude them from agreement.

### 14. `commit_stride` is ignored in `adjacent` mode
- **Where:** [src/benchmarking/commit_sampler.py:73-75](../src/benchmarking/commit_sampler.py)
- **Impact:** `"commit_stride": 20` in `benchmark_settings.json` has no effect with `"sampling_mode": "adjacent"`.

### 15. Multi-seed runs are identical
- **Where:** [src/benchmarking/runner.py:95-97](../src/benchmarking/runner.py)
- **Problem:** `seed` is never used for sampling or anything else, so every run is the same. Reported std is always 0, and "mean ± std over N seeds" is meaningless.

### 16. Confidence intervals are claimed but never computed
- **Where:** [src/benchmarking/reporting.py:19](../src/benchmarking/reporting.py) (`wilson_ci` is never called), [src/benchmarking/visualizer.py:85-94](../src/benchmarking/visualizer.py)
- **Problem:** The chart reads `_fresh_ci_lo` / `_fresh_ci_hi`, which are never set. The defaults of 0.0 draw an error bar from each freshness value down to 0.
- **Fix:** Compute Wilson CIs in `runner.py` and store them in the summaries, or remove the error bars.

---

## Medium

### 17. Pipeline A's own strategy evaluation (`run_experiment.py`)
- [:1067](../run_experiment.py): compares predicted **probabilities** against `self.threshold` (0.05 drift threshold) under LOO/hybrid labels. It should use 0.5.
- [:1233-1258](../run_experiment.py): `_generate_queries` picks queries using the ground-truth labels (75% most-drifted). Queries without a docstring contain the function and file name.
- [:1047](../run_experiment.py), [:1092-1103](../run_experiment.py): uses `self.repo_parser` (the **last** sampled commit) for entity lookups and graph strategies on every test pair, instead of `parsers_history[commit_b]`.

### 18. Training data is split twice
- **Where:** [run_experiment.py:909](../run_experiment.py), [:915](../run_experiment.py)
- **Problem:** `train_test_split_temporal` splits the training commits by `train_ratio` again. The saved model is trained on about 70% × 70% ≈ 49% of the data. The `prepare_data` result at :909 is unused.

### 19. Settings keys are silently ignored
- **Where:** [run_experiment.py:1657-1659](../run_experiment.py), [:530](../run_experiment.py)
- **Problem:**
  - `max_queries_per_entity` in `settings.json` is not a CLI argument, so it is dropped. The hybrid loader always uses 5.
  - The merge rule "override if the CLI value equals the default" also lets JSON overwrite an explicitly passed CLI value that happens to equal the default.
  - Same pattern in `src/benchmarking/config.py`.

### 20. The two configs target different repos
- **Problem:** `settings.json` now has `repo_url: test_repo_project1` (the synthetic repo), while the benchmark targets `psf/black`.
- **Also:** `parser_mode: tree_sitter` isn't a valid `run_experiment.py` choice. It's accepted only because the JSON merge bypasses argparse, and `parser_mode` is unused anyway.

### 21. Git HEAD is left wherever the last script put it
- **Problem:**
  - `run_experiment.py` checks out each sampled commit and never restores HEAD.
  - `build_black_sanitized_dataset.py` and `evaluate_models_and_metrics.py` check out `main`.
  - `GitHelper.clone_repo` runs `git pull` on a possibly detached HEAD, and it fails silently.
- **Impact:** The benchmark samples `git log -N` from the current HEAD, so its commit window depends on what ran last and may overlap the training commits.
- **Fix:** Pin explicit commit ranges, or sample from a named ref instead of HEAD.

### 22. Synthetic queries leak the file name
- **Where:** [src/benchmarking/query_sources.py:95](../src/benchmarking/query_sources.py)
- **Problem:** The template "Which component in {file_short} handles: …" contradicts the function's own docstring rule. The docstring-summary templates are also verbatim copies (same leakage as #6).

### 23. Embedding model max sequence length is changed
- **Where:** [src/embedder/embedding_manager.py:111-118](../src/embedder/embedding_manager.py)
- **Problem:** For `all-MiniLM-L6-v2` this raises `max_seq_length` from the model's own 256 to 512 (`max_position_embeddings`). Embeddings then differ from standard MiniLM, and long inputs use positions the model wasn't fine-tuned on.

### 24. Scaler is fit before the train/test split
- **Where:** [scripts/evaluate_models_and_metrics.py:136-141](../scripts/evaluate_models_and_metrics.py)
- **Problem:** Test data leaks into the scaling. The impact is small for tree models, but larger for logistic regression, MLP, SVC and KNN.

---

## Low / cleanup

- **Large benchmark output:** `store_raw_vectors` defaults to True, so `embedding_comparisons.json` stores every vector × strategy × pair.
- **Undefined names in type hints** (pyflakes). Harmless at runtime only because of `from __future__ import annotations`:
  - `Any` in [runner.py:202](../src/benchmarking/runner.py) and [ground_truth.py:165-166](../src/embedder/ground_truth.py)
  - `Optional` and `StrategyEmbeddingComparisonResult` in [serialization.py:58](../src/benchmarking/serialization.py)
- **Stray byte-order mark (BOM)** at the top of `src/benchmarking/strategy_runner.py` and `src/benchmarking/cache_tracker.py`.
- **Swallowed errors:** `except Exception: pass` in `index_builder.py`'s context code. If it fails, entities are embedded without context and nothing is logged.
- **Unused report variables:** `n_total`, `n_fresh` and `n_cache` in `reporting.py`'s strategy table loop.
- **Hard-coded saturation message:** the warning always blames identity leakage, whatever the real cause.
- **Unused docstring field:** `run_experiment._get_contextual_source` reads `dep_entity.docstring`, which `Entity` doesn't have. It always falls back to the first body line.
- **Wrong feature name:** `entity_modification_size` is file-level added+deleted lines, not entity-level.
- **Useless RSD metrics:** RSD semantic metrics use embedding magnitudes. Embeddings are normalized, so variance and entropy are always 0.
- **Semantic coverage keywords** (`jwt`, `pbkdf2`, `rbac`, …) fit only the synthetic repo. `"iso"` matches `isolation`, `is_…` etc. The scores mean nothing for `black`.
- **Dead options and dependencies:** the Joern parser modes (`--parser-mode joern_*`, `--use-joern`) do nothing, and `gitpython` / `cpgqls-client` are unused dependencies in `requirements.txt`.
- **Wasted work in curated mode:** `build_queries` always builds synthetic queries even when `query_mode == "curated"`.
- **Repeated parsing:** each pair parses `commit_before` again even though it equals the previous pair's `commit_after` in adjacent mode.

---

## Suggested fix order

1. #5: make the benchmark actually use its settings and a real model.
2. #1, #2, #3: one shared feature and context pipeline for training and benchmark, with no drift-derived features.
3. #6, #22: rebuild the query sets.
4. #9, #10, #11: parser fixes. Then re-parse, re-label and retrain.
5. #4: decide on the label rule and align the code with the docs.
6. #7, #8, #12–#16: benchmark metric fixes.
7. Medium and low items.

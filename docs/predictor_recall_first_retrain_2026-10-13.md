# Predictive ML retrain: recall-first stale-entity detection

**Date:** 2026-10-13
**Branch:** `feature/Benchmark-Polish` (all changes uncommitted)
**Repo under test:** psf/black, embeddings `sentence-transformers/all-MiniLM-L6-v2`, context chunking on

**Goal:** never skip an entity that needs re-embedding. Extra re-embeds are acceptable.

---

## TL;DR

| | `predictive_ml` at start | `predictive_ml` now |
|---|---|---|
| Needed re-embeds skipped | 95 / 553 (17.2%)¹ | **1 / 553 (0.2%)** |
| Re-embed cost | 0.4% | 5.4% |
| Lost@5 vs full re-index | 3.01% | **0.00%** |
| Exact-rank agreement with full re-index | 60.6% | **99.91%** |
| Held-out test recall / precision | 0.07 / 0.05 | **1.00 / 0.94** |

¹ The miss count was first measured after steps 1–2. The original model's misses were not counted directly, but it flagged 0–2 entities per pair in later pairs, so it missed more.

At 5.4% cost the model now misses fewer needed re-embeds than `fixed_hop` (k=2), which misses 5 at 16.6% cost. It also beats `changed_only` (24 misses at 4.3% cost) on every fidelity measure.

---

## 1. Baseline run (before any changes)

The pipeline is `run_experiment.py` (training, `settings.json`) followed by `benchmark_runner.py` (benchmark, `benchmark_settings.json`, `model_path: latest`).

### Training (18 commits, stride 30, `label_source: hybrid`)

- Labels: 26 / 5,152 positive (0.5%)
- Decision threshold 0.473 (F1-optimal on out-of-fold predictions)
- Test: F1 0.057, precision 0.048, recall 0.071, PR-AUC 0.071

### Benchmark (15 adjacent commit pairs ending at `3702ba22`, 27,345 queries per strategy)

| Strategy | Re-embeds | Lost@5 | Lost@1 | Exact-rank agreement | Same top-5 | Stale-target queries |
|---|---|---|---|---|---|---|
| `predictive_ml` | 0.43% | 3.01% | 5.30% | 60.6% | 96.6% | 25.5% |
| `changed_only` | 4.31% | 0.13% | 0.39% | 91.7% | 99.7% | 2.9% |
| `fixed_hop` (k=2) | 16.6% | 0.00% | 0.00% | 99.65% | 100% | 0.09% |
| `full_reindex` | 100% | 0 | 0 | 100% | 100% | 0 |

After the first three pairs, `predictive_ml` flagged 0–2 entities per pair, and 0 in the last four. Its agreement with a full re-index decayed from 94% to 51% over the 15 pairs.

---

## 2. Diagnosis

The first hypothesis was class imbalance. That was only partly right.

- **Imbalance was already handled.** Every classifier uses `class_weight='balanced'`, and the threshold is fitted from out-of-fold predictions.
- **The absolute count was the problem.** 26 positives (0–4 per commit pair) are too few to learn from, and oversampling would only duplicate them.
- **The label measured something different from the benchmark.** 25 of the 26 training positives were directly modified entities. The model was learning to pick a subset of modified entities, so it could never beat `changed_only`. The benchmark asks something else: is this vector different from a fresh full re-index? With context chunking, unmodified callers go stale when a callee's stub changes, and the training label almost never marked those.
- **Misses compound.** A skipped entity keeps its old vector into later pairs.

---

## 3. What we changed

### Step 1: New training label `embedded_text_changed`

An entity is positive when its embedded text (its source plus call-graph context stubs) differs between the two commits. That is exactly when its vector would differ from a full re-index, which is the benchmark's notion of staleness.

- `run_experiment.py`: new `compute_text_changed_labels()`, `sources_history` per commit, a `BINARY_LABEL_SOURCES` constant, and the CLI choice `--label-source embedded_text_changed`.

### Step 2: More training data

60 commits at stride 5 (59 pairs) instead of 18 at stride 30. The training window ends at `3702ba22~300`, well before the benchmark window, so there is no overlap.

**Result of steps 1 + 2**

| Metric | Value |
|---|---|
| Positives | 244 / 22,416 (1.1%) |
| Test F1 / precision / recall / PR-AUC | 0.905 / 1.000 / 0.826 / 0.891 |
| Benchmark cost | 3.2% |
| Lost@5 | 0.33% |
| Needed re-embeds skipped | 95 / 553 (17.2%) |

The F1-optimal threshold (0.84) favoured precision, so about 1 in 6 needed re-embeds was still skipped.

### Step 3: Recall-targeted decision threshold

- `src/predictor/predictor.py`: new `target_recall` option. `fit_decision_threshold()` picks the highest cut-off whose out-of-fold recall reaches the target, instead of maximising F1.
- `run_experiment.py`: new `--target-recall` flag; the value is recorded in the training metadata.

With the old features, `target_recall = 0.99` drove the threshold to **0**. The model re-embedded everything, which is just a full re-index.

**Out-of-fold analysis (old features)**

| Cut-off | Recall | Flagged | Missed |
|---|---|---|---|
| 0.84 | 0.660 | 0.72% | 83 |
| 0.1 | 0.766 | 2.55% | 57 |
| 0.02 | 0.930 | 6.63% | 17 |
| 0.005 | 0.980 | 17.53% | 5 |
| ~0 | 0.980 | 19.97% | 5 |

Five positives scored exactly 0, so no positive cut-off could catch them. The model lacked the signal, not just the right threshold.

What the missed positives showed:

- Every positive with `is_modified = 1` was already caught; no negative had `is_modified = 1`.
- Every miss was an entity whose embedded text changed although its own code did not.

### Step 4: Features that capture why the embedded text changes

All three features are added in `src/extractor/feature_extractor.py`, in `_get_context_change_features()`.

| Feature | Meaning | Why it is needed |
|---|---|---|
| `context_stub_changed_count` | Number of one-hop callee stubs that changed, appeared or disappeared | A caller's embedded text includes its callees' stubs |
| `modified_member_count` | For a class, the number of its methods that were modified | A class's source contains its methods |
| `own_source_changed` | The entity's raw source text differs | Comment, docstring and formatting edits change the embedded text, but the AST-normalised `is_modified` ignores them |

Supporting changes:

- `src/embedder/context_builder.py`: stub construction factored into a shared `build_callee_stubs()`, which `build_contextual_source()` now uses. The feature and the embedder therefore use identical stub text. Verified: identical output for all 684 entities in both `large_context` modes.
- `FeatureExtractor(..., parser_a=..., large_context=...)`: the new features need the earlier commit's parser. Without it they are 0.
- `run_experiment.py`: passes `parser_a` and `large_context`, and records `large_context` in the training metadata.
- `src/benchmarking/model_runner.py`: passes the anchor commit's parser and reads `large_context` from the artifact, so inference computes the same features.

**Out-of-fold analysis (with `context_stub_changed_count` and `modified_member_count`)**

| Cut-off | Recall | Flagged |
|---|---|---|
| 0.1 | 0.947 | 2.50% |
| 0.02 | 1.000 | 6.59% |

The remaining weak positives had no structural signal: comment or formatting-only edits. Adding `own_source_changed` resolved them.

---

## 4. Final results

### Training

| Metric | Value |
|---|---|
| Threshold (target recall 0.99) | 0.20; out-of-fold recall 0.996, precision 0.924 |
| Test F1 | 0.971 |
| Test precision | 0.944 |
| Test recall | 1.000 |
| Test PR-AUC | 1.000 |
| Top features | `distance_to_modified_undirected` 0.155, `data_flow_distance` 0.137, `own_source_changed` 0.118, `distance_to_modified_directed` 0.101, `gtd_change_class` 0.070, `file_lines_added` 0.055, `context_stub_changed_count` 0.055 |

### Benchmark against a full re-index

| Strategy | Re-embeds | Lost@1 | Lost@5 | Lost@10 | Exact-rank agreement | Stale-target queries |
|---|---|---|---|---|---|---|
| **`predictive_ml`** | **5.4%** | **0** | **0** | **0** | **99.91%** | **20** |
| `changed_only` | 4.3% | 28 | 19 | 19 | 91.7% | 790 |
| `fixed_hop` (k=2) | 16.6% | 0 | 0 | 1 | 99.65% | 25 |
| `full_reindex` | 100% | 0 | 0 | 0 | 100% | 0 |

Entities flagged per pair by `predictive_ml`: 42, 100, 26, 39, 10, 15, 23, 28, 40, 24, 59, 49, 12, 12, 25.

### Needed-but-skipped re-embeds

"Needed" means the entity's full re-index vector changed in that pair.

| Strategy | Skipped when needed | Old misses still stale in later pairs | Average stale vectors per pair |
|---|---|---|---|
| `full_reindex` | 0 / 553 | 0 | 0 |
| **`predictive_ml` (final)** | **1 / 553 (0.2%)** | **3** | **0.04%** |
| `fixed_hop` (k=2) | 5 / 553 (0.9%) | 1 | 0.06% |
| `changed_only` | 24 / 553 (4.3%) | 158 | 1.94% |
| `predictive_ml` (after steps 1–2) | 95 / 553 (17.2%) | 444 | 5.75% |

"Old misses still stale" counts an entity once for each later pair it stays stale.

### The one remaining miss

`src/blib2to3/pgen2/parse.py::Recorder::__init__` at pair 12 (`995e4ada → 2bc5ce8a`). Its callee `stack_copy` gained a trailing comma, which changed the stub embedded with `__init__`.

- `context_stub_changed_count` was correctly 1.
- The comma-only edit isn't "modified" under AST normalisation, so every distance feature read "far", and the model scored the entity below 0.20.
- The vector stayed at cosine 0.9987 through pair 15, with no retrieval loss.

**Possible future hardening**

- Always re-embed when `is_modified`, `own_source_changed`, `context_stub_changed_count` or `modified_member_count` is non-zero. This guarantees zero misses at about the same cost.
- Alternatively, add a monotonic constraint or more training data so those features always raise the score.

Neither was applied; the current state was accepted as is.

---

## 5. Why it works now

1. **Right target:** the label matches the benchmark's definition of stale.
2. **Enough data:** 244 positives instead of 26.
3. **Right objective:** the cut-off is chosen for recall, because a miss costs far more than an extra re-embed.
4. **Right signal:** features describe how embedded text changes indirectly (callee stubs, class members, cosmetic source edits).

Imbalance was a symptom. The root causes were the wrong label, too few positives, an F1-tuned threshold, and missing features.

---

## 6. Reproducing

Training config (stored in the session scratchpad as `settings_recall99.json`; `settings.json` was not changed). It is `settings.json` with these overrides:

```json
{
  "label_source": "embedded_text_changed",
  "num_commits": 60,
  "commit_stride": 5,
  "target_recall": 0.99
}
```

To reproduce without that file, copy `settings.json` with these four keys changed, then run:

```bash
python run_experiment.py --config <that settings file>
```

```bash
python benchmark_runner.py --config benchmark_settings.json
```

### Artifacts

- Model: `results/results_all-MiniLM-L6-v2_contextual_commits60_stride5_cleanFalse_20261013_215900/drift_predictor.pkl`
- Benchmark: `benchmark_runs/benchmark_v1.0_seed13_a4032dce_cf4cc298/`. The run ID depends only on the settings, so each benchmark run overwrote this folder; the numbers for earlier runs are recorded in this document.

### Known gaps

- `scripts/build_custom_notebook.py`, `scripts/compare_with_and_without_direct_supply.py` and `scripts/evaluate_models_and_metrics.py` construct `FeatureExtractor` without `parser_a`, so the three new features are 0 there.
- The training log still prints "leave_one_out labels: …" for every binary label source; this is cosmetic.

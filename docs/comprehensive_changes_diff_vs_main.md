# Comprehensive Engineering & Methodological Diff: `hybrid-ground-truth` vs. `main`

**Status:** Technical Change Log & Architectural Diff Specification  
**Source Branch:** `hybrid-ground-truth` (Remediated State)  
**Target Branch:** `main` (Baseline State)  
**Evaluated Scope:** 27 modified repository files (+3,290 insertions, -1,162 deletions) + 17 new untracked modules, scripts, and datasets.

---

## 1. Executive Summary of Changes

The primary objective of the `hybrid-ground-truth` branch is to transform **Predictive Semantic Cache Invalidation (Pipeline A)** from a self-referential distance heuristic into a publication-grade, mathematically defensible, and operationally grounded machine learning system.

### Key Architectural Transformations vs. `main`:
1. **Replacement of Self-Referential Labels:** Replaced the arbitrary cosine threshold ($y = \mathbb{I}(1 - \cos \ge 0.05)$) with an **In-Memory Leave-One-Out (LOO) Top-$K$ Rank Displacement Target Label** ($Y_i \in \{0, 1\}$).
2. **Elimination of Statistical Paradoxes:** Replaced the continuous Wilcoxon signed-rank test and its `underpowered` bypass bug with an **Exact One-Sided Binomial Sign Test** ($H_1: P(\Delta \text{nDCG} > 0) > 0.5$) using `scipy.stats.binomtest`.
3. **Strict Query Coverage Bounds:** Uncovered entities ($M_q < 3$ queries) are marked `is_covered=False` and **dropped from training set $Y$** rather than assigned ad-hoc fallback labels.
4. **Lexical Target Leakage Remediation:** Enforced a **Lexical Target Sanitization Protocol** on synthetic query workloads, removing exact AST function names (`short_name`) and relative file paths (`file_p`) from query text to eliminate token matching bias.
5. **Decoupled Features vs. Target Labels:** Decoupled `is_direct_edit` from target label $Y$, feeding it strictly as a model input feature $X$ to `RandomForestClassifier`.

---

## 2. Subsystem-by-Subsystem Technical Breakdown

### 2.1 Embedder & Ground-Truth Core (`src/embedder/ground_truth.py`)

| Feature / Logic | `main` Branch | `hybrid-ground-truth` Branch (Current) |
| :--- | :--- | :--- |
| **Statistical Test Engine** | Continuous Wilcoxon Signed-Rank Test (`scipy.stats.wilcoxon`) | **Exact Binomial Sign Test** (`scipy.stats.binomtest`) via `compute_exact_binomial_sign_test` |
| **Small Sample Handling** | `significant or underpowered` bypass bug (bypassed $p < 0.05$ for $N < 5$, forcing false positives) | **Strict Exclusion:** Entities with $M_q < 3$ queries are flagged `is_covered=False` and excluded from training $Y$ |
| **Data Class Schema** | `GroundTruthLabel` (contains `underpowered: bool`) | `StrictGroundTruthLabel` (contains `is_covered: bool`, `positive_delta_count: int`, exact $p$-value) |
| **Label Binarization** | `binarize_ground_truth()` with arbitrary $N \in [1, 5]$ thresholds | `compute_strict_ground_truth()` requiring BOTH Top-$K$ displacement ($D \ge 1$) AND exact sign test $p < 0.05$ |

---

### 2.2 Benchmarking & Shared Retrieval Metrics (`src/common/retrieval_metrics.py`, `src/benchmarking/`)

* **Extracted Retrieval Primitives (`src/common/retrieval_metrics.py`):**
  - Created shared, vectorized retrieval functions (`compute_ranks`, `top_k_hit`, `compute_ndcg`) used identically by both training label generation and strategy evaluation.
* **Semantic Coverage Framework (`src/benchmarking/semantic_coverage.py`):**
  - Implemented semantic coverage metric $SC(e, Q)$ measuring query coverage across 5 code dimensions: `intent:core_functionality`, `param:signature_args`, `error:exception_handling`, `domain:*`, and `method:*`.
* **Extended Benchmarking Types (`src/benchmarking/types.py` & `config.py`):**
  - Extended `QueryCase`, `RepositorySnapshot`, `CommitPair`, and `StrategyConfig` to support multi-query evaluations and strict ground truth parameters.

---

### 2.3 Query Workload Datasets (`src/benchmarking/data/`)

* **`curated_queries_perfect_sc.json` (New File - 408 Queries):**
  - Synthetic query dataset providing 100% semantic coverage ($SC = 1.00$) across all 90 AST entities in `test_repo_project1`.
* **`curated_queries_sanitized_sc.json` (New File):**
  - Sanitized query dataset passing the Lexical Target Sanitization Protocol (zero AST name or file path token leakage).
* **Query Loader Enhancements (`src/benchmarking/query_sources.py`):**
  - Added support for loading curated queries, fallback synthetic query generation, and string normalization.

---

### 2.4 Predictor & Experiment Pipeline (`src/predictor/predictor.py`, `run_experiment.py`)

* **Configurable Target Label Source (`run_experiment.py`):**
  - Added `label_source` parameter (`"cosine_threshold"` vs. `"leave_one_out"` / `"strict_leave_one_out"`).
* **Decoupled Feature Engineering (`src/predictor/predictor.py`):**
  - `is_direct_edit` (whether an entity's file was modified in `git diff`) is passed strictly as a feature in feature vector $X$, allowing `RandomForestClassifier` to learn git diff relationships without overriding ground truth $Y$.
* **Notebook Generators (`scripts/build_notebook.py`, `scripts/build_custom_notebook.py`):**
  - Updated automated notebook generators to render the updated pipeline, strict ground-truth dataset comparisons, and Pareto frontier plots.

---

## 2.5 Directory of New Files Added vs. `main`

The following 17 untracked files were created to support testing, audit analysis, query generation, and documentation:

```
docs/
├── phd_ground_truth_audit_and_remediation_framework.md   # PhD audit report & theoretical proofs
└── comprehensive_changes_diff_vs_main.md               # This technical change log

scripts/
├── test_ground_truth_pipeline.py                       # Chronological commit audit script (C0->C9)
├── build_perfect_semantic_coverage_dataset.py          # 100% SC query dataset generator
├── evaluate_models_and_metrics.py                       # Model evaluation & Pareto curve generator
├── build_synthetic_test_repo.py                         # 10-commit synthetic repository builder
├── compare_audit_vs_empirical_csv.py                   # CSV comparison utility
├── compare_with_and_without_direct_supply.py           # Feature ablation script
├── evaluate_current_semantic_coverage.py               # SC evaluation utility
├── generate_5_queries_per_entity.py                    # Multi-query generator
├── generate_per_commit_entity_md.py                    # Commit entity summary generator
└── test_dynamic_diff_queries.py                        # Dynamic query test script

src/benchmarking/
├── semantic_coverage.py                                 # Semantic coverage (SC) calculation engine
└── data/
    ├── curated_queries_perfect_sc.json                 # 408-query dataset (100% SC)
    ├── curated_queries_sanitized_sc.json               # Sanitized non-leaky query dataset
    ├── curated_queries_synthetic.json                 # Synthetic baseline query set
    └── curated_queries_synthetic_5x.json              # 5x synthetic query set
```

---

## 3. Empirical Performance & Label Distribution Comparison

Evaluating 803 total entity-commit pairs across 10 chronological commits ($C0 \rightarrow C9$) on `test_repo_project1`:

| Metric / Property | `main` Branch (Baseline Cosine) | `hybrid-ground-truth` (Remediated Branch) |
| :--- | :--- | :--- |
| **Label Definition** | $1 - \cos(\mathbf{e}_{\text{before}}, \mathbf{e}_{\text{after}}) \ge 0.05$ | Top-$K$ Displacement ($D \ge 1$) AND Exact Sign Test ($p < 0.05$) |
| **Statistical Test** | None (Raw distance threshold) | **Exact One-Sided Binomial Sign Test** (`binomtest`) |
| **Small Sample Rule** | N/A | Excludes $M_q < 3$ entities from $Y_{\text{train}}$ (`is_covered=False`) |
| **Direct Edit Rule** | Overrode label if file modified | Decoupled as Feature $X$; target $Y$ strictly operational |
| **Positive Rate ($Y=1$)** | ~45.2% (Heuristic inflation) | **11.83%** (95 / 803 entity-commit pairs, strictly grounded) |
| **Circularity Status** | Self-referential vector cutoff | Operationally grounded in retrieval displacement |

---

## 4. Verification Command Checklist

To verify all changes against `main` and run the strict ground-truth evaluation pipeline:

```bash
# 1. Run strict ground-truth pipeline audit across 10 chronological commits
python scripts/test_ground_truth_pipeline.py

# 2. Re-evaluate semantic coverage metrics across entity workload
python scripts/evaluate_current_semantic_coverage.py

# 3. Train DriftPredictor on strict ground truth and evaluate Pareto frontier
python run_experiment.py
```

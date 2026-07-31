# Implementation Plan: Benchmarking Pipeline Refactor

This document serves as the authoritative reference for refactoring and enhancing the `src/benchmarking` evaluation framework.

---

## 1. Executive Summary & Objective

The primary objective of this refactor is twofold:
1. **Direct Embedding Quality Comparison**: Introduce a dedicated vector-level comparison stage that directly evaluates cosine similarity and semantic representation drift between baseline embeddings and selective candidate embeddings *prior* to search query retrieval.
2. **Multi-Strategy Pipeline Scaling**: Refactor the pipeline architecture so that multiple invalidation strategies (`changed_only`, `fixed_hop`, `predictive_drift`, `full_reindex`) can be evaluated in a single pass against the ground-truth baseline, producing comparative Pareto trade-off analyses (Maintenance Cost vs. Embedding Fidelity vs. Retrieval Quality).

---

## 2. Architecture & Refactored Data Flow

```
                        [Git Repository & Commits]
                                    │
                                    ▼
                       [1. Commit Pair Sampler]
                        (adjacent / stride)
                                    │
                                    ▼
             ┌──────────────────────────────────────────────┐
             │ 2. Git Entity Snapshotter (AST Walk)         │
             │    - before_snapshot  (Commit A)             │
             │    - after_snapshot   (Commit B)             │
             └──────────────────────┬───────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              ▼                                           ▼
  [3. Ground-Truth Baseline Index]           [4. Multi-Strategy Dispatcher]
  (Full re-index of Commit B)                 Generates Candidate Indices for
              │                               $S_i \in$ {changed_only, fixed_hop, ...}
              │                                           │
              └─────────────────────┬─────────────────────┘
                                    │
                                    ▼
                     [5. Direct Embedding Comparator]
                     Computes Cosine Similarity & Vector Drift
                     for all entities in Commit B (S_i vs Baseline)
                                    │
                                    ▼
                       [6. Dual Top-K Retrieval]
                  Queries ran against Baseline & Candidate S_i
                                    │
                                    ▼
                    [7. Metric & Pareto Evaluator]
              Calculates Cost C(S_i), Fidelity V(S_i), Quality Q(S_i)
                                    │
                                    ▼
                [8. Artifact Serialization & Reporting]
              `embedding_comparisons.json`, `per_query_results.jsonl`,
              `summary_metrics.json`, and `summary_report.md`
```

---

## 3. Module Breakdown & Required Changes

### 3.1 Datatypes (`types.py`)
- **`EntityEmbeddingComparison`**:
  - `entity_id: str`: Canonical ID (`file_path::Class::method`).
  - `entity_type: str`: `"class"`, `"method"`, or `"function"`.
  - `file_path: str`: Target file path.
  - `status: str`: `"unchanged"`, `"modified"`, or `"added"`.
  - `cosine_similarity: float`: Vector dot product $\mathbf{v}_{\text{baseline}} \cdot \mathbf{v}_{\text{candidate}}$.
  - `semantic_drift: float`: $1.0 - \text{cosine\_similarity}$.
  - `baseline_raw_vector: Optional[List[float]]`: Raw vector payload (when raw vectors enabled).
  - `candidate_raw_vector: Optional[List[float]]`: Raw vector payload (when raw vectors enabled).
- **`StrategyEmbeddingComparisonResult`**:
  - `strategy_name: str`
  - `total_entities: int`
  - `mean_cosine_similarity: float`, `min_cosine_similarity: float`, `p95_cosine_similarity: float`
  - `updated_fraction: float`
  - `per_entity_comparisons: List[EntityEmbeddingComparison]`
- **`BenchmarkConfig` Update**:
  - `strategies: List[str] = field(default_factory=lambda: ["changed_only"])`
  - `compare_embeddings: bool = True`
  - `store_raw_vectors: bool = True`

### 3.2 Configuration Helpers (`config.py`)
- Add parser CLI options:
  - `--strategies`: Comma-separated strategy list (e.g. `changed_only,full_reindex`).
  - `--compare-embeddings` / `--no-compare-embeddings`.
  - `--store-raw-vectors` / `--no-store-raw-vectors`.

### 3.3 Direct Embedding Comparator (`embedding_comparator.py`)
- **`compare_index_snapshots(baseline_snapshot, candidate_snapshot, modified_files, strategy_name, store_raw_vectors)`**:
  - Iterates over all entities in Commit $B$.
  - Extracts baseline vector $\mathbf{v}_{\text{baseline}}$ and candidate vector $\mathbf{v}_{\text{candidate}}$.
  - Computes $\text{cosine\_similarity} = \mathbf{v}_{\text{baseline}} \cdot \mathbf{v}_{\text{candidate}}$.
  - Categorizes status (`modified` if in `modified_files`, `added` if missing in $A$, `unchanged` otherwise).
  - Computes aggregate metrics (mean similarity, min similarity, $p_{95}$ similarity).

### 3.4 Multi-Strategy Strategy Runner (`strategy_runner.py`)
- Expand `decide_updated_entities` to support:
  - `"full_reindex"`: updates 100% of entities.
  - `"changed_only"`: updates entities in modified files.
  - `"fixed_hop"`: updates modified files + 1-hop dependent entities.
  - `"predictive_drift"`: placeholder dispatch for ML drift model predictions.

### 3.5 Orchestrator (`runner.py`)
- Refactor `run_benchmark` to loop over all requested strategies:
  ```python
  for strategy_name in config.strategies:
      # 1. Decide updated entities
      # 2. Build candidate selective snapshot
      # 3. Perform direct embedding comparison against baseline snapshot
      # 4. Perform retrieval query evaluation against candidate snapshot
      # 5. Aggregate metrics per strategy
  ```

### 3.6 Serialization & Reporting (`serialization.py`, `reporting.py`)
- **`serialization.py`**:
  - Serialize per-strategy embedding comparison records to `embedding_comparisons.json`.
  - Record strategy vector fidelity stats inside `summary_metrics.json`.
- **`reporting.py`**:
  - Add section **"## Direct Embedding Quality & Vector Fidelity"**.
  - Add **Pareto Trade-off Analysis Table** comparing:
    - `Strategy`
    - `Updated Fraction C(S)` (Maintenance Cost)
    - `Mean Cosine Sim V(S)` (Vector Fidelity)
    - `Query MRR Q(S)` (Retrieval Quality)
    - `Query NDCG@10`

---

## 4. Implementation Task Checklist

- [ ] **Task 1**: Update [types.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/types.py) with comparison dataclasses and config fields.
- [ ] **Task 2**: Update [config.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/config.py) with CLI flags (`--strategies`, `--compare-embeddings`, `--store-raw-vectors`).
- [ ] **Task 3**: Create [embedding_comparator.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/embedding_comparator.py) containing direct vector dot product comparison and status categorization.
- [ ] **Task 4**: Update [strategy_runner.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/strategy_runner.py) for strategy dispatching.
- [ ] **Task 5**: Refactor [runner.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/runner.py) to support the multi-strategy comparative pipeline.
- [ ] **Task 6**: Update [serialization.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/serialization.py) and [reporting.py](file:///c:/Users/kmohn/New%20folder/Project-1/src/benchmarking/reporting.py) to render vector fidelity metrics and Pareto analysis tables.
- [ ] **Task 7**: Create unit test suite in `tests/test_benchmark_embedding_comparator.py`.
- [ ] **Task 8**: Execute unit tests and run end-to-end benchmark smoke verification.

---

## 5. Verification & Testing

### Automated Test Command
```powershell
./venv/Scripts/python.exe -m unittest discover -s tests -p 'test_benchmark_*.py'
```

### Manual Execution & Artifact Verification
```powershell
./venv/Scripts/python.exe benchmark_runner.py --repo-path . --output-dir benchmark_runs --num-commits 2 --query-mode synthetic --max-queries-per-entity 1 --strategies changed_only
```
Verify generated output files under `benchmark_runs/`:
- `benchmark_config.json`
- `commit_pairs.json`
- `queries.json`
- `embedding_comparisons.json`
- `per_query_results.jsonl`
- `summary_metrics.json`
- `summary_report.md`

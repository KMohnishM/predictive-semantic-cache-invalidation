# Implementation Notes — Problem Statement 2
# Dependency Graph Change Problem (Graph Transition Descriptor)

## Problem Recap

Our original `FeatureExtractor` used only basic hop-distance heuristics
(`distance_to_modified_directed`, `distance_to_modified_undirected`,
`modified_dependents_count`) to capture how changes propagate through the
codebase.  These are coarse approximations that do not formally model *how
the dependency graph itself evolved* between two commits.

---

## What Was Implemented

### New File: `src/gtd.py`

Class **`GraphTransitionDescriptor`** that computes a structured numerical
fingerprint of the graph transition $G_t \to G_{t+1}$.

#### Step 1 — Node-Level Diff (`_node_diff`)

| Metric | Description |
|--------|-------------|
| `node_added_ratio` | Fraction of nodes new in G_{t+1} |
| `node_deleted_ratio` | Fraction of nodes removed |
| `node_modified_ratio` | Fraction of shared nodes with drift > 0 |
| `node_unchanged_ratio` | Fraction of shared nodes with no drift |
| `node_survival_ratio` | Fraction of nodes present in both graphs |

#### Step 2 — Edge-Level Diff (`_edge_diff`)

| Metric | Description |
|--------|-------------|
| `edge_added_ratio` | New dependency edges |
| `edge_removed_ratio` | Removed dependency edges |
| `edge_churn` | Total fraction of edges that changed |
| `density_delta` | Absolute change in graph density |

#### Step 3 — Structural Evolution (`_structural_evolution`)

| Metric | Description |
|--------|-------------|
| `node_growth_ratio` | Relative change in node count |
| `edge_growth_ratio` | Relative change in edge count |
| `clustering_delta` | Change in average clustering coefficient |
| `component_delta` | Relative change in #weakly connected components |

#### Step 4 — Centrality Evolution (`_centrality_evolution`)

| Metric | Description |
|--------|-------------|
| `mean_pagerank_shift` | Mean PageRank change across shared nodes |
| `max_pagerank_shift` | Maximum PageRank change |
| `mean_degree_shift` | Mean degree change across shared nodes |

#### Step 5 — Semantic Evolution (`_semantic_evolution`)

| Metric | Description |
|--------|-------------|
| `mean_drift` | Mean cosine drift across all entities |
| `drift_variance` | Variance of drift values |
| `drift_entropy` | Entropy of drift histogram |
| `high_drift_ratio` | Fraction of entities drifting > 2× mean |

#### Step 6 — Per-Node Impact Features (`_node_impact_features`)

For every entity, the GTD also provides:
- `gtd_change_class` — 0=unchanged, 1=added, 2=deleted, 3=modified
- `gtd_local_edges_added` — edges added touching this node
- `gtd_local_edges_removed` — edges removed touching this node
- `gtd_local_edge_churn` — total local edge changes

### Integration in `src/feature_extractor.py`

Two new methods added to `FeatureExtractor`:

1. **`_get_pagerank_impact_feature(entity_id, modified_entities)`**
   - Computes **Personalised PageRank** seeded on the set of modified nodes
   - Every entity receives a score proportional to how much random-walk probability flows to it from changed nodes
   - Returns `{"pagerank_impact": float}` — replaces the coarse hop-distance as the primary propagation signal
   - PPR is cached per modified-entity set to avoid redundant computation

2. **`_get_gtd_features(entity_id, gtd)`**
   - Reads both per-node and global GTD metrics
   - Returns 12 new feature columns prefixed with `gtd_`:
     - `gtd_change_class`, `gtd_local_edges_added/removed/churn` (per-node)
     - `gtd_mean_drift`, `gtd_drift_variance`, `gtd_edge_churn`, `gtd_density_delta`, `gtd_node_growth_ratio`, `gtd_clustering_delta`, `gtd_mean_pagerank_shift`, `gtd_high_drift_ratio` (global)

### Integration in `run_experiment.py`

Inside `build_dataset()`, for each consecutive commit pair:
1. A `GraphTransitionDescriptor` is instantiated and `gtd.compute(parser_a, parser_b, drifts)` is called
2. The GTD is passed as `gtd=gtd` to `compute_drifts_and_features()`
3. After drifts are computed, GTD is recomputed with the real drift values (first pass uses empty drifts as bootstrapping)
4. All GTDs stored in `self.gtd_history`

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Two-pass GTD (empty drifts → then real drifts) | Drifts require embeddings which are generated after GTD is first needed for feature extraction; bootstrapping with empty drifts is safe because the global semantic metrics are only for context |
| PPR cached per seed set | The same modified-entity set is used for every entity in a commit pair — computing PPR once and reusing is essential for performance |
| 12 new features total | Keeps the feature space manageable while covering all 5 GTD components |
| Global metrics same for all entities in a pair | This is correct — density change, clustering shift, etc. are graph-level properties, not per-node |

---

## New Strategy: `BaselineDPageRankPropagation` (in `src/evaluator.py`)

A new cache invalidation strategy that directly uses the PPR scores computed
by GTD to decide which entities to re-embed:

1. Run personalised PageRank seeded on modified nodes
2. Always include modified nodes in the update set
3. Add the top `top_fraction` (default 30%) of remaining entities sorted by PPR score

This is compared against the fixed K-hop baseline in the strategy evaluation.

---

## Files Changed

| File | Change |
|------|--------|
| `src/gtd.py` | **New** — full GTD implementation |
| `src/feature_extractor.py` | Added `_get_pagerank_impact_feature`, `_get_gtd_features`, updated `extract_features` and `extract_features_batch` signatures |
| `src/evaluator.py` | Added `BaselineDPageRankPropagation` strategy class |
| `run_experiment.py` | GTD computation and storage per commit pair, `gtd=` parameter threading |

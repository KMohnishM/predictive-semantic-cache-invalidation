# Implementation Notes — Problem Statement 1
# Repository State Descriptor (RSD)

## Problem Recap

Our original pipeline split commits into train / test using a simple percentage cut
(e.g. first 70% = train).  This is statistically weak: a repository may have 20
quiet commits followed by 5 massive refactoring commits.  If the chaotic commits
land in test, the model looks artificially good (or bad) without any signal change.

---

## What Was Implemented

### New File: `src/rsd.py`

Class **`RepositoryStateDescriptor`** that converts every commit into a
5-dimensional numerical fingerprint:

```
R(C_i) = (S, T, M, C, E)
```

| Dimension | Name | Metrics Used |
|-----------|------|-------------|
| S | Scale | entity count, class count, function count, LOC, avg function length |
| T | Topology | nodes, edges, avg degree, density, #components, clustering coeff, avg PageRank |
| M | Semantic | avg pairwise cosine similarity, embedding variance, entropy of magnitudes |
| C | Complexity | avg fan-in, avg fan-out, avg LOC per entity, import diversity |
| E | Evolution | avg historical churn, modification frequency, avg prior drift, relative age |

**Normalisation:** Robust Scaling (IQR-based), clips to [−3, 3] then maps to [0, 1].
**Weighting:** Entropy Weight Method — metrics with higher information content get larger weights. No manual tuning needed.

### Integration in `run_experiment.py`

1. `Experiment.__init__` now holds `self.rsd = RepositoryStateDescriptor()`
2. After each commit is parsed + embedded in `build_dataset()`, `rsd.add_commit()` is called to record raw metrics.
3. After the full commit loop, `rsd.build_all_rsds()` normalises all metrics globally and produces the 5D vectors.
4. `rsd.stratified_split()` clusters commits using **K-Means (k=3)** on the RSD space.  Within each cluster, commits are assigned to train / test proportionally while preserving temporal order.
5. The final split replaces the naive percentage cut.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Lazy build (collect raw → normalise together) | Robust Scaling needs all values to compute IQR; must see all commits first |
| `k=3` clusters | Typical repos have 3 "phases": early, growth, mature. Adjustable. |
| Temporal ordering preserved within clusters | Avoids data leakage (future commits should not be in train) |
| Fallback to simple split if < 6 commits or sklearn missing | Graceful degradation for tiny test runs |

---

## How to Verify

After running the experiment you will see a log line:

```
[RSD] Stratified split → train=X, test=Y across 3 clusters
```

followed by an RSD summary table:

```
Commit      S        T        M        C        E
--------  ------   ------   ------   ------   ------
abc12345  0.4231   0.6120   0.3345   0.5012   0.1234
...
```

Commits with very different RSD vectors (e.g. a large refactoring commit vs a
tiny bug-fix) will land in different clusters, ensuring both train and test see
representative examples of each phase.

---

## Files Changed

| File | Change |
|------|--------|
| `src/rsd.py` | **New** — full RSD implementation |
| `run_experiment.py` | Added `self.rsd`, `rsd.add_commit()` calls, `rsd.build_all_rsds()`, `rsd.stratified_split()` |

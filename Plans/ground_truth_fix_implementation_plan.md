# Implementation Plan: Ground-Truth Fix for Pipeline A (Drift Predictor)

Status: proposed — not yet started.
Prerequisite reading: [`docs/ragas_nn_proposal.md`](../docs/ragas_nn_proposal.md), [`docs/ground_truth_method_comparison.md`](../docs/ground_truth_method_comparison.md)

## Goal

Replace the predictor's self-referential, arbitrary-threshold ground-truth label (`y = binarize(1 - cosine_similarity(before, after))`) with a defensible, non-circular, statistically-grounded label — using the leave-one-out rank-displacement + Wilcoxon methodology — while reusing (not duplicating) the query-independence and rank/top-k machinery already built into `src/benchmarking/`. RAGAS is explicitly excluded from this plan; see the referenced docs for why.

## Phase 0 — Branch setup

Create `ground-truth-fix` off `main` (already has the benchmarking refactor merged in). No code changes.

## Phase 1 — Extract shared retrieval primitives

Pull the rank/top-k/freshness logic currently duplicated inside `src/benchmarking/runner.py` and `strategy_runner.py` into a new shared module, e.g. `src/common/retrieval_metrics.py`:

- `compute_ranks(query_embeddings, entity_embedding_matrix) -> ranks`
- `top_k_hit(rank, k) -> bool`
- `load_query_set(path) -> List[QueryCase]` (wraps `load_curated_queries`)

Both `src/benchmarking/runner.py` and the new ground-truth generator (Phase 3) import from here, so "same logic" is guaranteed by shared code, not by two independent implementations happening to agree.

**Done when**: `src/benchmarking/` is refactored to call the shared module and its existing outputs are unchanged (regression check — same numbers as before the refactor).

## Phase 2 — AST-canonicalization fix (independent, cheap, can run in parallel with Phase 1)

Replace `normalize_source()` in `run_experiment.py:403-418` — currently `ast.dump(ast.parse(code))`, which still treats identifier renames as "semantic" — with a canonicalizing pass (rename all local identifiers to positional placeholders before comparing dumps).

**Done when**: a synthetic test case (rename-only diff, no logic change) is correctly filtered out as cosmetic.

## Phase 3 — Leave-one-out ground truth generator (Layer 1)

New function, e.g. `src/embedder/ground_truth.py::compute_leave_one_out_labels(E_before, E_after, entity_ids, queries)`:

- For each entity `i`: build `E_stale_i` (fresh matrix with row `i` swapped back to `E_before[i]`), compute ranks for all queries against both `E_after` and `E_stale_i` using the Phase 1 shared primitives, flag displacement per `D(i, q)`:
  $$D(i, q) = \mathbb{I}\big(\text{Rank}_{\text{fresh}}(i,q) \le K \;\land\; \text{Rank}_{\text{stale\_i}}(i,q) > K\big)$$
- **Query source: `curated_queries.json` only.** Do not use `run_experiment.py::_generate_queries()` — it selects entities by the model's own drift score and builds query text from the target's own docstring, both of which reintroduce circularity.
- Output: a per-entity continuous score (fraction of queries displaced, or raw nDCG delta) — keep it continuous here, not yet binarized.

**Done when**: running this on one commit pair from `psf/black` produces a displacement score per entity, sanity-checked by hand on 2–3 known cases (a pure rename should score ~0 post-Phase-2; a real logic change to a heavily-queried entity should score high).

## Phase 4 — Statistical significance layer (Layer 2)

Add `wilcoxon_significance(entity_id, per_query_ndcg_deltas) -> p_value` using `scipy.stats.wilcoxon`. Combine with Phase 3's displacement indicator per:

$$Y_i = \begin{cases} 1 & \text{if } \big(\sum_q D(i,q) \ge 1\big) \land (p_i < 0.05) \\ 0 & \text{otherwise} \end{cases}$$

**Done when**: label distribution (fraction of entities labeled 1) is inspected for sanity — not near-0% or near-100% by construction — and a warning is logged when a Wilcoxon test is underpowered (too few paired queries for an entity) rather than silently trusting it.

## Phase 5 — Wire into `predictor.py` as a switchable label source

Add a `label_source` config option (`"cosine_threshold"` default-preserving vs. `"leave_one_out"`) in `DriftPredictor`/`run_experiment.py`, rather than ripping out the old label outright. This allows training two models on the same commits/features and comparing them directly instead of trusting the new label blind.

**Done when**: both label sources run end-to-end through `Experiment.train_model()` without touching feature extraction.

## Phase 6 — Validation loop through the existing benchmarking harness

This is the step that answers "how do we know the new label is actually better," using the separation of concerns between training-label generation (isolated, per-entity) and strategy benchmarking (joint, whole-matrix):

1. Train the predictor on the new leave-one-out label.
2. Convert its predictions into an actual strategy (re-embed whatever it flags) and register it as a candidate in `src/benchmarking/strategy_runner.py`, alongside `changed_only`, `fixed_hop`, `full_reindex`.
3. Run the **unmodified** benchmarking pipeline, get the Pareto frontier.
4. Repeat for the old-label-trained predictor.

**Done when**: two Pareto-frontier plots exist (old label vs. new label) to compare. If the new-label predictor doesn't dominate or at least match the old one on the frontier, treat that as a signal to debug upstream (Phase 1–4) rather than assuming the theory holds.

## Phase 7 — Write up results and limitations

Update [`docs/ground_truth_method_comparison.md`](../docs/ground_truth_method_comparison.md) with actual numbers from Phase 6, and add an explicit limitations section (program-equivalence undecidability, embedding blind spot) as a required section, not an afterthought.

## Sequencing

Phases 1 and 2 are independent of each other and can run in either order. Phase 3 depends on Phase 1. Phase 4 depends on Phase 3. Phase 5 depends on Phase 3/4. Phase 6 depends on Phase 5. Recommended order for a single contributor: 1 → 2 → 3 → 4 → 5 → 6 → 7, with Phase 2 slotted in whenever convenient.

# Ground-Truth & Training-Signal Design for Predictive Cache Invalidation — Full Comparison & Recommendation

Status: design summary consolidating the RAGAS_NN branch discussion.
Related: [`docs/ragas_nn_proposal.md`](ragas_nn_proposal.md)

## The question being answered

The predictor's target label is currently `y = binarize(1 - cosine_similarity(embedding_before, embedding_after), threshold)` (`src/embedder/embedding_manager.py::compute_drift`, `src/predictor/predictor.py`). We evaluated whether — and how — to replace that label/training signal with something more defensible, and whether a neural network + RAGAS-based reward is the right way to do it.

---

## Option A — Baseline: Random Forest + raw cosine-drift threshold (what exists today)

**Mechanism**: `drift = 1 - cos(e_before, e_after)`, binarized at a fixed threshold (0.05) or the 85th percentile of nonzero drifts. `RandomForestClassifier` trained on ~25 structural/evolution/code-metric features to predict it.

| Pros | Cons |
|---|---|
| Cheap, fast, fully deterministic, no LLM | Threshold is an arbitrary heuristic with no independent justification |
| Random Forest is sample-efficient — fits well at the current scale (5–10 sampled commits/run) | Label is self-referential: "ground truth" is just "did the same embedding model's own vector move past a cutoff" |
| Well understood, easy to debug/inspect (feature importances) | AST-normalization filter only strips whitespace/comments — renames, docstring edits, and reorders still count as "semantic," inflating false positives |
| Zero extra infrastructure | No independent evaluation of whether the threshold crossing actually matters for retrieval outcomes |

---

## Option B — NN + RAGAS-as-online-reward (the original idea)

**Mechanism**: randomly-initialized NN outputs a decision/embedding per commit; retrieval is run; RAGAS scores retrieval/answer quality; that score is fed back as a training signal.

| Pros | Cons |
|---|---|
| Directly optimizes for a downstream, task-relevant notion of quality rather than a raw distance proxy | **Missing cost term** — with no penalty for re-embedding, the optimal policy degenerates to "always re-embed everything," which has zero predictive value (identical to the `full_reindex` baseline already benchmarked) |
| An LLM judge reading real text can, in principle, be more sensitive to some subtle logic changes than a small sentence-transformer's cosine distance | **RAGAS is non-differentiable** (goes through top-k argsort + an LLM call) → forces reinforcement learning, not standard backprop |
| — | **RL is extremely sample-hungry**; current experiments sample only 5–10 commits/run — 2–4 orders of magnitude short of what RL from random init typically needs |
| — | RAGAS calls are slow and cost money per sample — a training loop calling it per step is impractical at any real iteration count |
| — | LLM-judge scores have known run-to-run variance/noise — a bad foundation for a reward signal |
| — | Predicting an *embedding* directly is redundant: if an entity needs re-embedding, the frozen encoder already gives you the true vector for free — that's literally what `compute_drift()` already does |
| — | Doesn't fix the underlying circularity concern about query→entity relevance (see cross-cutting issues below) — RAGAS needs you to supply that independently anyway |

**Verdict**: interesting instinct, not feasible as literally described, for reasons independent of each other (any one of them alone would sink it).

---

## Option C — 3-Layer Rank-Displacement + Wilcoxon + Pareto (the external ground-truth doc)

**Mechanism**: Leave-one-row-out simulation — swap a single entity's embedding back to its pre-commit value, recompute Top-K rankings for a query set `Q`, flag "operational staleness" only if the entity is displaced from Top-K *and* the nDCG drop is statistically significant (Wilcoxon, p<0.05). Reports a cost/quality Pareto frontier instead of one fixed operating point.

| Pros | Cons |
|---|---|
| Zero LLM calls — pure NumPy, deterministic, <100ms per pair | Still entirely computed inside the *same* embedding model's geometry — doesn't fix the "encoder blind to subtle behavioral change" false-negative problem at all |
| Fixes the missing-cost-term flaw from Option B directly — Pareto frontier makes the quality/cost tradeoff explicit instead of hiding it | "Eliminates hardcoded thresholds" is overstated — `K` and `α=0.05` are still hyperparameters, just more conventional ones |
| Ties the label to a real structural event (Top-K displacement) instead of an arbitrary distance cutoff | Circularity risk reappears if the query set `Q` is drift-conditioned or lexically leaked from the target entity — must specifically use `curated_queries.json` (independent, human-authored, fixed `target_entity_id`), **not** `run_experiment.py::_generate_queries()` (which selects entities by the model's own drift score and builds query text from the target's own docstring) |
| Statistically rigorous (Wilcoxon) — standard, well-understood, reviewer-recognizable methodology | Wilcoxon needs enough paired observations per entity to have real power — a small curated query set may under-power the test |
| Converts the whole problem back into ordinary supervised learning (precomputed offline label, standard loss) — no RL, no reward noise, no black-box optimization | Doesn't verify actual program behavior (no execution) — still fundamentally a text/embedding-space proxy, same as every other option here |
| More auditable/reproducible than an LLM-judge-based signal — nothing to defend beyond your own math | — |

**Verdict**: the strongest of the training-signal options, with three concrete, fixable gaps (query source, threshold-language honesty, and an explicit limitations section on the embedding-blind-spot).

---

## Option D — RAGAS as offline, periodic evaluation metric only (not a training signal)

**Mechanism**: after training (with whatever label — A or C), separately compute RAGAS metrics (context precision/recall, ideally) on the strategy's actual retrieval output, sampled occasionally, purely for reporting.

| Pros | Cons |
|---|---|
| Adds an LLM-judged, more code-literate quality signal alongside existing recall@k/MRR/nDCG metrics, for free (no impact on training) | Only as good as query coverage — if no query touches a subtly-changed code path, RAGAS won't reveal anything either |
| No RL, no differentiability problem, no training-loop cost blowup — it only runs once per strategy per experiment | Adds LLM cost/latency/noise to the *evaluation* stage — manageable if sampled sparingly, but not free |
| Useful for the "does our predictive strategy hold up under a richer judge" story in a writeup/defense | Doesn't change or improve the ground truth used to train the model at all — purely descriptive |

**Verdict**: legitimate, cheap addition to the evaluation section of a report — not a substitute for a training-label design.

---

## Supplementary, orthogonal fixes (stackable on top of any option above)

These don't replace A/B/C/D — they attack the shared blind spot (embedding models can't see all behavioral change) from different angles.

| Fix | What it actually closes | What it doesn't |
|---|---|---|
| **Canonicalized AST diffing** (compare ASTs after identifier canonicalization, not raw `ast.dump()` string equality) | Fully, precisely solves the "pure rename/reformat" false-positive case — decidable and cheap, should just be done regardless of everything else discussed | Doesn't touch false negatives (operator/constant changes) at all |
| **Code-specific embedding model** (CodeBERT/UnixCoder/contrastive mutation-trained encoder) instead of a general NL sentence-transformer | Genuinely raises sensitivity to logic-level changes — part of the current blind spot is a *choice* of encoder, not an inherent law | Still a proxy; smaller blind spot, not zero |
| **Differential/fuzz testing** (generate inputs, run entity-before vs entity-after, diff outputs) | Real behavioral evidence, independent of embeddings, for pure functions | Doesn't work for stateful/side-effecting code; needs input generation |
| **Existing test suite + coverage mapping** | Real signal when tests exist and cover the entity | Useless in early-dev/low-coverage repos (an acknowledged weakness even in the 3-layer doc's own defense guide) |
| **Periodic LLM diff review** (ask an LLM "does this diff change behavior," offline, occasional spot-check) | Cheap sanity check without full RAGAS/RL machinery | Still text-based guessing, still noisy, no execution |

---

## Cross-cutting, unavoidable limits (true regardless of which option you pick)

1. **Program-equivalence in general is undecidable** (Rice's theorem territory). No embedding, no LLM judge, no statistic will ever give a universal, always-correct answer to "did behavior change" for arbitrary code. Every option above is a *practical approximation*, not a solution to that theoretical ceiling — state this explicitly in any writeup rather than implying it's solved.
2. **Whatever generates your evaluation queries must be independent of the embedding model being validated**, or every downstream metric (recall@k, nDCG, RAGAS, Wilcoxon) silently inherits circularity. Your repo already has the right building block (`curated_queries.json`) — the wrong one (`_generate_queries()`) is also in the repo and must not be the source of `Q` for any ground-truth computation.
3. **"Ground truth" cannot be eliminated, only relocated.** Supervised learning needs a label; RL needs a reward; both are "some definition of correct." The real choice is *how cheaply, reproducibly, and defensibly* that definition is computed — not whether you need one.

---

## Final recommendation: the optimal combination

**Adopt Option C (3-Layer Rank-Displacement + Wilcoxon + Pareto) as the label, with its three fixes applied, plus one cheap supplementary fix — and drop RAGAS from training entirely, keeping it only as an optional offline evaluation metric (Option D).**

Concretely, in priority order:

1. **Fix the query source.** Point the ground-truth computation at `curated_queries.json`, not `_generate_queries()`. This is the single highest-leverage, cheapest fix — without it, everything downstream is compromised.
2. **Add canonicalized AST diffing** to replace the current `normalize_source()` whitespace/comment-only filter. Free, deterministic, fully closes the rename/reformat false-positive case.
3. **Implement the 3-layer label** (`compute_leave_one_out_ground_truth`) as a drop-in replacement for `y = binarize(cosine_drift)` in `predictor.py` — same supervised training loop, same loss function, no RL, no LLM in the loop.
4. **Report the Pareto frontier**, not a single accuracy number, when evaluating the predictor against baselines — this is both more honest and a stronger result to present.
5. **Add an explicit limitations section** acknowledging the embedding-blind-spot and program-equivalence undecidability, rather than claiming full circularity elimination.
6. **Optional, if time/budget allows**: run RAGAS once, offline, at the end, on the final strategy's retrieval output, purely as a supplementary reported metric (Option D) — not as anything the model trains against. If the codebase leans toward pure functions, differential/fuzz testing is a stronger and cheaper "second signal" to add than RAGAS would be.

**Why this is optimal**: it keeps every genuine improvement identified in this discussion (task-relevant label instead of raw distance, explicit cost/quality tradeoff, statistical rigor, non-circular query grounding) while discarding everything that only added cost, noise, or infeasibility (RL, per-sample LLM calls, an unfixed missing-cost-term). It is strictly simpler to build than the original NN+RAGAS idea — same training loop as today, one changed label — while being more defensible on every axis a reviewer would probe (reproducibility, cost, statistical grounding, auditability), and it's honest about the one thing that can't be fixed by any of this (true semantic/behavioral verification), rather than overclaiming it away.

# Proposal: RAGAS-Rewarded Neural Network Replacing the Random-Forest Drift Predictor

Status: **idea review / design doc** — not yet implemented.
Branch: `RAGAS_NN`

## 1. Current baseline (for reference)

So the comparison below is grounded in what actually exists today, not assumptions:

- **Label**: `compute_drift()` in [`src/embedder/embedding_manager.py`](../src/embedder/embedding_manager.py) computes `drift = 1 - cosine_similarity(embedding_at_commit_A, embedding_at_commit_B)` for every code entity that survives between two consecutive sampled commits. This is binarized at a threshold (fixed at `0.05`, or dynamic at the 85th percentile of nonzero drifts) into "needs re-embedding" vs. "stays fresh."
- **Features**: ~25 per-entity, per-commit-pair features from [`src/extractor/feature_extractor.py`](../src/extractor/feature_extractor.py) — graph centrality (pagerank, betweenness, degree), change-propagation distance to modified nodes, personalized-PageRank impact, diff size, historical modification frequency, previous drift, Graph Transition Descriptor churn features, and code-complexity metrics (cyclomatic complexity, AST size, nesting depth, taint reachability).
- **Model**: `DriftPredictor` in [`src/predictor/predictor.py`](../src/predictor/predictor.py) — a `RandomForestClassifier` trained on those features to predict the binarized drift label.
- **Evaluation**: `evaluator.py` compares cache-invalidation strategies (predictive, always-reindex, changed-only, fixed-hop) using retrieval metrics — recall@k, MRR, nDCG, Spearman correlation — from `evaluator/util.py`. No LLM is involved anywhere in the current pipeline. **RAGAS is not used anywhere in the codebase today** — this would be a new dependency.
- **Scale**: default runs sample **5–10 commits** per repo (`settings.json`, `benchmark_settings.json`), producing on the order of a few hundred entity-level training rows per experiment. This number matters a lot for section 5.

## 2. The proposed idea, restated

As I understand it:

1. Initialize a neural network with random weights, fed the same (or similar) per-commit/per-entity features used today.
2. For each commit, the network outputs something that is used to produce an embedding (either: a corrective/predicted embedding directly, or a re-embed/keep-cached decision).
3. Run retrieval using that embedding, score the retrieval quality with **RAGAS**.
4. Feed the RAGAS score back into the network as a training signal, replacing the cosine-drift ground truth label and the Random Forest.

This is a reasonable-sounding sketch, but it collapses two different design decisions that need to be pulled apart before "is it feasible" can be answered:

- **(A) What does the network output?** An embedding vector itself, or a scalar invalidation decision (same shape as today's classifier output)?
- **(B) How does a non-differentiable, LLM-judged score train a network?** You can't backprop through RAGAS (see §4).

I'll address both, because the answer to "is this good" is different for each combination.

## 3. The critical flaw hiding in the idea: no cost term

This is the most important thing in this document, so it goes first, not last.

The entire point of the existing system is a **cost/quality tradeoff**: re-embedding every entity on every commit gives perfect retrieval quality trivially (you always have the freshest embeddings), but costs compute/API calls proportional to repo size × commit frequency. The prediction task only has value because it lets you *skip* re-embedding for entities that haven't meaningfully changed, while still keeping retrieval quality acceptable.

If you train a network purely to **maximize RAGAS retrieval quality**, with no penalty for re-embedding, the globally optimal policy it will converge toward is: *"always re-embed everything."* That policy has zero prediction value and is exactly the `full_reindex` baseline the current pipeline already benchmarks against. A reward signal built only from retrieval quality has a degenerate optimum that defeats the purpose of the whole project.

**Fix**: the reward/loss must be something like

```
reward = retrieval_quality(RAGAS or otherwise) - λ * cost(re-embedding_decision)
```

where `cost` counts how many entities were actually re-embedded (or the compute/$ spent). Tuning `λ` becomes a real hyperparameter and a real research question ("what's the quality-per-dollar frontier"), which is actually a *more* interesting framing than the current one — but it must be explicit, or the network has nothing stopping it from trivially always re-embedding.

This also reframes what the network should output: a **re-embed/keep-cached decision** (same shape as today's binary classifier, or a continuous "value of re-embedding this entity now" score), not a predicted embedding vector. Predicting the embedding vector itself is not useful even if it "works": if an entity needs re-embedding, you already have the cheapest possible way to get the true new embedding — run it through the frozen sentence-transformer, which is exactly what `compute_drift()` already does to build the label. A neural net trying to *guess* that vector without running the entity through the encoder is solving a harder, less accurate version of a problem you can solve exactly for the same or lower cost. Keep the network's job as "decide," not "hallucinate an embedding."

## 4. Why you can't just backprop the RAGAS score

RAGAS metrics (faithfulness, context precision/recall, answer relevancy, etc.) are computed by:
1. Running retrieval with some embedding/index state → getting top-k contexts (an **argsort/top-k operation — not differentiable**).
2. Often generating an answer with an LLM from those contexts (**another non-differentiable, external API call**).
3. Scoring the result with an LLM-as-judge prompt (**also non-differentiable, and noisy** — LLM judges are known to have run-to-run variance).

So there is no gradient path from "network output" to "RAGAS score" — standard backpropagation is off the table. To use RAGAS as the training signal at all, you need **reinforcement learning** (policy gradient / REINFORCE, or a bandit method), treating the network's decision as an action and the RAGAS score (minus the cost term above) as a scalar reward. That's a materially different and harder training setup than supervised learning with MSE/cross-entropy against a fixed label, with its own failure modes: high-variance gradient estimates, need for a baseline/advantage estimator to reduce variance, exploration vs. exploitation, and sensitivity to reward scale/noise.

## 5. The scale problem

RL methods are notoriously sample-hungry — typically thousands to millions of environment interactions even for small problems, because each gradient update only uses a noisy scalar reward instead of a dense per-output-dimension error signal. Compare that to what's actually available here:

- Current experiments sample **5–10 commits per run** (`settings.json`/`benchmark_settings.json`), giving a few hundred entity-level rows total — already a small dataset for a Random Forest, and a Random Forest is far more sample-efficient than a randomly-initialized neural network, which is in turn far more sample-efficient than an RL policy trained from scratch.
- Each RAGAS reward evaluation requires at least one LLM call (often several, per metric), so a training loop that wants to call RAGAS per training step is also expensive and slow — plausibly seconds per sample and real API cost, which puts a hard ceiling on how many gradient steps are practical.

Put together: **the current experimental scale (5–10 commits) is 2–4 orders of magnitude too small to train an RL policy from random initialization using an expensive, noisy LLM-judged reward.** This isn't a tuning problem — it's a fundamental mismatch between the data budget and what the proposed method needs.

## 6. Verdict

| Question | Answer |
|---|---|
| Is the underlying instinct sound? | Yes — using actual downstream retrieval quality as ground truth instead of a raw cosine-distance proxy is a legitimate critique of the current label, and worth pursuing. |
| Is "NN + RAGAS-as-reward via RL, trained online per-commit" feasible at the current project scale? | **No**, not as literally described. Missing cost term makes the reward degenerate; RAGAS's non-differentiability forces RL, which needs orders of magnitude more data and reward evaluations than exist or are affordable here. |
| Is there a version of this idea that *is* feasible and keeps the spirit? | Yes — see §7. |

This is a good instinct pointed at the wrong mechanism. The fix isn't to abandon "let real retrieval quality define the signal" — it's to decouple *label quality* from *online RL*, and to fix the missing cost term.

## 7. Recommended path (keeps the idea, drops what breaks it)

### Phase 1 — Swap RF → NN, same label, same loss (sanity check)
Replace `RandomForestClassifier` with a small feedforward NN (e.g., 2–3 hidden layers) trained with plain supervised learning (binary cross-entropy) on the exact same binarized cosine-drift label used today. This isolates "does a NN help at all on this feature set/scale" from "does changing the label help." Given the ~hundreds-of-rows scale, expect the NN to at best match, likely underperform, the Random Forest — small tabular datasets are the Random Forest's home turf. Worth doing only to have an honest baseline before touching the label; don't expect a win here.

### Phase 2 — Replace the *label*, keep supervised learning (this is the real idea, made tractable)
Instead of `1 - cosine_similarity(old, new)` as ground truth, compute a **retrieval-quality-based label**, but do it **offline, in batch, using the cheap, deterministic, already-implemented metrics in `evaluator/util.py`** (recall@k, nDCG, MRR) — not RAGAS, not online. Concretely: for each entity/commit pair, measure how much retrieval quality (against the existing synthetic-query set) actually degrades if you *don't* re-embed that entity, versus if you do. That delta is a continuous, still-fully-computable-without-an-LLM target that directly encodes "does skipping re-embedding here actually hurt retrieval" — much closer to what actually matters than raw cosine distance, with none of RL's differentiability or sample-efficiency problems, because it's still a fixed label you regress against with plain MSE. Don't forget the cost term from §3 if you turn this into a policy rather than a label (e.g., label = quality_drop - λ·1).

### Phase 3 — Bring RAGAS in, but only as an evaluation metric, not a training signal
Add RAGAS metrics (context precision/recall are the cheapest — they don't require an LLM to *generate* an answer, only to judge relevance) alongside the existing recall@k/MRR/nDCG comparison in the Stage 5 strategy evaluation. This tells you whether the predictive strategy's retrieval quality holds up under an LLM-judged metric, not just embedding-similarity-based ones — genuinely useful signal, and cheap because it only runs once per strategy per experiment, not once per training step. Sample only a subset of queries/commits to control LLM cost.

### Phase 4 — Only if Phase 2 shows the retrieval-quality label beats the cosine-drift label, and only if you want the research stretch
Consider a real RL formulation using the *cheap* recall@k/nDCG reward from Phase 2 (not RAGAS) as the per-step reward — this keeps the "reward = actual retrieval quality" idea alive without the LLM cost/noise/latency, and reserve RAGAS for periodic checkpoint evaluation (e.g., every N training episodes) rather than per-sample reward. Explicitly include the cost term. This would also need you to decide whether it's a true sequential MDP (policy's own past decisions change the cache state future commits see — requires rewriting the sequential loop in `build_dataset()`/`evaluate_strategies()` in `run_experiment.py` to branch on the policy's choices) or a simpler contextual bandit over the existing historical trace (each commit's decision doesn't affect what data future commits see — much cheaper, and probably where to start).

## 8. Other risks to keep in mind if you proceed

- **Reward/label noise from LLM judges**: RAGAS scores are not perfectly reproducible across runs of the same input; if used as a training signal at any stage, expect to need multiple samples per data point or explicit noise-robust training (label smoothing, averaging over repeats) — another reason to prefer Phase 2's deterministic metric over RAGAS during training.
- **Query dependency**: RAGAS-style retrieval evaluation is only as good as the synthetic query set. If queries don't actually exercise the entities being scored, both cosine-drift and RAGAS-based labels will be unreliable in different ways — worth auditing the synthetic query generator's coverage before trusting either label source.
- **Non-i.i.d. commits**: `build_dataset()` and `evaluate_strategies()` in `run_experiment.py` process commits sequentially and mutate shared history dicts as they go; if Phase 4's RL formulation is pursued, decide explicitly whether it's online (policy affects future state) or offline/bandit (it doesn't) — this changes both the algorithm and the amount of code that needs to change.

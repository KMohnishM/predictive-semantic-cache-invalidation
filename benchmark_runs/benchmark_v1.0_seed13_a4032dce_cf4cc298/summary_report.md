# Benchmark Summary

- Run ID: benchmark_v1.0_seed13_a4032dce_cf4cc298
- Total queries: 109380
- Changed queries: 7420
- Unchanged queries: 101960

## Staleness Cost vs. Full Re-index

For each query the target's rank in the strategy's index is compared with its rank in a full re-index of the same commit. **Lost@k**: the full re-index has the target in the top-k and the strategy does not (rate = lost / full-re-index hits, 95% Wilson CI). **Stale gains@k**: the reverse — a stale vector beating the fresh one; reported, never credited. Primary k = 5. *Stale-target* queries are those whose target's vector in the strategy's index differs from the full re-index.

| Strategy | Update Cost | Lost@1 | Lost@5 | Lost@10 | Stale gains@5 | Rank degraded | Stale-target queries | Lost@5 (stale-target) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `changed_only` | 0.0431 | 28/7146 = 0.39% [0.27%, 0.57%] | 19/14708 = 0.13% [0.08%, 0.20%] | 19/17040 = 0.11% [0.07%, 0.17%] | 66 | 5.02% | 790 / 27345 | 19/392 = 4.85% |
| `fixed_hop` | 0.1660 | 0/7146 = 0.00% [0.00%, 0.05%] | 0/14708 = 0.00% [0.00%, 0.03%] | 1/17040 = 0.01% [0.00%, 0.03%] | 1 | 0.23% | 25 / 27345 | 0/20 = 0.00% |
| `predictive_ml` | 0.0479 | 0/7146 = 0.00% [0.00%, 0.05%] | 0/14708 = 0.00% [0.00%, 0.03%] | 0/17040 = 0.00% [0.00%, 0.02%] | 1 | 0.55% | 125 / 27345 | 0/61 = 0.00% |
| `full_reindex` | 1.0000 | 0/7146 = 0.00% [0.00%, 0.05%] | 0/14708 = 0.00% [0.00%, 0.03%] | 0/17040 = 0.00% [0.00%, 0.02%] | 0 | 0.00% | 0 / 27345 | – |

## Absolute Retrieval Quality

Hit rates in the strategy's own index. These are dominated by the embedding model's retrieval quality (a full re-index scores the same way), so compare strategies on the staleness cost above, not on these.

| Strategy | Update Cost | Freshness [95% CI] ($N_{\text{changed}}$) | Cache Pres. [95% CI] ($N_{\text{unchanged}}$) | Relative Baseline Agreement | nDCG Ratio |
| :--- | :---: | :--- | :--- | :---: | :---: |
| `changed_only` | 0.0431 | 0.613 [0.591, 0.635] (n=1855) | 0.624 [0.618, 0.630] (n=25490) | **0.9989** | **1.0002** |
| `fixed_hop` | 0.1660 | 0.613 [0.591, 0.635] (n=1855) | 0.624 [0.618, 0.630] (n=25490) | **0.9999** | **1.0002** |
| `predictive_ml` | 0.0479 | 0.613 [0.591, 0.635] (n=1855) | 0.624 [0.618, 0.630] (n=25490) | **1.0000** | **1.0002** |
| `full_reindex` | 1.0000 | 0.613 [0.591, 0.635] (n=1855) | 0.624 [0.618, 0.630] (n=25490) | **1.0000** | **1.0000** |

## Cost vs. Quality Pareto Frontier

A strategy is **Pareto-optimal** if no other strategy is simultaneously cheaper (lower update cost) and better on quality (Retention@5). Strategies on the frontier represent the best achievable tradeoffs.

**Pareto-optimal strategies:** `changed_only`, `predictive_ml`

| Strategy | Update Cost ↓ | Retention@5 ↑ | Pareto-Optimal |
| :--- | :---: | :---: | :---: |
| `changed_only` | 0.0431 | 0.9987 | ✅ Yes |
| `predictive_ml` | 0.0479 | 1.0000 | ✅ Yes |
| `fixed_hop` | 0.1660 | 1.0000 | ❌ No |
| `full_reindex` | 1.0000 | 1.0000 | ❌ No |

## Direct Embedding Quality & Vector Fidelity

| Strategy | Updated Fraction (Cost) | Mean Cosine Sim (Fidelity) | Min Cosine Sim | P95 Cosine Sim | Total Entities |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `changed_only` | 0.0631 | 1.0000 | 1.0000 | 1.0000 | 586 |
| `fixed_hop` | 0.1775 | 1.0000 | 1.0000 | 1.0000 | 586 |
| `predictive_ml` | 0.0648 | 1.0000 | 1.0000 | 1.0000 | 586 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 586 |
| `changed_only` | 0.1438 | 0.9999 | 0.9875 | 1.0000 | 584 |
| `fixed_hop` | 0.2791 | 1.0000 | 1.0000 | 1.0000 | 584 |
| `predictive_ml` | 0.1695 | 1.0000 | 1.0000 | 1.0000 | 584 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 584 |
| `changed_only` | 0.0427 | 0.9999 | 0.9875 | 1.0000 | 585 |
| `fixed_hop` | 0.1829 | 1.0000 | 1.0000 | 1.0000 | 585 |
| `predictive_ml` | 0.0427 | 1.0000 | 1.0000 | 1.0000 | 585 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 585 |
| `changed_only` | 0.0204 | 0.9992 | 0.7846 | 1.0000 | 589 |
| `fixed_hop` | 0.2632 | 0.9992 | 0.7846 | 1.0000 | 589 |
| `predictive_ml` | 0.0323 | 1.0000 | 1.0000 | 1.0000 | 589 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 589 |
| `changed_only` | 0.0152 | 0.9991 | 0.7846 | 1.0000 | 591 |
| `fixed_hop` | 0.0626 | 0.9999 | 0.9608 | 1.0000 | 591 |
| `predictive_ml` | 0.0152 | 0.9999 | 0.9608 | 1.0000 | 591 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 591 |
| `changed_only` | 0.0203 | 0.9991 | 0.7846 | 1.0000 | 592 |
| `fixed_hop` | 0.0338 | 0.9999 | 0.9608 | 1.0000 | 592 |
| `predictive_ml` | 0.0203 | 0.9999 | 0.9608 | 1.0000 | 592 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 592 |
| `changed_only` | 0.0336 | 0.9992 | 0.7846 | 1.0000 | 596 |
| `fixed_hop` | 0.1057 | 1.0000 | 1.0000 | 1.0000 | 596 |
| `predictive_ml` | 0.0336 | 1.0000 | 0.9948 | 1.0000 | 596 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 596 |
| `changed_only` | 0.0359 | 0.9992 | 0.7846 | 1.0000 | 640 |
| `fixed_hop` | 0.0672 | 1.0000 | 1.0000 | 1.0000 | 640 |
| `predictive_ml` | 0.0437 | 1.0000 | 0.9948 | 1.0000 | 640 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 640 |
| `changed_only` | 0.0529 | 0.9992 | 0.7846 | 1.0000 | 643 |
| `fixed_hop` | 0.2442 | 1.0000 | 1.0000 | 1.0000 | 643 |
| `predictive_ml` | 0.0591 | 1.0000 | 0.9902 | 1.0000 | 643 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 643 |
| `changed_only` | 0.0325 | 0.9992 | 0.7846 | 1.0000 | 646 |
| `fixed_hop` | 0.1006 | 1.0000 | 1.0000 | 1.0000 | 646 |
| `predictive_ml` | 0.0341 | 1.0000 | 0.9902 | 1.0000 | 646 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 646 |
| `changed_only` | 0.0603 | 0.9992 | 0.7846 | 1.0000 | 647 |
| `fixed_hop` | 0.3153 | 1.0000 | 1.0000 | 1.0000 | 647 |
| `predictive_ml` | 0.0726 | 1.0000 | 0.9902 | 1.0000 | 647 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 647 |
| `changed_only` | 0.0703 | 0.9992 | 0.7846 | 1.0000 | 654 |
| `fixed_hop` | 0.2492 | 1.0000 | 1.0000 | 1.0000 | 654 |
| `predictive_ml` | 0.0719 | 1.0000 | 0.9902 | 1.0000 | 654 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 654 |
| `changed_only` | 0.0182 | 0.9992 | 0.7846 | 1.0000 | 660 |
| `fixed_hop` | 0.0470 | 1.0000 | 1.0000 | 1.0000 | 660 |
| `predictive_ml` | 0.0182 | 1.0000 | 0.9902 | 1.0000 | 660 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 660 |
| `changed_only` | 0.0164 | 0.9992 | 0.7846 | 1.0000 | 669 |
| `fixed_hop` | 0.0658 | 1.0000 | 1.0000 | 1.0000 | 669 |
| `predictive_ml` | 0.0179 | 1.0000 | 0.9902 | 1.0000 | 669 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 669 |
| `changed_only` | 0.0278 | 0.9992 | 0.7846 | 1.0000 | 684 |
| `fixed_hop` | 0.2909 | 1.0000 | 1.0000 | 1.0000 | 684 |
| `predictive_ml` | 0.0307 | 1.0000 | 0.9902 | 1.0000 | 684 |
| `full_reindex` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 684 |
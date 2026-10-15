# Query-set robustness: Lost@5

Source: `benchmark_runs\benchmark_v1.0_seed13_a4032dce_cf4cc298\per_query_results.jsonl`  
Bootstrap: 2000 replicates over target entities, seed 13.

## All queries

285 target entities with at least one eligible query; 27345 query checks per strategy.

| Strategy | Mean per-pair update cost | Lost@5 | Wilson 95% (query-level) | Bootstrap 95% (target-level) | Design effect | Effective n | Adjusted upper bound |
|---|---|---|---|---|---|---|---|
| `changed_only` | 4.36% | 19/14,708 = 0.13% | [0.08%, 0.20%] | [0.00%, 0.37%] | 11.35 | 1,296 | 0.56% (design effect 11.35) |
| `predictive_ml` | 4.84% | 0/14,708 = 0.00% | [0.00%, 0.03%] | [0.00%, 0.00%] | – | – | 0.30% (design effect 11.35) |
| `fixed_hop` | 16.57% | 0/14,708 = 0.00% | [0.00%, 0.03%] | [0.00%, 0.00%] | – | – | 0.30% (design effect 11.35) |
| `full_reindex` | 100.00% | 0/14,708 = 0.00% | [0.00%, 0.03%] | [0.00%, 0.00%] | – | – | 0.30% (design effect 11.35) |

Paired differences (row minus column strategy), target-level bootstrap:

| Pair | Difference in Lost@5 | 95% interval | Share of replicates > 0 | Smallest detectable difference (80% power) |
|---|---|---|---|---|
| `changed_only` − `predictive_ml` | 0.13% | [0.00%, 0.37%] | 0.946 | 0.28% |
| `changed_only` − `fixed_hop` | 0.13% | [0.00%, 0.37%] | 0.946 | 0.28% |
| `changed_only` − `full_reindex` | 0.13% | [0.00%, 0.37%] | 0.946 | 0.28% |
| `predictive_ml` − `fixed_hop` | 0.00% | [0.00%, 0.00%] | 0.000 | – |
| `predictive_ml` − `full_reindex` | 0.00% | [0.00%, 0.00%] | 0.000 | – |
| `fixed_hop` − `full_reindex` | 0.00% | [0.00%, 0.00%] | 0.000 | – |

Observed ordering (lowest Lost@5 first, ties by update cost): `predictive_ml` < `fixed_hop` < `full_reindex` < `changed_only`
Share of bootstrap replicates with the same ordering: 0.946

## Queries with at least 8 words

271 target entities with at least one eligible query; 24689 query checks per strategy.

| Strategy | Mean per-pair update cost | Lost@5 | Wilson 95% (query-level) | Bootstrap 95% (target-level) | Design effect | Effective n | Adjusted upper bound |
|---|---|---|---|---|---|---|---|
| `changed_only` | 4.36% | 19/13,162 = 0.14% | [0.09%, 0.23%] | [0.00%, 0.38%] | 10.42 | 1,263 | 0.58% (design effect 10.42) |
| `predictive_ml` | 4.84% | 0/13,162 = 0.00% | [0.00%, 0.03%] | [0.00%, 0.00%] | – | – | 0.30% (design effect 10.42) |
| `fixed_hop` | 16.57% | 0/13,162 = 0.00% | [0.00%, 0.03%] | [0.00%, 0.00%] | – | – | 0.30% (design effect 10.42) |
| `full_reindex` | 100.00% | 0/13,162 = 0.00% | [0.00%, 0.03%] | [0.00%, 0.00%] | – | – | 0.30% (design effect 10.42) |

Paired differences (row minus column strategy), target-level bootstrap:

| Pair | Difference in Lost@5 | 95% interval | Share of replicates > 0 | Smallest detectable difference (80% power) |
|---|---|---|---|---|
| `changed_only` − `predictive_ml` | 0.14% | [0.00%, 0.38%] | 0.956 | 0.30% |
| `changed_only` − `fixed_hop` | 0.14% | [0.00%, 0.38%] | 0.956 | 0.30% |
| `changed_only` − `full_reindex` | 0.14% | [0.00%, 0.38%] | 0.956 | 0.30% |
| `predictive_ml` − `fixed_hop` | 0.00% | [0.00%, 0.00%] | 0.000 | – |
| `predictive_ml` − `full_reindex` | 0.00% | [0.00%, 0.00%] | 0.000 | – |
| `fixed_hop` − `full_reindex` | 0.00% | [0.00%, 0.00%] | 0.000 | – |

Observed ordering (lowest Lost@5 first, ties by update cost): `predictive_ml` < `fixed_hop` < `full_reindex` < `changed_only`
Share of bootstrap replicates with the same ordering: 0.956


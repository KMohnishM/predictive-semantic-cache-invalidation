# Problem Statement

The main question is: what is the smallest set of repository entities that must be re-embedded after a code change to keep retrieval quality close to a full repository re-index?

To evaluate this, we need a benchmark that measures retrieval quality rather than embedding quality alone. The benchmark should use the same search queries in two cases: a ground-truth run where the full codebase is re-embedded, and a selective run where only the important changed components are re-embedded. This lets us compare how well the selective strategy preserves retrieval behavior.

The benchmark should confirm that queries about modified code return the latest information instead of stale cache results, while queries about unchanged code still retrieve the correct cached information. If the selective re-embedding strategy matches the full re-index closely in both cases, it can be considered acceptable.

In the happy-path evaluation, we should also assume perfect search queries that are aimed at the updated information in the latest commit. For a changed module or component, the query should return the latest snapshot of that part of the codebase, not an older cached version. For information that was not changed, the query should still return the correct snapshot from the cache, showing that the benchmark can distinguish updated and unchanged knowledge correctly.


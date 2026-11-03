"""Example 4: Programmatic Benchmarking on Custom Repositories.

Demonstrates how to run comparative benchmarks evaluating:
  - changed_only
  - fixed_hop (1-hop / 2-hop)
  - predictive_ml
  - full_reindex
"""

from pathlib import Path
from predictive_semantic_cache.benchmarking.runner import run_benchmark
from predictive_semantic_cache.benchmarking.config import BenchmarkConfig

# Configure the benchmark run
config = BenchmarkConfig(
    repo_path=".",                       # Target repository
    output_dir="./benchmark_results",     # Where charts and reports are saved
    num_commits=5,                       # Number of commits to evaluate
    commit_stride=1,
    strategies=["changed_only", "fixed_hop", "predictive_ml"],
    hop_k=1,
    query_mode="synthetic",
    model_name="sentence-transformers/all-MiniLM-L6-v2",
)

print(f"Running benchmark across {config.num_commits} commits...")
# output_dir = run_benchmark(config)
# print(f"Benchmark completed! Reports generated in: {output_dir}")
print("To run from the terminal directly:")
print("  predictive-cache-benchmark --repo-path . --num-commits 5 --strategies changed_only,predictive_ml")

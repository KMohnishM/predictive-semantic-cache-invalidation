"""Example 1: Basic Usage of Predictive Semantic Cache Invalidation.

Demonstrates:
  1. Default ML (Zero-Config): Auto-loading the bundled pre-trained model.
  2. Custom Model: Supplying your own trained .pkl artifact.
  3. Graph Heuristics: Fast, deterministic call-graph traversal (no ML).
"""

from pathlib import Path
from predictive_semantic_cache import PredictiveCache

# Point to your repository (current directory in this example)
REPO_PATH = Path(".").resolve()

print("=" * 60)
print("1. DEFAULT ML (Zero-Config, bundled 50 KB model)")
print("=" * 60)

# Zero setup: automatically loads the bundled pre-trained model
cache_default = PredictiveCache(repo_path=REPO_PATH)

# Detect which entities drifted between two commits
# (Replace with your own commit hashes or refs like 'main~1', 'main')
summary_default = cache_default.get_stale_summary(from_commit="HEAD~1", to_commit="HEAD")

print(f"Total codebase entities:    {summary_default['total_entities']}")
print(f"Entities needing re-index: {summary_default['stale_count']}")
print(f"Re-embedding ratio:        {summary_default['reembed_ratio']:.2%}")
print(f"Model used:                {summary_default['model_path']}")


print("\n" + "=" * 60)
print("2. CUSTOM MODEL (Enterprise / Fine-tuned .pkl)")
print("=" * 60)

# If your team trained a custom model on your private Git history:
custom_model_file = "models/my_custom_model.pkl"
if Path(custom_model_file).exists():
    cache_custom = PredictiveCache(
        repo_path=REPO_PATH,
        model_path=custom_model_file,
        threshold=0.6,  # Optional custom decision threshold
    )
    summary_custom = cache_custom.get_stale_summary("HEAD~1", "HEAD")
    print(f"Stale count (Custom ML): {summary_custom['stale_count']}")
else:
    print(f"To use a custom model, train one and pass: PredictiveCache(model_path='{custom_model_file}')")
    print("See examples/05_train_custom_model.py for training instructions.")


print("\n" + "=" * 60)
print("3. GRAPH HEURISTIC (Deterministic, No ML required)")
print("=" * 60)

# Re-embed directly modified entities + 1-hop callers in the call graph
cache_graph = PredictiveCache(
    repo_path=REPO_PATH,
    strategy="fixed_hop",
    hop_k=1,
)
summary_graph = cache_graph.get_stale_summary("HEAD~1", "HEAD")
print(f"Stale count (1-hop call graph): {summary_graph['stale_count']}")

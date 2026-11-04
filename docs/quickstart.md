# Quickstart

Get started with **Predictive Semantic Cache** in less than 5 minutes.

---

## 1. Installation

Install the base package from PyPI:

```bash
pip install predictive-semantic-cache-invalidation
```

### Optional Extras

- **LlamaIndex Support**:
  ```bash
  pip install "predictive-semantic-cache-invalidation[llamaindex]"
  ```
- **LightGBM Accelerator**:
  ```bash
  pip install "predictive-semantic-cache-invalidation[lightgbm]"
  ```
- **Full Research & Benchmarking Suite**:
  ```bash
  pip install "predictive-semantic-cache-invalidation[all]"
  ```

---

## 2. Basic Usage (Zero Configuration)

By default, the library loads a bundled pre-trained 50 KB model. You don't need to configure weights or train anything:

```python
from predictive_semantic_cache import PredictiveCache

# 1. Point to your repository root
cache = PredictiveCache(repo_path=".")

# 2. Get entities requiring re-embedding between two Git commits
stale_entities = cache.get_stale_entities(from_commit="HEAD~1", to_commit="HEAD")

print(f"Found {len(stale_entities)} entities that experienced semantic drift:")
for ent in stale_entities:
    print(f"  -> {ent.name} in {ent.file_path}:{ent.lineno}")
```

---

## 3. Getting Invalidation Summary

To inspect re-embed ratios and metrics:

```python
summary = cache.get_stale_summary(from_commit="main~1", to_commit="main")

print(f"Total codebase entities:    {summary['total_entities']}")
print(f"Entities needing re-index: {summary['stale_count']}")
print(f"Re-embed ratio:            {summary['reembed_ratio']:.2%}")
print(f"Strategy:                  {summary['strategy']}")
```

---

## 4. Next Steps

- Check out [Default ML vs Custom Model](guides/default_vs_custom_model.md) to learn how to train custom models on your repo.
- Check out [LlamaIndex Integration](guides/llama_index.md) to integrate directly into a RAG ingestion pipeline.
- Check out [GitHub Actions CI/CD](guides/github_actions.md) for automated production indexing on push.

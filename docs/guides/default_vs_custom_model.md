# Default ML vs Custom Model

`predictive-semantic-cache-invalidation` is designed with maximum flexibility: it provides both a **Zero-Config Default Pre-Trained Model** and a **Custom Model Training Pipeline**.

---

## 1. Default Pre-Trained Model (Out-of-the-Box)

### What it is
The library ships with a compact (50 KB) calibrated model (`default_drift_predictor.pkl`) embedded directly inside the package. It was trained across thousands of Git commits from popular open-source Python codebases (such as Black and Django) using:
- **47 graph-theoretic and AST features** (including Graph Transition Descriptors, Repository State Descriptors, centrality shifts, and taint distances).
- **Calibrated recall-first decision thresholds** to ensure critical semantic changes are not missed.

### How to use it
Simply leave `model_path=None`:

```python
from predictive_semantic_cache import PredictiveCache

# Automatically uses the bundled pre-trained model
cache = PredictiveCache(repo_path=".")
stale_entities = cache.get_stale_entities("HEAD~1", "HEAD")
```

---

## 2. Custom Model Training (Fine-Tuning on Your Codebase)

### Why train a custom model?
Enterprise repositories often have unique architectures, custom frameworks, or distinct code churn patterns. Training a model on your own commit history allows you to:
1. Maximize precision and recall on proprietary codebases.
2. Select your preferred classifier algorithm (`hist_gradient_boosting`, `lightgbm`, `random_forest`, `extra_trees`).
3. Set custom recall targets (e.g., target 99.5% recall for mission-critical code search).

### Step-by-Step Training Guide

```python
from pathlib import Path
import pandas as pd
from predictive_semantic_cache import DriftPredictor, FeatureExtractor
from predictive_semantic_cache.parser import TreeSitterRepoParser

repo_path = Path(".").resolve()

# Step 1: Parse the repository into an AST and call graph
parser = TreeSitterRepoParser(str(repo_path))
parser.parse_directory(str(repo_path))

# Step 2: Extract features for entities
extractor = FeatureExtractor(parser)
all_entities = list(parser.entities.keys())

features = [extractor.extract_features(eid) for eid in all_entities]
features_df = pd.DataFrame(features, index=all_entities)

# Labels: 1 = drifted (needs re-index), 0 = fresh
# (Labels can be generated from embedding cosine distance thresholds across historical commits)
labels = [1 if f.get("distance_to_modified_directed", 999) <= 1 else 0 for f in features]

# Step 3: Train the predictor with target recall
predictor = DriftPredictor(
    model_type="hist_gradient_boosting",
    task_type="classification",
    target_recall=0.98,
)
predictor.train(features_df.values, labels, feature_names=list(features_df.columns))

# Step 4: Save your custom artifact
output_path = "models/custom_drift_predictor.pkl"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
predictor.save(output_path)
print(f"Custom model saved to {output_path} with threshold {predictor.decision_threshold:.4f}")
```

### Loading Your Custom Model

Once trained, supply your `.pkl` path to `PredictiveCache`:

```python
from predictive_semantic_cache import PredictiveCache

cache = PredictiveCache(
    repo_path=".",
    model_path="models/custom_drift_predictor.pkl",
    threshold=0.55,  # Optional manual override
)
stale_entities = cache.get_stale_entities("HEAD~1", "HEAD")
```

---

## 3. Comparison Summary

| Capability | Default Pre-Trained Model | Custom Fine-Tuned Model |
| :--- | :--- | :--- |
| **Setup Time** | 0 seconds (Immediate) | 5–15 minutes (Training step) |
| **Dependencies** | Standard scikit-learn | scikit-learn or LightGBM |
| **Model Size** | ~50 KB | ~50–200 KB |
| **Custom Recall Target** | Fixed (~95–98%) | Fully configurable (up to 100%) |
| **Best For** | General RAG, quick prototypes, OSS | Enterprise monorepos, strict SLAs |

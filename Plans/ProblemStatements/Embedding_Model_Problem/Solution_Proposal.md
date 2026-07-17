# Solution Proposal: Embedding Model Selection for Source Code

This proposal addresses the **Embedding Model Selection Problem** by analyzing the limitations of general-purpose natural language processing (NLP) models, recommending candidate code-specific models, and outlining the architectural changes required to support multi-model evaluation.

---

## 1. Limitations of General NLP Models (The "Why")

General-purpose text embedding models (e.g., `all-MiniLM-L6-v2`) are trained on natural language corpora (e.g., Wikipedia, book transcripts). When applied to source code, they suffer from three key limitations:

1.  **Tokenization Weakness:** They split code tokens (e.g., `def parse_ast_node():`) into sub-words based on English patterns rather than programming constructs, losing syntactic context.
2.  **Context Window Exhaustion:** They typically limit inputs to **256 or 512 tokens**. Under our *Call-Graph Aware Contextual Chunking*, appending caller signatures and dependencies quickly exceeds this limit, resulting in severe truncation.
3.  **Semantic Drift Insensitivity:** They treat comments and variable renames with similar weight as control-flow changes (e.g., altering a loop condition or dependency hash), leading to noisy semantic drift calculations.

---

## 2. Code-Specific Model Evaluation Candidates

To address these limitations, we propose supporting and benchmarking three classes of models:

| Model | HuggingFace Path | Context Limit | Size | Primary Strength |
| :--- | :--- | :--- | :--- | :--- |
| **Jina Code (Primary)** | `jinaai/jina-embeddings-v2-base-code` | **8,192 tokens** | ~300 MB | Large context window. Supports embedding full function signatures and caller-callee context stubs without truncation. |
| **UniXcoder** | `microsoft/unixcoder-base` | **512 tokens** | ~250 MB | Pre-trained natively on AST structures and code-comment pairs. Understands code logic and syntax deeply. |
| **all-MiniLM-L6-v2 (Baseline)** | `sentence-transformers/all-MiniLM-L6-v2` | **256 tokens** | ~120 MB | Lightweight baseline. Runs rapidly on CPU. |

---

## 3. Integration Plan & Codebase Changes

### Step 1: Parameterize the Embedding Model
We modify [`src/embedding_manager.py`](file:///c:/Users/kmohn/New%20folder/Project-1/src/embedding_manager.py) and [`run_experiment.py`](file:///c:/Users/kmohn/New%20folder/Project-1/run_experiment.py) to accept a configurable `--model-name` argument.

```python
# In src/embedding_manager.py
class EmbeddingManager:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", clean_mode: bool = False):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
```

### Step 2: Context Chunk Adaptability
With `jina-embeddings-v2-base-code`, we can expand our `_get_contextual_source` logic in [`run_experiment.py`](file:///c:/Users/kmohn/New%20folder/Project-1/run_experiment.py) to include actual Python signatures and docstrings of dependencies rather than just source hashes, since the 8,192 token limit can easily accommodate it.

```python
# Context builder checks model window size:
max_tokens = 8192 if "jina" in model_name else 256
```

### Step 3: Run Comparative Benchmarks
To determine if code-specific models improve performance:
1.  **Drift Profile Variance:** We plot the semantic drift distribution for both models. Code models should show clear, sharp drift signals for structural modifications and negligible drift for comments.
2.  **ML Predictor Accuracy:** Compare the $R^2$ score and classification F1-score of the `DriftPredictor` under both embedding spaces.
3.  **Pareto Frontier Shift:** Compare the trade-offs of retrieval quality vs. cost.

---

## 4. Risks and Mitigation

*   **Computational Latency:** Code-specific models are larger and slower to compute on CPU.
    *   *Mitigation:* Keep `all-MiniLM-L6-v2` as the default CLI flag for quick local validation, while recommending Jina Code for final benchmarks.
*   **Drift Threshold Drift:** A cosine drift of `0.02` under MiniLM might correspond to `0.05` under Jina Code.
    *   *Mitigation:* Dynamically calculate the classification threshold as a percentile (e.g., top 15% of historical drifts) rather than hardcoding it to `0.02`.

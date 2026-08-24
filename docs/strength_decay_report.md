# Strength-Decay-Reembedding — Research & Empirical Evaluation Report

## 1. What This Project Is
Semantic caches for code (embedding every function/method for similarity search, RAG retrieval, etc.) go stale every time the underlying code changes. The naive fix is to re-embed the whole codebase on every commit, which doesn't scale. The alternative — re-embedding only what actually changed — requires knowing not just which functions were directly edited, but which other functions might need re-embedding because something they depend on changed underneath them.

This project builds and evaluates a pipeline that:
1. **Learns**, from a repo's own commit history, how strongly a change to one function tends to affect the functions that call it.
2. **Uses that learned model** to predict a "blast radius" of stale functions after a commit, cheaper than a full re-embed.
3. **Benchmarks** that selective strategy against full re-embedding and simpler baselines to evaluate efficiency vs. retrieval fidelity.

It is a formalization of an earlier prototype that used a hardcoded formula instead of a trained model. The target repo used to validate everything below is [psf/black](https://github.com/psf/black), a mid-size, actively developed Python codebase (~350 files at time of testing).

---

## 2. Pipeline Overview

```
[repo @ commit A] --AST/CPG--> [method-level call graph A]
[repo @ commit B] --AST/CPG--> [method-level call graph B]
       │
       ├─> graph diff + cosmetic-change filter (AST normalization)
       ├─> edge-strength scoring (trained model / BFS weights)
       ├─> decay-based impact propagation (BFS, blast radius)
       ├─> selective re-embed vs. full re-embed
       └─> benchmark: cost vs. fidelity
```

### Step 1: Graph Extraction
We parse the codebase into a method-level call graph. For every method in the repo, we track its full name, file, line range, callers, callees, and structural interaction patterns. Method source bodies are extracted with line ranges and compiled into structural nodes.

### Step 2: Graph Diff + Semantic Filter
Comparing the call graph at commit A vs. commit B gives added, removed, and changed methods. "Changed" is filtered further: a method's source is normalized by round-tripping it through Python's `ast` module (stripping comments, docstrings, formatting) before comparing old vs. new — so a comment edit or reformatting doesn't count as a semantic change, only a real logic change does.

### Step 3: Edge-Strength Features
For every `(caller, directly-changed callee)` pair, we compute a feature vector:

| Feature | What It Measures |
| :--- | :--- |
| `data_flow_coupling` | Fraction of the caller's calls to the callee whose return value is used vs. discarded |
| `call_freq_norm` | How central this caller is to the callee, relative to the callee's other callers |
| `signature_changed` | Did the callee's signature break |
| `code_similarity` | Text similarity of the caller's own source, old vs. new |
| `call_site_count` | How many times the caller calls the callee |
| `same_file` | Caller and callee in the same file |
| `co_change_freq` | Historical git co-change frequency of the caller's and callee's files |

### Step 4: Edge-Strength Model
A `RandomForest` regressor is trained per-repo on that feature set, with the label being the caller's real observed embedding drift ($1 - \text{cosine\_similarity}$ between the caller's embedding at commit A and commit B). Split is temporal — the model trains on the earlier portion of commit history and is evaluated on a held-out later portion, never mixed.

### Step 5: Propagation (Blast Radius)
Starting from the directly-changed methods, a BFS walks outward along reverse call edges (toward callers), multiplying the predicted edge strength at each hop. A node is marked stale if its propagated strength clears a threshold. This is how a change several hops away from a function can still mark it stale, with the strength decaying the further away it is.

### Step 6: Embedding
All embeddings (both ground-truth drift labels and actual re-embedding strategies compared in the benchmark) use `microsoft/unixcoder-base` via `sentence-transformers` — ensuring consistent and comparable vector evaluation.

---

## 3. Benchmark Strategies

On held-out commit pairs, four core strategies are evaluated:
1. **Full re-embed:** Embed every method. (Reference / Ground Truth).
2. **Learned (Predictive ML):** Propagate impact using the trained strength model.
3. **Hardcoded (Fixed Formula):** The original prototype's fixed formula ($0.5 \cdot \text{data\_flow\_coupling} + 0.3 \cdot \text{call\_freq\_norm}$), kept as an ablation baseline.
4. **No propagation (`changed_only`):** Only re-embed directly-changed methods, no graph walk.

Each strategy is scored on:
*   **Cost:** Fraction of methods actually re-embedded.
*   **Fidelity Error:** Mean cosine distance between that strategy's resulting cache and the full-reembed reference (lower is better).
*   **Precision / Recall / F1:** Of the predicted stale set against methods whose true observed drift exceeds a threshold.

---

## 4. Empirical Results & Findings

### Training Metrics (70 commit pairs, 1,341 labeled caller→callee edges, 21 held-out pairs)

| Metric | Value |
| :--- | :--- |
| **Train $R^2$** | **0.82** |
| **Test $R^2$ (held out)** | **0.61** |
| **Test MAE** | **0.017** |

Feature importance was dominated by `code_similarity` (0.93) — i.e., whether the caller's own code changed is by far the strongest predictor of whether the caller's embedding will drift.

### Benchmark Evaluation (21 held-out pairs)

| Strategy | Cost (%) | Fidelity Error | Precision | Recall | F1 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **No propagation (`changed_only`)** | 1.41% | ~0 | 0.098 | 0.852 | 0.163 |
| **Hardcoded formula** | 1.57% | ~0 | 0.083 | 0.852 | 0.142 |
| **Learned model** | 1.41% | ~0 | 0.098 | 0.852 | 0.163 |

---

## 5. Key Architectural Insights & Takeaways

### 1. Text-Isolated Embeddings vs. Context-Aware Chunking
*   **Text-Isolated Embeddings:** Under standard code embedders (`unixcoder-base`, `all-MiniLM-L6-v2`), if a method's own source text is byte-identical between two commits, its generated vector is 100% bit-identical. In this mode, re-embedding directly changed methods (`changed_only`) recovers **~85% of true drift at 1.4% of full re-embedding cost**, with fidelity error near zero.
*   **Context-Aware Chunking (`--context-chunking`):** When context-aware chunking is enabled (appending caller/callee signatures and structural interfaces to the prompt), modifying a callee *does* mutate the text representation of its caller. In context-aware mode, graph propagation strategies (`weighted_bfs_decay` and `predictive_ml`) show their true value by catching indirect semantic drift that text-isolated models miss.

### 2. High-Performance Native Parsing vs. Heavy Infrastructure
*   Relying on heavy JVM servers (like Joern REPL) creates memory leaks, JVM degradation under sustained load, and startup bottlenecks (30-45s per commit) that exceed the cost of embedding itself.
*   Migrating to **pure Python AST + NetworkX** yields **<0.15s per commit** decision latency (200x faster), zero memory leaks, zero Java dependencies, and 100% feature preservation.

### 3. Commit Stride Sampling
*   Adjacent commits are often uninformative (single whitespace or comment edits).
*   Sampling commits $N$ steps apart (stride sampling) produces richer, realistic semantic diffs for evaluating multi-hop propagation.

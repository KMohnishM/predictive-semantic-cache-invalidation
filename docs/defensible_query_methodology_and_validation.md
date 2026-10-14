# Defensible Query Methodology: Theory, Validation, and Quality Framework

**Document:** Comprehensive Defense of Evaluation Queries for Predictive Semantic Cache Invalidation  
**Target Repository:** `psf/black` (Sequential AST Snapshots across 2,384 commits)  
**Evaluation Standard:** Cranfield Information Retrieval Paradigm & TREC / BEIR Benchmark Specifications  

---

## Executive Summary

A fundamental vulnerability of vector search cache-invalidation benchmarks is **Evaluation Query Leakage**: when query strings include verbatim function names or parameter identifiers, dense embedding bi-encoders (e.g. `sentence-transformers/all-MiniLM-L6-v2`) act as token-matching mechanisms. Under leaky queries, retrieval success is guaranteed by surface string similarity regardless of whether vector caches are stale, creating artificial saturation where all strategies score identically.

To ensure academic and industrial defensibility, the evaluation queries in `curated_queries_black_change_focused.json` are authored and filtered under a dual-layer **Qualitative & Quantitative Quality Assurance Protocol**.

---

## 1. Quantitative Foundations & Theoretical Justifications

### 1.1 The Cranfield Paradigm & Lexical De-biasing
* **Theoretical Origin:** Cleverdon (1960s, Cranfield Experiments) and Voorhees (1991, Text REtrieval Conference / TREC).
* **The Core Axiom:** *Queries must be independently authored and decoupled from target document identity.* 
* **Implementation (`src/benchmarking/query_validation.py`):**
  - **No Identifier Leakage:** For each target entity $e$ (with short identifier $s_e$, enclosing class $c_e$, and file path $f_e$), all constituent tokens of length $\ge 4$ characters are extracted:
    $$T_{\text{prohibited}}(e) = \text{tokens}(s_e) \cup \text{tokens}(c_e) \cup \text{tokens}(\text{stem}(f_e))$$
  - Every query $q$ is regex-tested against $T_{\text{prohibited}}(e)$ on word boundaries. Any match rejects the query immediately.
  - *Example:* For target `action/main.py::determine_version_specifier`, the words `"determine"`, `"version"`, and `"specifier"` are completely forbidden from appearing anywhere in the query text.

### 1.2 Verbatim N-Gram Duplication Suppression ($N \ge 4$)
* **Theoretical Origin:** Thakur et al., *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models* (NeurIPS 2021).
* **The Vulnerability:** Embedding models easily memorize verbatim consecutive word sequences found within docstrings.
* **Implementation (`src/benchmarking/query_validation.py`):**
  - The query is decomposed into 4-grams ($W_4(q)$) and compared against the 4-grams of the target entity's source text and docstring ($W_4(\text{source}_e)$):
    $$W_4(q) \cap W_4(\text{source}_e) = \emptyset$$
  - If any 4 consecutive words match between the query and the embedded code chunk, the candidate query is disqualified.

### 1.3 Cross-Model Independent Semantic Fidelity (Circular Bias Elimination)
* **Theoretical Origin:** Preventing model-specific self-reinforcing bias.
* **Implementation (`scripts/build_black_change_focused_queries.py`):**
  - Queries synthesized via text-to-text generation (T5 / LLM) can hallucinate or drift into non-functional tangents.
  - Candidate queries are scored for semantic similarity against the entity's functional specification using an **independent second embedding model** (`BAAI/bge-base-en-v1.5`), requiring:
    $$\cos(\mathbf{e}_{\text{bge}}(q), \mathbf{e}_{\text{bge}}(\text{purpose}_e)) \ge 0.70$$
  - **Crucial Defense:** The evaluation model (`all-MiniLM-L6-v2`) is **deliberately NOT used** during query generation or filtering, eliminating circularity.

### 1.4 Unambiguous One-to-One Disambiguation
* **Mathematical Property:** $\forall q_i, q_j \in Q$, if $i \neq j \implies \text{target}(q_i) \neq \text{target}(q_j)$ for duplicate texts.
* **Implementation:** Queries that generate identical surface text across different AST targets (such as generic constructor questions like *"Which component coordinates initialization?"*) are strictly purged, preventing ambiguous ground truth where two valid documents compete for rank 1.

### 1.5 Statistical Power & Coverage Bounds ($M_q \ge 5$)
* **Theoretical Origin:** Exact Binomial Sign Test sample size requirements ($H_0: p=0.5$).
* **Significance Constraint:** In statistical hypothesis testing for rank displacement, a sample size $N < 5$ cannot reject the null hypothesis at $\alpha = 0.05$ under a two-tailed or one-tailed sign test:
  $$p = 0.5^4 = 0.0625 > 0.05 \quad (\text{insufficient power})$$
  $$p = 0.5^5 = 0.03125 < 0.05 \quad (\text{statistically valid})$$
* **Rule:** Every target entity included in the benchmark must have at least $M_q \ge 5$ clean, independent queries.

---

## 2. Qualitative Dimensions of Query Workload Design

### 2.1 The 3-Tier Change-Focused Workload Partitioning
Unlike random code-search queries, cache invalidation benchmarks must explicitly evaluate structural boundaries across commit histories:

```
+---------------------------------------------------------------+
|  Tier 1: Changed Entities                                     |
|  - Directly edited in git diff (AST modifications)             |
|  - Tests: Freshness detection & direct invalidation           |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|  Tier 2: Dependent Neighbors (1-Hop / 2-Hop Callers & Callees)|
|  - Un-edited code lines, but call-graph contextual text drifted|
|  - Tests: Indirect semantic drift, propagation, predictive ML |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|  Tier 3: Stable Background Entities                           |
|  - Completely un-affected by git commit changeset             |
|  - Tests: False-positive suppression & cache preservation     |
+---------------------------------------------------------------+
```

1. **Tier 1 (Changed Targets):** Tests whether invalidation catches direct code changes without dropping recall.
2. **Tier 2 (Neighbor Targets):** Specifically targets entities whose callees were edited. Under `changed_only`, these entities become stale. Under `predictive_ml` and `fixed_hop`, they are refreshed. This tier provides the discrimination power between baselines.
3. **Tier 3 (Stable Control):** Verifies that the strategy does not aggressively over-invalidate the entire cache (which would degenerate into `full_reindex`).

### 2.2 Intent-Oriented Functional Abstraction
Queries are phrased from the perspective of an engineer or downstream LLM agent searching for functional responsibilities:
* *Bad (Implementation / Token Leakage):* `"How does visit_trailer format lines in linegen.py?"`
* *Good (Functional Intent):* `"Which subsystem enforces indentation rules when splitting closing brackets and comma-separated arguments?"`

---

## 3. Query Validation Audit Summary (Empirical Proof)

Running the automated validator on `curated_queries_black_change_focused.json` produces:

```json
{
  "total_queries_evaluated": 23707,
  "identifier_leakage_violations": 0,
  "verbatim_ngram_copy_violations": 0,
  "multi_target_ambiguity_count": 0,
  "min_queries_per_target": 5,
  "semantic_fidelity_mean_bge": 0.814,
  "total_unique_ast_targets_covered": 684
}
```

---

## 4. Answering Common Panel Questions

### Question A: "Why not use real user search queries from GitHub / StackOverflow?"
* **Defense:** Real user search logs on GitHub are unaligned with specific internal commit-to-commit AST entity IDs in a single repository. Mining GitHub search logs introduces noise and misses internal helper functions. Following the TREC/BEIR Cranfield formulation guarantees complete entity coverage, exact target ground truth, and controlled de-biasing while maintaining realistic semantic diversity.

### Question B: "How do you prove that queries are not cherry-picked to favor `predictive_ml`?"
* **Defense:**
  1. The query dataset is generated statically *before* strategy evaluation.
  2. The exact same query workload is fed unconditionally to all 4 competing strategies (`changed_only`, `fixed_hop`, `predictive_ml`, and `full_reindex`).
  3. Query acceptance is governed by mathematical constraints (zero leakage, zero 4-grams, $M_q \ge 5$) rather than model performance.

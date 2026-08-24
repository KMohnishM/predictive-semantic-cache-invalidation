# Predictive Semantic Cache Invalidation for Vector-Based Code Search and RAG Systems
**Review-1 Academic Project Proposal and Technical Assessment Report**

**Authors:** Aditya Bhandari, Chebolu Tarun, K. Mohnish  
**Department:** Department of Computer Science and Engineering, School of Computing and Information Technology, Vellore Institute of Technology, Chennai, India  
**Project Guide:** Dr. Sivagami M (Associate Professor, Department of Computer Science and Engineering)  
**Date:** August 2026  

---

## Abstract
Codebase vector search engines and Retrieval-Augmented Generation (RAG) pipelines convert source code functions into dense vector embeddings for semantic navigation, automated code generation, and AI pair-programming. However, software repositories evolve continuously across Git commits. Re-indexing every function upon each commit incurs prohibitive $O(N)$ computational and API token costs. Conversely, naively re-embedding only directly edited files leaves dependent caller functions with stale vector representations, degrading LLM context quality. This paper proposes a native, graph-aware predictive cache invalidation framework. By extracting Abstract Syntax Tree (AST) structures, Git diff statistics, and NetworkX topological features (including PageRank, shortest-path distance, and graph transition descriptors), our pipeline trains a Random Forest regressor to predict embedding drift ($1 - \text{cosine\_similarity}$). A Weighted BFS Decay algorithm propagates invalidation signals along reverse call-graph edges to selectively refresh stale caches. The proposed framework aims to significantly reduce re-embedding overhead while preserving high retrieval recall without requiring heavy external server daemons.

---

## Section I: Introduction and Problem Formulation

### 1.1 Context and Technical Relevance
The modern software engineering ecosystem has been fundamentally transformed by AI-assisted code intelligence tools, intelligent IDE assistants (e.g., Cursor, GitHub Copilot, Sourcegraph Cody), and codebase-level Retrieval-Augmented Generation (RAG) platforms. These applications operate by partitioning a software repository into fine-grained code snippets (typically individual functions or class methods) and projecting them into a high-dimensional vector space using neural code embedding models such as UniXcoder, CodeBERT, or sentence-transformers. When a developer submits a natural language query or prompts an AI pair-programmer, the system performs a vector similarity search against a vector database (e.g., ChromaDB, Qdrant, or Pinecone) to retrieve the most semantically relevant code snippets as context for a Large Language Model (LLM).

However, software repositories are dynamic, constantly changing environments. As software development teams continuously merge Git commits, push refactorings, and modify function signatures, the underlying code entities evolve. This evolution introduces a major operational challenge: **vector cache staleness**. If a code entity is edited or its surrounding context changes, its existing cached embedding in the vector database becomes obsolete. Existing industry practices suffer from a strict trade-off between full repository re-indexing ($O(N)$ compute cost) and naive direct diff tracking (`changed_only`), which ignores dependent caller functions.

### 1.2 Problem Definition and Semantic Drift Taxonomy
To quantitatively analyze how code updates impact vector indices, we establish a formal taxonomy of code evolution across Git commits ($C_i \to C_{i+1}$):

#### 1.2.1 Direct Semantic Drift
Direct Semantic Drift occurs when a function $f$ undergoes internal logic modifications, parameter signature changes, or statement updates directly within the Git diff. In this scenario, the source code text of $f$ itself is modified, causing its vector embedding $v_f$ to drift directly from $v_f^{(i)}$ to $v_f^{(i+1)}$.

#### 1.2.2 Indirect Semantic Drift
Indirect Semantic Drift occurs when function $f$ remains unedited in Git, but one of its downstream callees $g$ (where $f$ calls $g$) undergoes logic modifications. Under context-aware chunking regimes (where prompt text incorporates callee interface stubs, docstrings, or MD5 hashes), modifying callee $g$ mutates the contextual prompt text of caller $f$. As a result, caller $f$ undergoes indirect vector drift despite being unedited in Git diffs.

### 1.3 Project Objectives
To address vector cache staleness effectively, the proposed project is defined around seven concrete technical objectives:
1. **Construct a Native AST Code Parsing Engine:** Build a lightweight Python AST parser to extract function and method entities along with symbol definitions.
2. **Develop a 25-Signal Topological Feature Engine:** Compute structural, edit volatility, centrality (PageRank, betweenness), shortest-path distance, and McCabe cyclomatic complexity features.
3. **Train a Predictive ML Drift Model:** Train a Random Forest regressor on historical Git commit pairs to accurately forecast continuous vector distance drift ($1 - \text{cosine\_similarity}$).
4. **Design a Weighted BFS Decay Propagation Algorithm:** Develop a graph cascade algorithm to propagate invalidation signals along reverse call-graph edges to capture indirect caller drift.
5. **Implement an AST Cosmetic Normalization Filter:** Perform round-trip AST compilation to strip whitespace, formatting, and docstrings, ignoring non-functional code edits.
6. **Deliver a Production Vector Store Integration Plugin:** Package the system into a production-ready extension (`llama_index_integration.py`) for LlamaIndex vector store ingestion pipelines (ChromaDB/Qdrant).
7. **Benchmark Against Baseline Strategies:** Systematically evaluate performance against full re-indexing, direct diff tracking (`changed_only`), and fixed-hop heuristics across Cost Ratio %, Recall@K, MAE, and decision latency.

---

## Section II: Scope, Expected Outcomes, and Feasibility

### 2.1 Scope and Project Boundaries
The scope of this project is strictly defined around function-level static analysis and vector store invalidation.

#### 2.1.1 In-Scope System Capabilities
* Analysis restricted to Python software repositories.
* Fine-grained analysis at the individual function and class method level.
* Static call-graph construction and topological feature extraction.
* Selective cache invalidation targeting vector databases for code RAG applications.

#### 2.1.2 Explicit System Boundaries and Non-Coverage
To maintain clear engineering boundaries, the following aspects are explicitly outside the system scope:
* **Dynamic Method Dispatch:** Dynamic runtime polymorphic overrides are resolved statically using module import symbol tables and suffix-matching heuristics rather than dynamic runtime tracing.
* **Non-Python Programming Languages:** The primary implementation targets Python source code; multi-language support (e.g., C++, Java, Rust) is reserved for future Tree-sitter extension.
* **External Network APIs and Runtime Dependencies:** External cloud service calls or non-static data streams are not tracked in static call graphs.

### 2.2 Expected System Outcomes
Upon completion, the project will deliver the following key technical outcomes:
* **Predictive Vector Drift Model:** A trained ML regressor predicting continuous cosine embedding distance drift ($1 - \text{cosine\_similarity}$).
* **Call-Graph Decay Propagation:** A functional Weighted BFS Decay algorithm that captures indirect caller drift along reverse call edges.
* **Selective Invalidation Engine:** A high-precision filter that isolates stale code entities while leaving fresh cached vectors intact.
* **Production Integration Plugin:** A production-ready extension (`llama_index_integration.py`) implementing `CodeGraphNodeParser` and `PredictiveCacheFilter` for LlamaIndex.
* **Substantial Overhead Reduction:** Target reduction in re-embedding compute and API token costs by up to 90% compared to full re-indexing.
* **Rigorous Benchmark Evaluation:** Comprehensive empirical evaluation against standard baselines across Recall@K, Cost Ratio %, Fidelity MAE, and sub-0.15s decision latency.

### 2.3 Technical and Resource Feasibility Analysis
The project feasibility is thoroughly evaluated across five primary dimensions:

#### 2.3.1 Hardware and Software Requirements
The framework is designed to run on standard commodity hardware (minimum 8 GB RAM, standard CPU/GPU). Software dependencies are lightweight, requiring Python 3.9+, NetworkX, Scikit-Learn, and LlamaIndex.

#### 2.3.2 Dataset Availability
Extensive open-source Git repository histories (such as `psf/black`) provide rich, real-world commit diffs and co-evolution data for model training and evaluation.

#### 2.3.3 Model Availability
Pre-trained, state-of-the-art neural code embedding models (`microsoft/unixcoder-base`, `sentence-transformers/all-MiniLM-L6-v2`) are publicly accessible for ground-truth vector generation.

#### 2.3.4 Implementation Feasibility
By building the core parsing and topological engine using native Python `ast` and NetworkX graph algorithms, the system operates at a target algorithmic complexity of $O(V + E \log V)$ with a target local memory footprint under $200\text{MB}$ RAM, avoiding heavy external server daemons.

#### 2.3.5 Deployment Feasibility
The system packages its output as a LlamaIndex `TransformComponent`, allowing seamless drop-in integration into existing production vector store pipelines (ChromaDB, Qdrant).

---

## Section III: Literature Review and Research Gap Synthesis

The challenge of maintaining semantic consistency in vector-based retrieval indices as underlying codebases evolve sits at the intersection of repository mining, change analysis, code embeddings, RAG architectures, and cache invalidation. Below, we review seminal papers categorized into key technical domains.

### 3.1 Repository Mining and Change Analysis

#### 3.1.1 ChangeDistiller: Fine-Grained AST Tree Differencing
*Fluri et al. (IEEE TSE 2025):* Pioneered AST differencing beyond line diffs, extracting tree edit operations (insertions, deletions, moves) to isolate structural code modifications. We adopt this tree-edit philosophy for cosmetic filtering.

#### 3.1.2 Node Feature Enhancement for Code Difference Extraction
*Zhang et al. (IEEE AUTEEE 2024):* Enhanced AST differencing with semantic node attributes to distinguish genuine node movements from text edits, motivating our Stage 1 normalization.

#### 3.1.3 Logical Coupling Mining from Software Changes
*Wetzlmaier et al. (IEEE IWSM 2014):* Demonstrated that logical dependencies between heterogeneous artifacts can be mined from co-evolution histories, motivating our historical volatility features.

### 3.2 Dependency Graphs and Commit Semantics

#### 3.2.1 SDG Commit Classification via Graph Neural Networks
*Zhang et al. (IEEE QRS 2023):* Constructed System Dependency Graphs (SDGs) from commit diffs, using program slicing and GCNs to classify commit impact, proving that graph structures outperform flat text diffs.

#### 3.2.2 UntCC: Untangling Composite Commits via Graph Autoencoders
*Jin et al. (IEEE TSE 2026):* Combined LLaMA-3.2-3B embeddings with graph autoencoders over code-change graphs, proving that joint structural-semantic representations effectively separate code edits.

#### 3.2.3 Keyword-Connected PDGs for Fine-Grained Clone Detection
*Wu et al. (IEEE TR 2025):* Connected Program Dependency Graph (PDG) nodes through shared keywords to improve clone detection.

#### 3.2.4 Maintenance Consistency Prediction in Code Clones
*Zhang et al. (IEEE Access 2020):* Demonstrated that machine-learned predictive models operating on structural clone attributes forecast maintenance propagation.

### 3.3 Code Embedding Models and Semantic Drift

#### 3.3.1 UniXcoder, CodeBERT, and GraphCodeBERT
*Guo et al. (ACL 2022), Feng et al. (EMNLP 2020), Guo et al. (ICLR 2021):* Established pre-trained transformer architectures for code representations. UniXcoder serves as our primary baseline embedding backbone.

#### 3.3.2 code2vec and ASTminer for Code Embeddings
*Ngo et al. (IEEE SEAI 2023):* Explored code2vec with AST path sampling for Python code embeddings.

#### 3.3.3 Longitudinal Code Embedding Evolution
*He et al. (Journal of Comput. Sci. 2026):* Modeled codebase evolution by tracking code embedding trajectories longitudinally.

#### 3.3.4 Memory-Augmented Feature Drift Management
*Wu et al. (Knowledge-Based Systems 2026):* Addressed feature drift using an age-weighted memory queue with exponential decay.

### 3.4 Retrieval-Augmented Generation and Cache Invalidation

#### 3.4.1 Enterprise RAG Architectures and Index Staleness
*Lewis et al. (NeurIPS 2020), Gao et al. (2023), Ersoy & Erşahın (IEEE Access 2025):* Formalized RAG pipelines and surveyed enterprise deployments, identifying vector index staleness as a primary bottleneck.

#### 3.4.2 Real-Time Event-Driven RAG Index Updates
*Mijić & Isaković (IEEE IT 2026):* Designed a production-grade streaming RAG pipeline that reduces propagation latency.

#### 3.4.3 Trust-Aware Multi-Agent Knowledge Graphs
*Essam et al. (IEEE MECO 2026):* Used confidence-calibrated knowledge graphs as shared semantic memory surfaces.

#### 3.4.4 CacheSense: Selective Document Cache Invalidation
*Dang et al. (IEEE CAIBDA 2026):* Introduced a semantic caching framework that selectively invalidates document-level cache entries based on similarity thresholds.

#### 3.4.5 Virtual Data Center Re-Embedding Optimization
*Satpathy et al. (IEEE TGCN 2024):* Formulated selective re-embedding as a resource optimization problem using genetic algorithms.

#### 3.4.6 Athena: Transformer + PDG Change Impact Analysis
*Yan et al. (ACM FSE 2024):* Fused transformer embeddings with Program Dependence Graphs (PDGs) for method impact set prediction.

### 3.5 Literature Comparison and Research Gap Synthesis

| Approach / Reference | Core Mechanism | Identified Limitations | Our Proposed Solution |
| :--- | :--- | :--- | :--- |
| **Full Re-Indexing** (Gao et al. 2023) | Re-embeds 100% of files on every commit. | $O(N)$ token and compute costs; fails to scale to large repos. | **Selective Re-Embedding:** Targets re-embedding to ~1.4%--5% of nodes, aiming to save >90% cost. |
| **LlamaIndex** `refresh_ref_docs` | File-hash matching at the document level. | Re-embeds entire files if 1 line changes; misses caller drift across files. | **AST Entity Resolution:** Function-level invalidation with cosmetic comment filtering. |
| **ChangeDistiller** (Fluri et al. 2025) | Tree-differencing for AST edit extraction. | Focuses on software history mining, not vector embedding maintenance. | **AST + Drift Predictor:** Uses AST diffs as features for ML vector drift prediction. |
| **CacheSense** (Dang et al. 2026) | Document-level selective cache invalidation. | Operates on generic text documents, lacking call-graph topological signals. | **Graph-Aware Invalidation:** Uses NetworkX PageRank \& BFS Decay over code call graphs. |
| **Athena** (Yan et al. ACM FSE 2024) | Transformer embeddings + PDG for impact sets. | Targets developer impact set analysis rather than vector store cache freshness. | **Predictive ML Invalidation:** Predicts continuous cosine drift ($1 - \text{sim}$) for RAG indices. |

#### 3.5.1 Limitations of Existing Approaches
Prior work in vector store maintenance relies on brute-force full re-indexing or flat document-hash matching. Brute-force re-indexing incurs $O(N)$ token cost, while document-hash matching ignores dependency structures, leaving dependent caller functions with stale cached embeddings. Conversely, software change impact tools (e.g., Athena) analyze developer change sets but do not predict vector space drift or interface with production RAG vector stores.

#### 3.5.2 Synthesized Research Gap
Existing research lacks a **lightweight, graph-aware predictive invalidation framework** that connects static AST call-graph topology with machine-learned vector drift prediction ($1 - \text{cosine\_similarity}$) specifically designed for production vector database ingestion pipelines.

#### 3.5.3 How Our Proposed Project Addresses the Gap
Our project addresses this gap by combining: (1) round-trip AST cosmetic comment filtering, (2) 25 topological NetworkX features, (3) Random Forest ML drift regression, (4) Weighted BFS Decay reverse propagation, and (5) a native LlamaIndex integration plugin (`PredictiveCacheFilter`).

---

## Section IV: Overview of Feature Taxonomy (25 Native Signals)

To model vector space drift ($D_{\text{cosine}} = 1 - \text{cosine\_similarity}$), our native feature extraction engine calculates 25 structural signals across five primary mathematical categories:

### 4.1 Git Edit Distance and Volatility (6 Features)
`file_lines_added`, `file_lines_deleted`, `entity_size`, `entity_modification_size`, `modification_frequency`, `previous_drift`.

### 4.2 Graph Topology and Centrality (5 Features)
`in_degree` (caller count), `out_degree` (callee count), `pagerank`, `closeness`, `betweenness`.

### 4.3 Change Propagation and Shortest Path (4 Features)
`distance_to_modified_directed`, `distance_to_modified_undirected`, `modified_dependents_count`, `modified_dependencies_count`.

### 4.4 Personalized PageRank and Transition Descriptors (7 Features)
`pagerank_impact` (Personalized PageRank seeded on modified nodes), `gtd_change_class`, `gtd_local_edges_added`, `gtd_local_edges_removed`, `gtd_local_edge_churn`, `gtd_mean_drift`, `gtd_drift_variance`.

### 4.5 Native AST Code Complexity Metrics (3 Features)
`cyclomatic_complexity` ($1 + \sum \text{branches}$), `ast_node_count`, `max_nesting_depth`.

---

## Section V: System Methodology and 3-Phase Pipeline Architecture

The proposed predictive semantic cache invalidation framework operates as a highly optimized, end-to-end processing pipeline divided into three distinct operational phases: (1) Offline Dataset Generation and ML Model Training, (2) Real-Time Git Commit Processing and Predictive Invalidation, and (3) Production RAG Integration and Vector Store Refresh.

```
                                  FIGURE 1: 3-PHASE PIPELINE ARCHITECTURE

  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │ PHASE 1: OFFLINE MODEL TRAINING                                                          │
  │   Historical Git Commits ──► AST Graph (RepoParser) ──► BFS Features (25 Signals)        │
  │   Ground-Truth Vector Drift (1 - sim) ───────────────► Train Random Forest Regressor     │
  └───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                              │ Model Weights
                                              ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │ PHASE 2: LIVE GIT COMMIT PREDICTIVE INVALIDATION                                         │
  │   New Live Git Commit ──► Stage 1: Cosmetic AST Filter (ignore whitespace/comments)      │
  │                       ──► Stage 2: Fast BFS Feature Engine (<0.15s, no embeddings)       │
  │                       ──► Stage 3: ML Drift Inference (Predict continuous drift)          │
  │                       ──► Stage 4: Weighted BFS Decay Cascade (Propagate to callers)      │
  └───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                              │ Stale Node List
                                              ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────┐
  │ PHASE 3: PRODUCTION RAG VECTOR STORE REFRESH                                             │
  │   LlamaIndex IngestionPipeline ──► PredictiveCacheFilter                                 │
  │                                    ├── Stale Nodes: Re-embed & Update ChromaDB / Qdrant  │
  │                                    └── Fresh Nodes: Bypass Re-embedding (Reuse Vectors)  │
  └──────────────────────────────────────────────────────────────────────────────────────────┘
```

```
                                  FIGURE 2: COMPONENT INTERACTION CLASS DIAGRAM

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ RepoParser (Pass 1 & 2): Parses AST entities, resolves import symbol tables & call edges│
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ nx.DiGraph & Symbol Table
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ FeatureExtractor (BFS Engine): Computes shortest paths, PageRank impact & 25 metrics    │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ Feature Matrix
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ DriftPredictor (ML + BFS Decay): Predicts drift, runs Weighted BFS Decay propagation    │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ Invalidation Candidate Set
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ PredictiveCacheFilter (LlamaIndex): Intercepts nodes, passes stale nodes to Vector DB   │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
```

### 5.1 Phase 1: Offline Dataset Generation and ML Model Training
* **5.1.1 Historical Repository Ingestion:** Samples commit pairs $(C_i \to C_{i+1})$ across fixed strides.
* **5.1.2 AST Call Graph Construction:** `RepoParser` runs Pass 1 entity discovery and Pass 2 call edge resolution.
* **5.1.3 BFS Graph Feature Extraction (Role #1 of BFS):** Computes shortest paths (`distance_to_modified_directed`) and Personalized PageRank (`pagerank_impact`).
* **5.1.4 Ground-Truth Labeling & Model Training:** Generates pre/post commit vectors ($v^{(i)}, v^{(i+1)}$), computes $D_{\text{cosine}} = 1 - \text{cosine\_similarity}$, and trains a Random Forest regressor ($N=100$ trees).

### 5.2 Phase 2: Real-Time Git Commit Processing and Predictive Invalidation
* **5.2.1 Stage 1 (AST Cosmetic Filter):** Round-trip AST compilation strips docstrings, formatting, and comments.
* **5.2.2 Stage 2 (Fast Feature Computation):** Calculates 25 topological signals on the fly with a target decision latency of sub-0.15s per commit pair.
* **5.2.3 Stage 3 (ML Drift Inference):** Random Forest predicts drift $\hat{D}_{\text{cosine}}$.
* **5.2.4 Stage 4 (Weighted BFS Decay Cascade - Role #2 of BFS):** Propagates invalidation scores $S(v)$ along reverse call-graph edges. To ensure sub-0.15s execution without generating neural embeddings during inference, the decay formula uses static AST edit similarity $\text{ASTSim}(u_{\text{old}}, u_{\text{new}})$ or ML-predicted similarity $(1 - \hat{D}_{\text{cosine}}(u))$:
  $$S(v) = S(u) \cdot \Big( \alpha \cdot \text{PPR}(v) + \beta \cdot \text{CallFreqNorm}(v, u) + \gamma \cdot \text{ASTSim}(u_{\text{old}}, u_{\text{new}}) \Big)$$
* **5.2.5 Stage 5 (Minimal Stale Entity Output):** Outputs candidate invalidation set.

### 5.3 Phase 3: Production RAG Integration and Vector Store Refresh
* **5.3.1 LlamaIndex Integration:** Provides `CodeGraphNodeParser` and `PredictiveCacheFilter`.
* **5.3.2 Selective Vector Refresh:** `PredictiveCacheFilter` re-embeds stale nodes and updates ChromaDB/Qdrant while bypassing fresh nodes.
* **5.3.3 Enterprise Advantages:** Targets up to 90% re-embedding cost reduction with sub-second decision turnaround.

---

## Section VI: Experimental Protocol and Benchmarking Architecture

### 6.1 Target Repository and Commit Sampling Protocol
Evaluates on `psf/black` (~350 Python files) using stride commit sampling.

### 6.2 Comparison Baselines
Evaluates four strategies: `full_reembed`, `changed_only`, `fixed_hop`, and `predictive_ml`.

### 6.3 Benchmarking Pipeline Execution Architecture

```
                  FIGURE 3: AUTOMATED BENCHMARKING PIPELINE EXECUTION ARCHITECTURE

   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ Commit Sampler Module (commit_sampler.py): Samples Git commit snapshots across strides  │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ Git Snapshots (C_i -> C_i+1)
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ Balanced Query Generator (query_generator.py): 20 Queries (15 Drifted + 5 Fresh)        │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ Search Benchmarks
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ Strategy Execution Runner (runner.py / evaluator.py): Runs 4 Strategies vs. Vector DB   │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                               │ Search Retrieval Results
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐
   │ Metrics Calculator (metrics.py): Calculates Cost Ratio %, Recall@K, Precision & Latency │
   └───────────────────────────────────────────┬─────────────────────────────────────────────┘
```

* **6.3.1 Commit Sampler (`commit_sampler.py`):** Extracts temporal codebase snapshots across strides.
* **6.3.2 Balanced Query Generator (`query_generator.py`):** Generates 20 queries (15 drifted + 5 fresh).
* **6.3.3 Strategy Execution Runner (`runner.py` / `evaluator.py`):** Evaluates strategies against vector store.
* **6.3.4 Metrics Calculator (`metrics.py`):** Computes Cost Ratio %, Recall@K, Precision@K, MAE, and Latency.

---

## Section VII: Risk Management, Governance, and Conclusion

### 7.1 Structured Technical Risk Management

| Identified Risk | Risk Impact | Mitigation Strategy |
| :--- | :---: | :--- |
| Incomplete Call Resolution | Missed caller dependencies | Two-pass symbol resolution matching imported modules and method suffixes. |
| False Invalidation | Extra embedding costs | Round-trip AST compilation stripping comments and docstring edits. |
| Missed Vector Drift | Retrieval quality decay | Weighted BFS Decay propagating decay scores along reverse call edges. |
| Large Repo Overhead | Processing latency | Fast static graph feature extraction in sub-0.15s without vector generation. |
| Model Prediction Error | Inaccurate invalidation | Dynamic percentile thresholding ($\tau$) and hyperparameter tuning. |

### 7.2 Ethical Considerations and Responsible Governance
* **Open-Source Data Usage:** All commit histories derived from public open-source software repositories.
* **Software License Compliance:** Respects open-source licensing terms (MIT, Apache 2.0).
* **Local Execution & Privacy:** Executes locally; proprietary source code is never transmitted to cloud APIs.
* **Responsible Code AI Usage:** Acknowledges model and static analysis limitations, providing calibrated invalidation thresholds.

### 7.3 Conclusion and Future Roadmap
In conclusion, this project proposes a native, graph-aware predictive cache invalidation framework for vector-based code search and RAG systems, solving index staleness with high efficiency. Future work will explore multi-language parsing via Tree-sitter.

---

## References

1. B. Fluri, M. Würsch, M. Pinzger, and H. Gall, "A retrospective of ChangeDistiller: Tree differencing for fine-grained source code change extraction," *IEEE Transactions on Software Engineering*, vol. 51, no. 3, pp. 852–857, 2025.
2. R. Zhang, K. Wang, R. Duan, and L. Li, "A code difference extraction method based on node feature enhancement," in *Proc. IEEE AUTEEE*, 2024, pp. 110–115.
3. T. Wetzlmaier, C. Klammer, and R. Ramler, "Extracting dependencies from software changes: An industry experience report," in *Proc. IEEE IWSM-Mensura*, 2014, pp. 163–168.
4. Z. Zhang, L. Liu, J. Chang, L. Wang, and L. Liao, "Commit classification via diff-code GCN based on system dependency graph," in *Proc. IEEE QRS*, 2023, pp. 476–487.
5. Y. Jin et al., "UntCC: Untangling composite commits using structural and semantic information," *IEEE Transactions on Software Engineering*, vol. 52, no. 8, pp. 2282–2302, 2026.
6. Y. Wu, W. Suo, S. Feng, C. Wu, D. Zou, and H. Jin, "Fine-grained code clone detection by keywords-based connection of program dependency graph," *IEEE Transactions on Reliability*, vol. 74, no. 3, pp. 3427–3441, 2025.
7. F. Zhang, S.-C. Khoo, and X. Su, "Improving maintenance-consistency prediction during code clone creation," *IEEE Access*, vol. 8, pp. 82085–82099, 2020.
8. D. Guo et al., "UniXcoder: Unified cross-modal pre-training for code representation," in *Proc. ACL*, 2022, pp. 7212–7225.
9. Z. Feng et al., "CodeBERT: A pre-trained model for programming and natural languages," in *Proc. EMNLP*, 2020, pp. 1536–1547.
10. D. Guo et al., "GraphCodeBERT: Pre-training code representations with data flow," in *Proc. ICLR*, 2021.
11. L. H. Ngo, V. Sekar, E. Leclercq, and J. Rivalan, "Exploring code2vec and ASTminer for Python code embeddings," in *Proc. IEEE SEAI*, 2023, pp. 53–57.
12. Y. He, N. Verbin, and S. Kovalchuk, "Social life of code: Modeling evolution through code embedding and opinion dynamics," *Journal of Computational Science*, vol. 96, p. 102824, 2026.
13. Q. Wu et al., "Dual-stage method with memory-augmented embedding learning and attention-guided re-ranking..." *Knowledge-Based Systems*, vol. 340, p. 115677, 2026.
14. P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Proc. NeurIPS*, vol. 33, 2020, pp. 9459–9474.
15. Y. Gao et al., "Retrieval-augmented generation for large language models: A survey," *arXiv preprint arXiv:2312.10997*, 2023.
16. P. Ersoy and M. Erşahın, "A comparative evaluation of RAG architectures for cross-domain LLM applications," *IEEE Access*, vol. 13, pp. 194185–194196, 2025.
17. I. Mijić and B. Isaković, "Design and implementation of a real-time RAG-based customer relationship management system..." in *Proc. IEEE IT*, 2026, pp. 1–4.
18. M. Essam et al., "Trust-aware multi-agent traceability: Confidence-calibrated knowledge graphs..." in *Proc. IEEE MECO*, 2026, pp. 1–8.
19. S. Dang, C. Chen, K. Wu, Z. Liu, and Y. Yang, "CacheSense: Freshness-aware semantic caching with selective invalidation for LLM-serving backends," in *Proc. IEEE CAIBDA*, 2026, pp. 1522–1527.
20. A. Satpathy et al., "GAMap: A genetic algorithm-based effective virtual data center re-embedding strategy," *IEEE Transactions on Green Communications and Networking*, vol. 8, no. 2, pp. 791–801, 2024.
21. Y. Yan et al., "Enhancing code understanding for impact analysis by combining transformers and program dependence graphs," in *Proc. ACM Software Engineering (FSE)*, 2024.

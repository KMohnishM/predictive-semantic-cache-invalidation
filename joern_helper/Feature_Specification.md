# Joern Feature Specification & Data Flow Mapping

This document details the master list of all **25 predictive features** used by the `DriftPredictor` ML model, mapping each feature to its precise data source module.

---

## 1. Joern CPG Helper (`joern_interactive.py`) — 13 Features
*Extracted directly from Joern's Code Property Graph (AST + Control Flow + Data Flow)*

| # | Feature Name | Joern Layer | CPGQL Query / Method | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `in_degree` | **Call Graph** | `cpg.method.name("X").caller.size` | Number of direct callers |
| 2 | `out_degree` | **Call Graph** | `cpg.method.name("X").callee.size` | Number of direct callees |
| 3 | `distance_to_modified_directed` | **Call Graph** | Shortest path query | Direct hop distance to nearest modified node |
| 4 | `distance_to_modified_undirected`| **Call Graph** | Undirected path query | Undirected hop distance to modified node |
| 5 | `modified_dependents_count` | **Call Graph** | Filter callers by modified set | Count of modified entities that call this entity |
| 6 | `joern_transitive_callers_count` | **Call Graph** | `repeat(_.caller)(_.emit).size` | Recursive multi-hop caller count |
| 7 | `joern_transitive_callees_count` | **Call Graph** | `repeat(_.callee)(_.emit).size` | Recursive multi-hop callee count |
| 8 | `joern_cyclomatic_complexity` | **CFG** (Control Flow) | `cpg.method.name("X").controlStructure.size` | Count of decision branches (`if`, `while`, `for`) |
| 9 | `joern_cfg_node_count` | **CFG** (Control Flow) | `cpg.method.name("X").cfgNode.size` | Total control flow instruction nodes in method |
| 10 | `joern_cfg_affected_depth` | **CFG** (Control Flow) | `cpg.method.name("X").controlStructure.lineNumber` | Nesting depth of conditional blocks touched by edits |
| 11 | `joern_data_flow_distance` | **PDG** (Data Flow) | `parameter.reachableByFlows(...)` | Path distance along actual **variable/data movement** |
| 12 | `joern_modified_data_deps_count` | **PDG** (Data Flow) | `parameter.reachableByFlows(...).size` | Count of parameters receiving data from modified nodes |
| 13 | `joern_taint_reachability_score` | **PDG** (Data Flow) | Reachability flow score | Reachability score (0.0 to 1.0) of modified data |

---

## 2. Git Helper (`src/git_helper.py`) — 4 Features
*Extracted directly from Git repository diffs and commit logs*

| # | Feature Name | Source | Description |
| :--- | :--- | :--- | :--- |
| 14 | `lines_added` | `git diff` | Number of lines added to this entity in current commit diff |
| 15 | `lines_deleted` | `git diff` | Number of lines deleted from this entity in current commit diff |
| 16 | `loc` | Source AST | Total lines of code in this entity |
| 17 | `modification_frequency` | `git log` | How often this entity was edited across recent Git commits |

---

## 3. Embedding Manager (`src/embedding_manager.py`) — 3 Features
*Computed from vector embeddings and cosine similarity distances*

| # | Feature Name | Source | Description |
| :--- | :--- | :--- | :--- |
| 18 | `previous_drift` | Vector Cosine Distance | Semantic drift score from the *previous* commit transition |
| 19 | `pagerank` | NetworkX | Centrality score computed on the Joern call graph nodes |
| 20 | `pagerank_impact` | NetworkX + PPR | Personalized PageRank flow seeded specifically on modified nodes |

---

## 4. GTD Module (`src/gtd.py`) — 5 Features
*Computed by comparing Joern's Graph snapshot $G_t$ against $G_{t+1}$ in Python*

| # | Feature Name | Source | Description |
| :--- | :--- | :--- | :--- |
| 21 | `gtd_change_class` | Graph Diff | Entity state classification (0=unchanged, 1=added, 2=deleted, 3=modified) |
| 22 | `gtd_local_edges_added` | Graph Diff | Number of new call/data edges connected to this node in $G_{t+1}$ |
| 23 | `gtd_local_edges_removed` | Graph Diff | Number of removed call/data edges connected to this node in $G_{t+1}$ |
| 24 | `gtd_local_edge_churn` | Graph Diff | Total edge mutations touching this node |
| 25 | `joern_signature_changed` | Signature Diff | Flag indicating if parameter list or return signature mutated between $G_t$ and $G_{t+1}$ |

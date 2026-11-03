# Graph Features & AST Analysis

`predictive-semantic-cache` extracts 47 features combining Abstract Syntax Tree (AST) analysis, graph theory, and Git revision deltas.

---

## 1. Feature Categories

### A. Graph Topologies & Centrality
- `in_degree`, `out_degree`: Number of callers and callees.
- `pagerank`: Global authority and centrality of the code entity.
- `betweenness`, `closeness`: Node position in call flow paths.
- `distance_to_modified_directed`: Directed graph distance to the nearest directly modified entity.
- `distance_to_modified_undirected`: Undirected graph distance.

### B. AST & Syntactic Complexity
- `cyclomatic_complexity`: Branching complexity extracted via Tree-sitter.
- `ast_node_count`: Size of the parsed syntax tree.
- `max_nesting_depth`: Maximum depth of loops and conditional blocks.
- `entity_size`: Character length of the entity.

### C. Graph Transition Descriptors (GTD)
Captures local call-graph edge churn between revisions:
- `gtd_local_edges_added`: New outgoing or incoming calls.
- `gtd_local_edges_removed`: Deleted calls.
- `gtd_local_edge_churn`: Total edge modification rate.

### D. Repository State Descriptors (RSD)
Macro-level structural evolution of the codebase:
- `se_node_growth_ratio`: Proportional entity additions.
- `se_edge_growth_ratio`: Proportional relationship additions.
- `ce_mean_pagerank_shift`: Macro drift in repository architecture.

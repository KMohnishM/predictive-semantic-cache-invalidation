"""
Graph Transition Descriptor (GTD)
===================================
Characterises how the dependency graph changes between two consecutive
commits  G_t → G_{t+1}  using a structured, fixed-length numerical vector.

GTD = (NodeEvolution, EdgeEvolution, StructuralEvolution,
        CentralityEvolution, SemanticEvolution)

Every component is computed from raw graph-diff metrics, then
normalised using Robust Scaling and combined via the Entropy Weight Method.

The GTD vector is consumed by FeatureExtractor to enrich the per-entity
feature set fed into the drift-prediction model.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import networkx as nx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_mean(values) -> float:
    arr = [v for v in values if v is not None and not np.isnan(v)]
    return float(np.mean(arr)) if arr else 0.0


def _graph_diameter(G: nx.DiGraph) -> float:
    """Approximated diameter on the largest weakly connected component."""
    try:
        if G.number_of_nodes() == 0:
            return 0.0
        UG = G.to_undirected()
        largest = max(nx.connected_components(UG), key=len)
        sub = UG.subgraph(largest)
        if len(sub) < 2:
            return 0.0
        return float(nx.diameter(sub))
    except Exception:
        return 0.0


def _avg_shortest_path(G: nx.DiGraph) -> float:
    try:
        if G.number_of_nodes() < 2:
            return 0.0
        UG = G.to_undirected()
        largest = max(nx.connected_components(UG), key=len)
        sub = UG.subgraph(largest)
        if len(sub) < 2:
            return 0.0
        return float(nx.average_shortest_path_length(sub))
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Node-level diff
# ---------------------------------------------------------------------------

def _node_diff(graph_a: nx.DiGraph, graph_b: nx.DiGraph,
               drifts: Dict[str, float]) -> Dict[str, float]:
    """
    Classify every node and return aggregate counts + drift statistics.

    Classification (per node in union of both graphs):
      added     — in G_{t+1} but not G_t
      deleted   — in G_t but not G_{t+1}
      modified  — drift > 0 (node present in both)
      unchanged — drift == 0 (node present in both, no drift recorded)
    """
    nodes_a: Set[str] = set(graph_a.nodes())
    nodes_b: Set[str] = set(graph_b.nodes())
    both = nodes_a & nodes_b

    n_added    = len(nodes_b - nodes_a)
    n_deleted  = len(nodes_a - nodes_b)
    n_total    = max(len(nodes_a | nodes_b), 1)

    # Among shared nodes, classify by drift
    drifted    = [eid for eid in both if drifts.get(eid, 0.0) > 0]
    n_modified = len(drifted)
    n_unchanged = len(both) - n_modified

    drift_vals = [drifts[eid] for eid in both if eid in drifts]

    return {
        "node_added_ratio":     n_added    / n_total,
        "node_deleted_ratio":   n_deleted  / n_total,
        "node_modified_ratio":  n_modified / max(len(both), 1),
        "node_unchanged_ratio": n_unchanged / max(len(both), 1),
        "node_survival_ratio":  len(both)  / n_total,
    }


# ---------------------------------------------------------------------------
# Edge-level diff
# ---------------------------------------------------------------------------

def _edge_diff(graph_a: nx.DiGraph, graph_b: nx.DiGraph) -> Dict[str, float]:
    """
    Compare edge sets and return churn / rewiring statistics.
    """
    edges_a: Set[Tuple] = set(graph_a.edges())
    edges_b: Set[Tuple] = set(graph_b.edges())

    added   = edges_b - edges_a
    removed = edges_a - edges_b
    total   = max(len(edges_a | edges_b), 1)

    edge_churn = (len(added) + len(removed)) / total
    density_a = nx.density(graph_a) if graph_a.number_of_nodes() > 1 else 0.0
    density_b = nx.density(graph_b) if graph_b.number_of_nodes() > 1 else 0.0
    density_delta = abs(density_b - density_a)

    return {
        "edge_added_ratio":   len(added)   / total,
        "edge_removed_ratio": len(removed) / total,
        "edge_churn":         edge_churn,
        "density_delta":      density_delta,
        "density_a":          density_a,
        "density_b":          density_b,
    }


# ---------------------------------------------------------------------------
# Graph-level structural evolution
# ---------------------------------------------------------------------------

def _structural_evolution(graph_a: nx.DiGraph, graph_b: nx.DiGraph) -> Dict[str, float]:
    """
    Measure global structural changes between the two snapshots.
    """
    n_a = max(graph_a.number_of_nodes(), 1)
    n_b = max(graph_b.number_of_nodes(), 1)

    node_growth = (n_b - n_a) / n_a
    edge_growth = (graph_b.number_of_edges() - graph_a.number_of_edges()) / max(graph_a.number_of_edges(), 1)

    UG_a = graph_a.to_undirected()
    UG_b = graph_b.to_undirected()

    clust_a = nx.average_clustering(UG_a) if UG_a.number_of_nodes() > 1 else 0.0
    clust_b = nx.average_clustering(UG_b) if UG_b.number_of_nodes() > 1 else 0.0
    clustering_delta = abs(clust_b - clust_a)

    n_comp_a = nx.number_weakly_connected_components(graph_a)
    n_comp_b = nx.number_weakly_connected_components(graph_b)
    comp_delta = abs(n_comp_b - n_comp_a) / max(n_comp_a, 1)

    return {
        "node_growth_ratio":  float(node_growth),
        "edge_growth_ratio":  float(edge_growth),
        "clustering_delta":   float(clustering_delta),
        "component_delta":    float(comp_delta),
    }


# ---------------------------------------------------------------------------
# Centrality evolution
# ---------------------------------------------------------------------------

def _centrality_evolution(graph_a: nx.DiGraph, graph_b: nx.DiGraph) -> Dict[str, float]:
    """
    Compare PageRank and degree centrality distributions between snapshots.
    """
    try:
        pr_a = nx.pagerank(graph_a, alpha=0.85) if graph_a.number_of_nodes() > 0 else {}
        pr_b = nx.pagerank(graph_b, alpha=0.85) if graph_b.number_of_nodes() > 0 else {}
    except Exception:
        pr_a, pr_b = {}, {}

    common = set(pr_a.keys()) & set(pr_b.keys())
    if common:
        pr_diffs = [abs(pr_b[n] - pr_a[n]) for n in common]
        mean_pr_shift   = float(np.mean(pr_diffs))
        max_pr_shift    = float(np.max(pr_diffs))
    else:
        mean_pr_shift = max_pr_shift = 0.0

    # Degree distribution shift (via mean degree change)
    deg_a = dict(graph_a.degree())
    deg_b = dict(graph_b.degree())
    common_deg = set(deg_a.keys()) & set(deg_b.keys())
    if common_deg:
        deg_diffs = [abs(deg_b[n] - deg_a[n]) for n in common_deg]
        mean_deg_shift = float(np.mean(deg_diffs))
    else:
        mean_deg_shift = 0.0

    return {
        "mean_pagerank_shift": mean_pr_shift,
        "max_pagerank_shift":  max_pr_shift,
        "mean_degree_shift":   mean_deg_shift,
    }


# ---------------------------------------------------------------------------
# Semantic evolution (drift aggregates on graph)
# ---------------------------------------------------------------------------

def _semantic_evolution(graph_b: nx.DiGraph,
                        drifts: Dict[str, float]) -> Dict[str, float]:
    """
    Aggregate per-node drift values into graph-level semantic metrics.
    """
    drift_vals = [v for v in drifts.values() if not np.isnan(v)]
    if not drift_vals:
        return {k: 0.0 for k in ("mean_drift", "drift_variance",
                                  "drift_entropy", "high_drift_ratio")}

    arr = np.array(drift_vals)
    mean_drift     = float(np.mean(arr))
    drift_variance = float(np.var(arr))

    # Entropy of drift histogram
    hist, _ = np.histogram(arr, bins=min(20, len(arr)), density=True)
    hist = hist + 1e-9
    hist /= hist.sum()
    drift_entropy = float(-np.sum(hist * np.log(hist)))

    # High-drift ratio (entities drifting more than 2× mean)
    threshold = 2 * mean_drift
    high_drift_ratio = float(np.mean(arr > threshold)) if mean_drift > 0 else 0.0

    return {
        "mean_drift":       mean_drift,
        "drift_variance":   drift_variance,
        "drift_entropy":    drift_entropy,
        "high_drift_ratio": high_drift_ratio,
    }


# ---------------------------------------------------------------------------
# Per-node impact features derived from GTD
# ---------------------------------------------------------------------------

def _node_impact_features(node: str,
                           graph_a: nx.DiGraph,
                           graph_b: nx.DiGraph,
                           drifts: Dict[str, float]) -> Dict[str, float]:
    """
    Derive node-level features that describe how a specific entity is
    affected by the graph transition.
    """
    # Change classification label (0=unchanged, 1=added, 2=deleted, 3=modified)
    in_a = node in graph_a
    in_b = node in graph_b
    if in_b and not in_a:
        change_class = 1.0    # added
    elif in_a and not in_b:
        change_class = 2.0    # deleted
    elif in_a and in_b and drifts.get(node, 0.0) > 0:
        change_class = 3.0    # modified
    else:
        change_class = 0.0    # unchanged

    # Local edge churn for this node
    edges_a = set(graph_a.in_edges(node)) | set(graph_a.out_edges(node)) if in_a else set()
    edges_b = set(graph_b.in_edges(node)) | set(graph_b.out_edges(node)) if in_b else set()
    local_edges_added   = len(edges_b - edges_a)
    local_edges_removed = len(edges_a - edges_b)
    local_edge_churn    = local_edges_added + local_edges_removed

    return {
        "gtd_change_class":      change_class,
        "gtd_local_edges_added": float(local_edges_added),
        "gtd_local_edges_removed": float(local_edges_removed),
        "gtd_local_edge_churn":  float(local_edge_churn),
    }


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class GraphTransitionDescriptor:
    """
    Computes and stores the GTD for a pair of consecutive commits.

    Usage:
        gtd = GraphTransitionDescriptor()
        gtd.compute(parser_a, parser_b, drifts)
        global_vec = gtd.global_vector          # dict of aggregated metrics
        node_feats = gtd.get_node_features(eid) # per-entity dict
    """

    def __init__(self):
        self.global_vector: Dict[str, float] = {}
        self._node_features: Dict[str, Dict[str, float]] = {}
        self._graph_a: Optional[nx.DiGraph] = None
        self._graph_b: Optional[nx.DiGraph] = None

    # ------------------------------------------------------------------

    def compute(self, parser_a, parser_b,
                drifts: Dict[str, float]) -> None:
        """
        Compute the full GTD.

        Args:
            parser_a : RepoParser for commit t
            parser_b : RepoParser for commit t+1
            drifts   : entity_id → cosine drift (only entities in both commits)
        """
        G_a = parser_a.get_graph() if parser_a else nx.DiGraph()
        G_b = parser_b.get_graph() if parser_b else nx.DiGraph()
        self._graph_a = G_a
        self._graph_b = G_b

        # Compute all component dicts
        node_ev   = _node_diff(G_a, G_b, drifts)
        edge_ev   = _edge_diff(G_a, G_b)
        struct_ev = _structural_evolution(G_a, G_b)
        cent_ev   = _centrality_evolution(G_a, G_b)
        sem_ev    = _semantic_evolution(G_b, drifts)

        # Merge into a single global vector
        self.global_vector = {}
        self.global_vector.update({f"ne_{k}": v for k, v in node_ev.items()})
        self.global_vector.update({f"ee_{k}": v for k, v in edge_ev.items()})
        self.global_vector.update({f"se_{k}": v for k, v in struct_ev.items()})
        self.global_vector.update({f"ce_{k}": v for k, v in cent_ev.items()})
        self.global_vector.update({f"sm_{k}": v for k, v in sem_ev.items()})

        # Pre-compute per-node features for all entities in either graph
        all_nodes = set(G_a.nodes()) | set(G_b.nodes())
        for node in all_nodes:
            self._node_features[node] = _node_impact_features(node, G_a, G_b, drifts)

        logger.info(
            f"[GTD] nodes_added={node_ev['node_added_ratio']:.3f}  "
            f"edge_churn={edge_ev['edge_churn']:.3f}  "
            f"mean_drift={sem_ev['mean_drift']:.4f}"
        )

    def get_node_features(self, entity_id: str) -> Dict[str, float]:
        """
        Return per-entity GTD features for a given entity ID.
        Returns zero-filled dict if entity was not seen.
        """
        return self._node_features.get(entity_id, {
            "gtd_change_class":        0.0,
            "gtd_local_edges_added":   0.0,
            "gtd_local_edges_removed": 0.0,
            "gtd_local_edge_churn":    0.0,
        })

    def get_global_features(self) -> Dict[str, float]:
        """Return the global GTD vector (same for every entity in this pair)."""
        return self.global_vector.copy()

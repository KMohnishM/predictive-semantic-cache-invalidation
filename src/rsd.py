"""
Repository State Descriptor (RSD)
==================================
Converts each Git commit snapshot into a fixed-length 5-dimensional
numerical tuple:  R(C_i) = (S, T, M, C, E)

  S — Repository Scale Score
  T — Dependency Topology Score
  M — Semantic Organisation Score
  C — Code Complexity Score
  E — Repository Evolution Score

Each score is in [0, 1] after Robust Scaling + Entropy-Weight aggregation.

The RSDs are used to cluster commits (K-Means / GMM) so that the
train / test split is *stratified* rather than a raw time-based
percentage cut.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import networkx as nx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _robust_scale(values: np.ndarray) -> np.ndarray:
    """
    Robust (IQR-based) normalisation.

    x' = (x - median) / IQR

    Clips to [-3, 3] then rescales to [0, 1] to keep everything bounded.
    Handles zero-IQR gracefully.
    """
    if values.ndim == 1:
        values = values.reshape(-1, 1)

    result = np.zeros_like(values, dtype=float)
    for col in range(values.shape[1]):
        col_vals = values[:, col].astype(float)
        median = np.median(col_vals)
        q75, q25 = np.percentile(col_vals, [75, 25])
        iqr = q75 - q25
        if iqr < 1e-9:
            result[:, col] = 0.0
        else:
            scaled = (col_vals - median) / iqr
            clipped = np.clip(scaled, -3, 3)
            result[:, col] = (clipped + 3) / 6.0   # map [-3,3] → [0,1]

    return result.squeeze()


def _entropy_weights(metric_matrix: np.ndarray) -> np.ndarray:
    """
    Entropy Weight Method.

    For each column (metric) compute its information entropy and derive
    a weight that is proportional to 1 - H_i (more informative = higher weight).

    metric_matrix : shape (n_commits, n_metrics), values already in [0,1].
    Returns       : weight vector of length n_metrics summing to 1.
    """
    n, m = metric_matrix.shape
    if n == 1:
        return np.ones(m) / m

    # Normalise columns to probability distributions (add tiny epsilon to avoid log(0))
    eps = 1e-9
    col_sums = metric_matrix.sum(axis=0) + eps
    P = metric_matrix / col_sums[None, :]

    # Entropy per metric
    H = -(P * np.log(P + eps)).sum(axis=0) / math.log(n + eps)
    H = np.clip(H, 0, 1)

    diversity = 1 - H
    total = diversity.sum()
    if total < 1e-9:
        return np.ones(m) / m

    return diversity / total


# ---------------------------------------------------------------------------
# Per-commit metric extractors
# ---------------------------------------------------------------------------

def _scale_metrics(repo_parser) -> Dict[str, float]:
    """Compute raw scale metrics from a parsed repository snapshot."""
    entities = repo_parser.get_all_entities()
    n_entities = len(entities)
    n_classes   = sum(1 for e in entities if e.entity_type == "class")
    n_functions = sum(1 for e in entities if e.entity_type in ("function", "method"))
    total_loc   = sum(len(e.source_code.splitlines()) for e in entities)
    avg_fn_len  = (total_loc / max(n_functions, 1))
    return {
        "n_entities":   float(n_entities),
        "n_classes":    float(n_classes),
        "n_functions":  float(n_functions),
        "total_loc":    float(total_loc),
        "avg_fn_len":   float(avg_fn_len),
    }


def _topology_metrics(repo_parser) -> Dict[str, float]:
    """Compute raw dependency-graph topology metrics."""
    G = repo_parser.get_graph()
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    if n_nodes == 0:
        return {k: 0.0 for k in ("n_nodes", "n_edges", "avg_degree",
                                  "density", "n_components", "avg_clustering",
                                  "avg_pagerank")}

    density = nx.density(G)
    avg_degree = (2 * n_edges / n_nodes) if n_nodes else 0.0
    n_components = nx.number_weakly_connected_components(G)

    UG = G.to_undirected()
    avg_clustering = nx.average_clustering(UG)

    try:
        pagerank = nx.pagerank(G, alpha=0.85)
        avg_pagerank = float(np.mean(list(pagerank.values())))
    except Exception:
        avg_pagerank = 0.0

    return {
        "n_nodes":       float(n_nodes),
        "n_edges":       float(n_edges),
        "avg_degree":    float(avg_degree),
        "density":       float(density),
        "n_components":  float(n_components),
        "avg_clustering":float(avg_clustering),
        "avg_pagerank":  float(avg_pagerank),
    }


def _semantic_metrics(embeddings: Dict[str, np.ndarray]) -> Dict[str, float]:
    """Compute raw semantic metrics from the embedding dictionary."""
    if not embeddings:
        return {k: 0.0 for k in ("avg_sim", "embed_variance", "embed_entropy")}

    emb_matrix = np.stack(list(embeddings.values()), axis=0)  # (N, D)

    # Average pairwise cosine similarity (sample 200 pairs max for speed)
    N = emb_matrix.shape[0]
    rng = np.random.default_rng(42)
    if N > 200:
        idx = rng.choice(N, 200, replace=False)
        sample = emb_matrix[idx]
    else:
        sample = emb_matrix

    norms = np.linalg.norm(sample, axis=1, keepdims=True) + 1e-9
    normed = sample / norms
    sim_matrix = normed @ normed.T
    upper = sim_matrix[np.triu_indices(len(normed), k=1)]
    avg_sim = float(np.mean(upper)) if len(upper) > 0 else 0.0

    # Variance and entropy of embedding magnitudes
    magnitudes = np.linalg.norm(emb_matrix, axis=1)
    embed_variance = float(np.var(magnitudes))

    # Approximate entropy via histogram of magnitudes
    mag_min, mag_max = np.min(magnitudes), np.max(magnitudes)
    if mag_max - mag_min < 1e-9:
        embed_entropy = 0.0
    else:
        hist, _ = np.histogram(magnitudes, bins=20, density=True)
        hist = hist + 1e-9
        hist /= hist.sum()
        embed_entropy = float(-np.sum(hist * np.log(hist)))

    return {
        "avg_sim":        avg_sim,
        "embed_variance": embed_variance,
        "embed_entropy":  embed_entropy,
    }


def _complexity_metrics(repo_parser) -> Dict[str, float]:
    """Approximate code complexity metrics from AST info."""
    entities = repo_parser.get_all_entities()
    G = repo_parser.get_graph()

    fan_ins  = [G.in_degree(e.entity_id)  for e in entities if e.entity_id in G]
    fan_outs = [G.out_degree(e.entity_id) for e in entities if e.entity_id in G]

    avg_fan_in  = float(np.mean(fan_ins))  if fan_ins  else 0.0
    avg_fan_out = float(np.mean(fan_outs)) if fan_outs else 0.0

    # Approximate cyclomatic complexity via source-code line count proxy
    avg_loc = float(np.mean([len(e.source_code.splitlines()) for e in entities])) if entities else 0.0

    # Import diversity: unique import statements across all source files
    import_tokens: set = set()
    for e in entities:
        for line in e.source_code.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_tokens.add(stripped)
    import_diversity = float(len(import_tokens))

    return {
        "avg_fan_in":       avg_fan_in,
        "avg_fan_out":      avg_fan_out,
        "avg_loc":          avg_loc,
        "import_diversity": import_diversity,
    }


def _evolution_metrics(commit_hash: str,
                       modification_history: Dict[str, List[str]],
                       previous_drifts: Dict[str, float],
                       commit_index: int,
                       total_commits: int) -> Dict[str, float]:
    """Compute evolution / history metrics for a commit."""
    if modification_history:
        churn_values = [len(v) for v in modification_history.values()]
        avg_churn = float(np.mean(churn_values))
        mod_freq  = float(np.sum([1 for v in modification_history.values() if commit_hash in v]))
    else:
        avg_churn = 0.0
        mod_freq  = 0.0

    avg_drift = float(np.mean(list(previous_drifts.values()))) if previous_drifts else 0.0
    relative_age = commit_index / max(total_commits - 1, 1)

    return {
        "avg_churn":    avg_churn,
        "mod_freq":     mod_freq,
        "avg_drift":    avg_drift,
        "relative_age": relative_age,
    }


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class RepositoryStateDescriptor:
    """
    Builds and stores Repository State Descriptors (RSDs) for every commit
    in an experiment run, then uses them for stratified train/test splitting.
    """

    # Category dimension names (for logging / display)
    DIMENSIONS = ["Scale", "Topology", "Semantic", "Complexity", "Evolution"]

    def __init__(self):
        # commit_hash -> raw metric dict per category
        self._raw: Dict[str, Dict[str, Dict[str, float]]] = {}
        # commit_hash -> 5D RSD vector
        self.descriptors: Dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_commit(self,
                   commit_hash: str,
                   repo_parser,
                   embeddings: Dict[str, np.ndarray],
                   modification_history: Dict[str, List[str]],
                   previous_drifts: Dict[str, float],
                   commit_index: int,
                   total_commits: int) -> None:
        """
        Record all raw metrics for *one* commit.  Call this for every
        commit immediately after parsing + embedding.  The final RSD
        vectors are computed lazily in `build_all_rsds()`.
        """
        self._raw[commit_hash] = {
            "scale":      _scale_metrics(repo_parser),
            "topology":   _topology_metrics(repo_parser),
            "semantic":   _semantic_metrics(embeddings),
            "complexity": _complexity_metrics(repo_parser),
            "evolution":  _evolution_metrics(
                              commit_hash, modification_history,
                              previous_drifts, commit_index, total_commits),
        }

    def build_all_rsds(self) -> None:
        """
        Compute normalised 5D RSD vectors for all recorded commits.
        Must be called after *all* `add_commit()` calls.
        """
        if not self._raw:
            return

        commit_hashes = list(self._raw.keys())
        n = len(commit_hashes)

        # Build metric matrices per category
        category_scores = {}
        for cat in ("scale", "topology", "semantic", "complexity", "evolution"):
            metric_keys = sorted(next(iter(self._raw.values()))[cat].keys())
            mat = np.array([
                [self._raw[ch][cat][k] for k in metric_keys]
                for ch in commit_hashes
            ], dtype=float)                                # (n, n_metrics)

            if n > 1:
                mat_scaled = _robust_scale(mat)            # (n, n_metrics)
            else:
                mat_scaled = np.zeros_like(mat)

            # Entropy weights
            weights = _entropy_weights(mat_scaled)         # (n_metrics,)
            # Category score = weighted sum → shape (n,)
            scores = mat_scaled @ weights
            category_scores[cat] = scores                  # (n,)

        # Stack → (n, 5), one column per category
        rsd_matrix = np.column_stack([
            category_scores["scale"],
            category_scores["topology"],
            category_scores["semantic"],
            category_scores["complexity"],
            category_scores["evolution"],
        ])                                                  # (n, 5)

        # Clip to [0, 1] (should already be close due to scaling)
        rsd_matrix = np.clip(rsd_matrix, 0, 1)

        for i, ch in enumerate(commit_hashes):
            self.descriptors[ch] = rsd_matrix[i]

        logger.info(f"[RSD] Built descriptors for {n} commits")
        for ch in commit_hashes[:3]:
            logger.debug(f"  {ch[:8]}: {np.round(self.descriptors[ch], 3)}")

    def stratified_split(self,
                         commits: List[str],
                         train_ratio: float = 0.7,
                         n_clusters: int = 3) -> Tuple[List[str], List[str]]:
        """
        Cluster commits by their RSD and do a stratified train / test split.

        Within each cluster, the *earliest* `train_ratio` fraction of commits
        (by position in `commits` list) go to train, the rest to test.
        This preserves temporal ordering while ensuring representativeness.

        Falls back to simple split if sklearn is unavailable or data is tiny.
        """
        if not self.descriptors or len(commits) < 6:
            logger.warning("[RSD] Falling back to simple temporal split (too few commits or no descriptors)")
            split_idx = int(len(commits) * train_ratio)
            return commits[:split_idx], commits[split_idx:]

        try:
            from sklearn.cluster import KMeans

            vectors = np.array([self.descriptors.get(ch, np.zeros(5)) for ch in commits])
            n_clusters = min(n_clusters, len(commits) // 2)
            km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = km.fit_predict(vectors)

            train_commits, test_commits = [], []
            for cluster_id in range(n_clusters):
                cluster_idxs = [i for i, l in enumerate(labels) if l == cluster_id]
                # Sort by original temporal order
                cluster_idxs.sort()
                n_train = max(1, int(len(cluster_idxs) * train_ratio))
                for rank, idx in enumerate(cluster_idxs):
                    if rank < n_train:
                        train_commits.append(commits[idx])
                    else:
                        test_commits.append(commits[idx])

            # Re-sort both lists to preserve temporal order
            commit_order = {ch: i for i, ch in enumerate(commits)}
            train_commits.sort(key=lambda ch: commit_order[ch])
            test_commits.sort(key=lambda ch: commit_order[ch])

            logger.info(
                f"[RSD] Stratified split → train={len(train_commits)}, "
                f"test={len(test_commits)} across {n_clusters} clusters"
            )
            return train_commits, test_commits

        except ImportError:
            logger.warning("[RSD] sklearn not available — falling back to simple split")
            split_idx = int(len(commits) * train_ratio)
            return commits[:split_idx], commits[split_idx:]

    def get_descriptor(self, commit_hash: str) -> Optional[np.ndarray]:
        """Return the 5D RSD vector for a commit, or None if not computed."""
        return self.descriptors.get(commit_hash)

    def summary_table(self) -> str:
        """Return a human-readable table of all commit RSDs."""
        if not self.descriptors:
            return "No RSD descriptors computed yet."
        lines = [f"{'Commit':10s}  {'S':6s}  {'T':6s}  {'M':6s}  {'C':6s}  {'E':6s}"]
        lines.append("-" * 50)
        for ch, vec in self.descriptors.items():
            lines.append(
                f"{ch[:8]:10s}  "
                + "  ".join(f"{v:.4f}" for v in vec)
            )
        return "\n".join(lines)

"""
Benchmark result visualizer.

Generates a suite of charts saved as PNG files into the run output directory.
Called automatically at the end of each benchmark run alongside summary_report.md.

Charts produced:
  1. strategy_comparison.png   — grouped bar chart: freshness, cache pres., update cost per strategy
  2. pareto_frontier.png       — scatter plot of update cost vs freshness rate with Pareto frontier
  3. cosine_similarity.png     — bar chart: mean / min / P95 cosine similarity per strategy
  4. metrics_heatmap.png       — heatmap of all key metrics across strategies
  5. radar_chart.png           — radar / spider chart overlaying all strategies
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Strategy display order and colour palette
_STRATEGY_ORDER = ["changed_only", "fixed_hop", "predictive_ml", "full_reindex"]
_COLOURS = {
    "changed_only":  "#4C72B0",
    "fixed_hop":     "#DD8452",
    "predictive_ml": "#55A868",
    "full_reindex":  "#C44E52",
}
_DEFAULT_COLOUR = "#8172B2"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ordered_strategies(strategy_summaries: Dict[str, Dict]) -> List[str]:
    """Return strategy names in display order, skipping internal keys."""
    real = [k for k in strategy_summaries if not k.startswith("__")]
    ordered = [s for s in _STRATEGY_ORDER if s in real]
    ordered += [s for s in real if s not in ordered]
    return ordered


def _colour(name: str) -> str:
    return _COLOURS.get(name, _DEFAULT_COLOUR)


# ---------------------------------------------------------------------------
# Chart 1: Grouped bar — freshness / cache preservation / update cost
# ---------------------------------------------------------------------------

def _plot_strategy_comparison(
    ax,
    strategies: List[str],
    strategy_summaries: Dict[str, Dict],
) -> None:
    import numpy as np

    metrics = {
        "Freshness Rate":        [strategy_summaries[s].get("freshness_success_rate", 0.0) for s in strategies],
        "Cache Preservation":    [strategy_summaries[s].get("cache_preservation_success_rate", 0.0) for s in strategies],
        "Update Cost (fraction)":[strategy_summaries[s].get("candidate_update_fraction", 0.0) for s in strategies],
    }

    x = np.arange(len(strategies))
    width = 0.22
    offsets = [-1, 0, 1]
    bar_colours = ["#4C9BE8", "#55A868", "#E8884C"]

    for idx, (label, values) in enumerate(metrics.items()):
        bars = ax.bar(
            x + offsets[idx] * width, values, width,
            label=label, color=bar_colours[idx], alpha=0.88, edgecolor="white", linewidth=0.7,
        )
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.012,
                f"{val:.3f}",
                ha="center", va="bottom", fontsize=7.5, fontweight="bold",
            )

    # 95% Wilson CI error bars for Freshness and Cache Preservation (computed in runner.py).
    # Strategies without a CI (older summaries) get no error bar rather than a fake one.
    for idx, (label, ci_key) in enumerate([("Freshness Rate", "freshness_ci_95"),
                                           ("Cache Preservation", "cache_preservation_ci_95")]):
        vals = metrics[label]
        cis = [strategy_summaries[s].get(ci_key) for s in strategies]
        if not all(ci and len(ci) == 2 for ci in cis):
            continue
        yerr_lo = [max(v - ci[0], 0) for v, ci in zip(vals, cis)]
        yerr_hi = [max(ci[1] - v, 0) for v, ci in zip(vals, cis)]
        ax.errorbar(
            x + offsets[idx] * width, vals,
            yerr=[yerr_lo, yerr_hi],
            fmt="none", color="black", capsize=3, linewidth=1.2,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in strategies], fontsize=9)
    ax.set_ylim(0, 1.18)
    ax.set_ylabel("Score / Fraction", fontsize=10)
    ax.set_title("Strategy Comparison: Freshness, Cache Preservation & Update Cost", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8.5, loc="upper right")
    ax.yaxis.grid(True, alpha=0.35)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Chart 2: Pareto frontier scatter
# ---------------------------------------------------------------------------

def _plot_pareto_frontier(
    ax,
    strategies: List[str],
    strategy_summaries: Dict[str, Dict],
    pareto_strategies: List[str],
) -> None:
    import numpy as np

    costs    = [strategy_summaries[s].get("candidate_update_fraction", 0.0) for s in strategies]
    freshness= [strategy_summaries[s].get("freshness_success_rate", 0.0)    for s in strategies]

    for s, cost, fresh in zip(strategies, costs, freshness):
        is_pareto = s in pareto_strategies
        ax.scatter(
            cost, fresh,
            color=_colour(s),
            s=180 if is_pareto else 90,
            marker="*" if is_pareto else "o",
            zorder=3,
            edgecolors="black" if is_pareto else "none",
            linewidths=0.8,
        )
        ax.annotate(
            s.replace("_", "\n"),
            (cost, fresh),
            textcoords="offset points",
            xytext=(8, 4),
            fontsize=8,
            color=_colour(s),
        )

    # Draw Pareto frontier line
    pareto_points = sorted(
        [(strategy_summaries[s].get("candidate_update_fraction", 0.0),
          strategy_summaries[s].get("freshness_success_rate", 0.0))
         for s in pareto_strategies],
        key=lambda p: p[0],
    )
    if len(pareto_points) >= 2:
        px, py = zip(*pareto_points)
        ax.step(px, py, where="post", color="crimson", linewidth=1.6,
                linestyle="--", label="Pareto frontier")
        ax.legend(fontsize=8.5)

    ax.set_xlabel("Update Cost (fraction re-embedded)  ← Lower is better", fontsize=9)
    ax.set_ylabel("Freshness Rate  ↑ Higher is better", fontsize=9)
    ax.set_title("Cost vs. Quality Pareto Frontier", fontsize=11, fontweight="bold")
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.yaxis.grid(True, alpha=0.3)
    ax.xaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Ideal point annotation
    ax.annotate("Ideal →\n(low cost, high freshness)",
                xy=(0, 1), xytext=(0.05, 0.88),
                fontsize=7.5, color="darkgreen",
                arrowprops=dict(arrowstyle="->", color="darkgreen", lw=1))


# ---------------------------------------------------------------------------
# Chart 3: Cosine similarity bars
# ---------------------------------------------------------------------------

def _plot_cosine_similarity(
    ax,
    strategies: List[str],
    embedding_comparisons: List[Any],
) -> None:
    import numpy as np

    comp_by_strategy: Dict[str, Any] = {c.strategy_name: c for c in embedding_comparisons}
    strategies_with_data = [s for s in strategies if s in comp_by_strategy]

    if not strategies_with_data:
        ax.text(0.5, 0.5, "No embedding comparison data available",
                ha="center", va="center", transform=ax.transAxes, fontsize=10, color="gray")
        ax.set_title("Cosine Similarity (Embedding Fidelity)", fontsize=11, fontweight="bold")
        return

    x = np.arange(len(strategies_with_data))
    width = 0.25

    mean_vals = [comp_by_strategy[s].mean_cosine_similarity for s in strategies_with_data]
    min_vals  = [comp_by_strategy[s].min_cosine_similarity  for s in strategies_with_data]
    p95_vals  = [comp_by_strategy[s].p95_cosine_similarity  for s in strategies_with_data]

    ax.bar(x - width, mean_vals, width, label="Mean",  color="#4C9BE8", alpha=0.88, edgecolor="white")
    ax.bar(x,          p95_vals, width, label="P95",   color="#55A868", alpha=0.88, edgecolor="white")
    ax.bar(x + width,  min_vals, width, label="Min",   color="#C44E52", alpha=0.88, edgecolor="white")

    for bars, vals in [(x - width, mean_vals), (x, p95_vals), (x + width, min_vals)]:
        for xi, val in zip(bars, vals):
            ax.text(xi, val + 0.005, f"{val:.3f}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in strategies_with_data], fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Cosine Similarity Score", fontsize=10)
    ax.set_title("Embedding Fidelity: Mean / P95 / Min Cosine Similarity per Strategy", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8.5)
    ax.yaxis.grid(True, alpha=0.35)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Chart 4: Metrics heatmap
# ---------------------------------------------------------------------------

def _plot_metrics_heatmap(ax, strategies: List[str], strategy_summaries: Dict[str, Dict]) -> None:
    import numpy as np

    metric_labels = [
        "Freshness Rate",
        "Cache Preservation",
        "Update Cost",
        "MRR Δ (shifted)",
        "nDCG@10 Δ (shifted)",
    ]

    data = []
    for s in strategies:
        ss = strategy_summaries[s]
        deltas = ss.get("metric_deltas", {})
        row = [
            ss.get("freshness_success_rate", 0.0),
            ss.get("cache_preservation_success_rate", 0.0),
            ss.get("candidate_update_fraction", 0.0),
            deltas.get("mrr", 0.0) + 0.5,        # shift to [0,1] range for colour mapping
            deltas.get("ndcg_at_10", 0.0) + 0.5,
        ]
        data.append(row)

    data_arr = np.array(data)

    im = ax.imshow(data_arr, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(metric_labels)))
    ax.set_xticklabels(metric_labels, fontsize=8.5, rotation=22, ha="right")
    ax.set_yticks(range(len(strategies)))
    ax.set_yticklabels([s.replace("_", "\n") for s in strategies], fontsize=9)

    for i in range(len(strategies)):
        for j in range(len(metric_labels)):
            val = data_arr[i, j]
            display_val = val - 0.5 if j >= 3 else val  # undo shift for display
            ax.text(j, i, f"{display_val:.3f}", ha="center", va="center",
                    fontsize=8, color="black" if 0.3 < val < 0.8 else "white",
                    fontweight="bold")

    import matplotlib.pyplot as plt
    plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="Score (0–1)")
    ax.set_title("Metrics Heatmap — All Strategies × All Dimensions", fontsize=11, fontweight="bold")


# ---------------------------------------------------------------------------
# Chart 5: Radar / spider chart
# ---------------------------------------------------------------------------

def _plot_radar(ax, strategies: List[str], strategy_summaries: Dict[str, Dict]) -> None:
    import numpy as np
    import matplotlib.pyplot as plt

    metric_labels = ["Freshness\nRate", "Cache\nPreservation", "Low\nUpdate Cost",
                     "MRR Δ\n(normalised)", "nDCG@10 Δ\n(normalised)"]
    N = len(metric_labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_labels, fontsize=8.5)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=6.5, color="gray")

    for s in strategies:
        ss = strategy_summaries[s]
        deltas = ss.get("metric_deltas", {})
        # Low update cost = 1 - update_fraction (so lower cost = better radar coverage)
        values = [
            ss.get("freshness_success_rate", 0.0),
            ss.get("cache_preservation_success_rate", 0.0),
            1.0 - ss.get("candidate_update_fraction", 0.0),
            max(0.0, min(1.0, deltas.get("mrr", 0.0) + 0.5)),
            max(0.0, min(1.0, deltas.get("ndcg_at_10", 0.0) + 0.5)),
        ]
        values += values[:1]  # close polygon
        ax.plot(angles, values, "o-", linewidth=1.8, label=s, color=_colour(s), markersize=4)
        ax.fill(angles, values, alpha=0.10, color=_colour(s))

    ax.legend(loc="upper right", bbox_to_anchor=(1.4, 1.15), fontsize=8.5)
    ax.set_title("Strategy Radar Chart\n(larger area = better overall)", fontsize=11,
                 fontweight="bold", pad=18)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_benchmark_charts(
    output_dir: str,
    strategy_summaries: Dict[str, Dict],
    embedding_comparisons: Optional[List[Any]] = None,
    pareto_strategies: Optional[List[str]] = None,
) -> List[Path]:
    """
    Generate all benchmark visualisation charts and save to output_dir.

    Args:
        output_dir:           Directory to write PNG files into (same as summary_report.md).
        strategy_summaries:   strategy_summaries dict from BenchmarkSummary.
        embedding_comparisons: List of StrategyEmbeddingComparisonResult objects (optional).
        pareto_strategies:    List of Pareto-optimal strategy names (optional).

    Returns:
        List of Path objects for each chart file written.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend — safe on all systems
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not installed — benchmark charts will not be generated.")
        return []

    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    real_summaries = {k: v for k, v in strategy_summaries.items() if not k.startswith("__")}
    if not real_summaries:
        logger.warning("No strategy summaries available — skipping chart generation.")
        return []

    strategies = _ordered_strategies(real_summaries)
    pareto = pareto_strategies or []
    emb_comps = embedding_comparisons or []

    written: List[Path] = []

    # ── Chart 1: Strategy comparison bar chart ──────────────────────────────
    try:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        _plot_strategy_comparison(ax, strategies, real_summaries)
        fig.tight_layout()
        p = out / "strategy_comparison.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(p)
        logger.info(f"Chart saved: {p.name}")
    except Exception as e:
        logger.warning(f"strategy_comparison.png failed: {e}")

    # ── Chart 2: Pareto frontier ─────────────────────────────────────────────
    try:
        fig, ax = plt.subplots(figsize=(7, 6))
        _plot_pareto_frontier(ax, strategies, real_summaries, pareto)
        fig.tight_layout()
        p = out / "pareto_frontier.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(p)
        logger.info(f"Chart saved: {p.name}")
    except Exception as e:
        logger.warning(f"pareto_frontier.png failed: {e}")

    # ── Chart 3: Cosine similarity ────────────────────────────────────────────
    try:
        fig, ax = plt.subplots(figsize=(9, 5))
        _plot_cosine_similarity(ax, strategies, emb_comps)
        fig.tight_layout()
        p = out / "cosine_similarity.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(p)
        logger.info(f"Chart saved: {p.name}")
    except Exception as e:
        logger.warning(f"cosine_similarity.png failed: {e}")

    # ── Chart 4: Heatmap ─────────────────────────────────────────────────────
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        _plot_metrics_heatmap(ax, strategies, real_summaries)
        fig.tight_layout()
        p = out / "metrics_heatmap.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(p)
        logger.info(f"Chart saved: {p.name}")
    except Exception as e:
        logger.warning(f"metrics_heatmap.png failed: {e}")

    # ── Chart 5: Radar chart ──────────────────────────────────────────────────
    try:
        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
        _plot_radar(ax, strategies, real_summaries)
        fig.tight_layout()
        p = out / "radar_chart.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(p)
        logger.info(f"Chart saved: {p.name}")
    except Exception as e:
        logger.warning(f"radar_chart.png failed: {e}")

    logger.info(f"Benchmark visualizer: {len(written)}/5 charts written to {out}")
    return written

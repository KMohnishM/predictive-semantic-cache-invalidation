"""Human-readable benchmark reporting."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .types import BenchmarkSummary, StrategyEmbeddingComparisonResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 3.2: Wilson confidence interval helper
# ---------------------------------------------------------------------------

def wilson_ci(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
    """
    95% Wilson confidence interval for a proportion (successes / trials).

    More accurate than the normal approximation for small n or extreme proportions
    (near 0 or 1). Standard in clinical trials and information-retrieval evaluation.

    Args:
        successes: Count of positive outcomes (e.g. freshness_pass queries)
        trials:    Total number of queries evaluated for this strategy
        z:         Critical value — 1.96 for 95% CI

    Returns:
        (lower_bound, upper_bound) both clipped to [0.0, 1.0]
    """
    if trials == 0:
        return 0.0, 0.0
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


# ---------------------------------------------------------------------------
# Phase 1.4: Benchmark saturation guard
# ---------------------------------------------------------------------------

def check_and_warn_saturation(
    strategy_summaries: Dict[str, Dict],
    discrimination_threshold: float = 0.05,
) -> bool:
    """
    Detect benchmark saturation: all strategies produce indistinguishable
    retrieval metrics despite differing update costs.

    Saturation criteria:
        - freshness_success_rate spread < discrimination_threshold  AND
        - cache_preservation_success_rate spread < discrimination_threshold  AND
        - candidate_update_fraction spread > 0.10  (strategies DO differ in cost)

    When saturated the benchmark cannot distinguish between invalidation strategies
    and reported numbers should not be used for comparison.

    Root cause when saturated: query text contains the target entity name, making
    retrieval an identity match regardless of embedding freshness. See query_sources.py.

    Literature:
        Thakur et al., BEIR (NeurIPS 2021) — documents how in-distribution /
        self-generated evaluation consistently overstates real retrieval quality.

    Returns:
        True if benchmark is saturated (also logs a prominent WARNING).
    """
    real_summaries = {k: v for k, v in strategy_summaries.items() if not k.startswith("__")}
    if len(real_summaries) < 2:
        return False  # Cannot detect saturation with only one strategy

    freshness_vals = [s.get("freshness_success_rate", 0.0)          for s in real_summaries.values()]
    cache_vals     = [s.get("cache_preservation_success_rate", 0.0) for s in real_summaries.values()]
    update_vals    = [s.get("candidate_update_fraction", 0.0)        for s in real_summaries.values()]

    freshness_spread = max(freshness_vals) - min(freshness_vals)
    cache_spread     = max(cache_vals)     - min(cache_vals)
    update_spread    = max(update_vals)    - min(update_vals)

    is_saturated = (
        freshness_spread < discrimination_threshold
        and cache_spread < discrimination_threshold
        and update_spread > 0.10
    )

    if is_saturated:
        logger.warning("=" * 70)
        logger.warning("BENCHMARK SATURATION DETECTED — RESULTS ARE UNRELIABLE")
        logger.warning(f"  Freshness rate spread:          {freshness_spread:.4f}  (need > {discrimination_threshold})")
        logger.warning(f"  Cache preservation rate spread: {cache_spread:.4f}  (need > {discrimination_threshold})")
        logger.warning(f"  Update fraction spread:         {update_spread:.4f}  (strategies DO differ in cost)")
        logger.warning("  All strategies produce indistinguishable retrieval metrics.")
        logger.warning("  Most likely cause: query text contains target entity name.")
        logger.warning("  Fix: run with --query-mode=curated or verify query_sources.py fix")
        logger.warning("=" * 70)

    return is_saturated


# ---------------------------------------------------------------------------
# Phase 4.1: Pareto frontier
# ---------------------------------------------------------------------------

def compute_pareto_frontier(strategy_summaries: Dict[str, Dict]) -> List[str]:
    """
    Return strategy names on the Pareto frontier of the cost-quality tradeoff.

    Axes:
        x: candidate_update_fraction  — LOWER is better (fewer re-embeddings = lower cost)
        y: freshness_success_rate     — HIGHER is better (more retrieval results are fresh)

    A strategy S1 is Pareto-dominated by S2 if:
        S2 costs <= S1 on update fraction  AND
        S2 is >= S1 on freshness rate      AND
        S2 is strictly better on at least one axis

    Non-dominated strategies form the Pareto frontier.
    Strategies on the frontier represent the best achievable cost-quality tradeoffs —
    no other strategy is simultaneously cheaper and fresher.

    Literature:
        Dang, Chen, Wu, Liu — CacheSense (IEEE CAIBDA 2026).
        Directly comparable prior work framing selective invalidation as a cost-quality
        Pareto problem. Standard framing for this problem class.
    """
    real_summaries = {k: v for k, v in strategy_summaries.items() if not k.startswith("__")}

    points = [
        (name, s.get("candidate_update_fraction", 1.0), s.get("freshness_success_rate", 0.0))
        for name, s in real_summaries.items()
    ]

    dominated: set = set()
    for i, (n1, cost1, qual1) in enumerate(points):
        for j, (n2, cost2, qual2) in enumerate(points):
            if i == j:
                continue
            # n1 is dominated by n2 if n2 is cheaper-or-equal AND fresher-or-equal,
            # and strictly better on at least one axis
            if cost2 <= cost1 and qual2 >= qual1 and (cost2 < cost1 or qual2 > qual1):
                dominated.add(n1)
                break

    return [n for n, _, _ in points if n not in dominated]


# ---------------------------------------------------------------------------
# Phase 3.3: Multi-seed aggregation
# ---------------------------------------------------------------------------

def aggregate_multi_run_results(
    all_run_strategy_summaries: List[Dict[str, Dict]],
) -> Dict[str, Dict]:
    """
    Aggregate strategy metrics across multiple independent benchmark runs (seeds).

    Args:
        all_run_strategy_summaries: List of strategy_summaries dicts, one per seed run.

    Returns:
        {strategy_name: {metric_name: {"mean": float, "std": float, "n_runs": int}}}
    """
    from collections import defaultdict

    aggregated: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    for run_summaries in all_run_strategy_summaries:
        for strategy_name, stats in run_summaries.items():
            if strategy_name.startswith("__"):
                continue
            aggregated[strategy_name]["freshness_success_rate"].append(
                stats.get("freshness_success_rate", 0.0))
            aggregated[strategy_name]["cache_preservation_success_rate"].append(
                stats.get("cache_preservation_success_rate", 0.0))
            aggregated[strategy_name]["candidate_update_fraction"].append(
                stats.get("candidate_update_fraction", 0.0))
            aggregated[strategy_name]["mrr_delta"].append(
                stats.get("metric_deltas", {}).get("mrr", 0.0))
            aggregated[strategy_name]["ndcg_at_10_delta"].append(
                stats.get("metric_deltas", {}).get("ndcg_at_10", 0.0))

    result: Dict[str, Dict] = {}
    for strategy_name, metrics_lists in aggregated.items():
        result[strategy_name] = {}
        for metric_name, values in metrics_lists.items():
            n = len(values)
            mean_val = sum(values) / n if n else 0.0
            variance = sum((v - mean_val) ** 2 for v in values) / max(n - 1, 1)
            result[strategy_name][metric_name] = {
                "mean":   round(mean_val, 4),
                "std":    round(variance ** 0.5, 4),
                "n_runs": n,
            }

    return result


def write_aggregated_report(
    output_path: str,
    aggregated: Dict[str, Dict],
    n_seeds: int,
) -> Path:
    """Write multi-run aggregated summary with mean ± std per metric."""
    lines = [
        "# Aggregated Benchmark Report",
        "",
        f"Aggregated over **{n_seeds} independent seeds**.",
        "",
        "| Strategy | Freshness (mean ± std) | Cache Pres. (mean ± std) | Update Cost (mean ± std) | MRR Δ (mean ± std) |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    def fmt(d: Dict) -> str:
        return f"{d.get('mean', 0.0):.3f} ± {d.get('std', 0.0):.3f}"

    for strategy_name, metrics in aggregated.items():
        lines.append(
            f"| `{strategy_name}` "
            f"| {fmt(metrics.get('freshness_success_rate', {}))} "
            f"| {fmt(metrics.get('cache_preservation_success_rate', {}))} "
            f"| {fmt(metrics.get('candidate_update_fraction', {}))} "
            f"| {fmt(metrics.get('mrr_delta', {}))} |"
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Main report writer
# ---------------------------------------------------------------------------

def write_summary_report(
    output_dir: str,
    summary: BenchmarkSummary,
    embedding_comparisons: Optional[Iterable[StrategyEmbeddingComparisonResult]] = None,
) -> Path:
    output_path = Path(output_dir).resolve() / "summary_report.md"
    lines = [
        "# Benchmark Summary",
        "",
        f"- Run ID: {summary.run_id}",
        f"- Total queries: {summary.total_queries}",
        f"- Changed queries: {summary.changed_query_count}",
        f"- Unchanged queries: {summary.unchanged_query_count}",
    ]

    # Phase 1.4: render saturation warning prominently if detected
    if getattr(summary, "saturation_warning", False):
        lines.extend([
            "",
            "> [!CAUTION]",
            "> **BENCHMARK SATURATED** — Retrieval metrics are indistinguishable across strategies.",
            "> Results in this report should not be used for strategy comparison.",
            "> Cause: query text contains the target entity name (identity leak).",
            "> Fix: switch to `--query-mode=curated` or verify the Phase 1.1 fix in `query_sources.py`.",
        ])

    # Phase 3.2: strategy table with Wilson CIs — no "Passed" column
    lines.extend([
        "",
        "## Strategy Performance Comparison",
        "",
        "| Strategy | Update Cost | Freshness [95% CI] (n) | Cache Pres. [95% CI] (n) | MRR Δ | nDCG@10 Δ |",
        "| :--- | :---: | :--- | :--- | :---: | :---: |",
    ])

    if getattr(summary, "strategy_summaries", None):
        for name, stats in summary.strategy_summaries.items():
            if name.startswith("__"):
                continue  # skip meta keys like __saturation_warning__

            n_total     = stats.get("total_queries", 0)
            n_fresh     = stats.get("freshness_successes", 0)
            n_cache     = stats.get("cache_successes", 0)
            fresh_rate  = stats.get("freshness_success_rate", 0.0)
            cache_rate  = stats.get("cache_preservation_success_rate", 0.0)
            update_frac = stats.get("candidate_update_fraction", 0.0)
            deltas      = stats.get("metric_deltas", {})
            mrr_delta   = deltas.get("mrr", 0.0)
            ndcg_delta  = deltas.get("ndcg_at_10", 0.0)

            # Compute Wilson CIs from raw success counts
            fresh_lo, fresh_hi = wilson_ci(n_fresh, n_total)
            cache_lo,  cache_hi = wilson_ci(n_cache,  n_total)

            fresh_str = (
                f"{fresh_rate:.3f} [{fresh_lo:.3f}–{fresh_hi:.3f}] (n={n_total})"
                if n_total > 0 else "n/a"
            )
            cache_str = (
                f"{cache_rate:.3f} [{cache_lo:.3f}–{cache_hi:.3f}] (n={n_total})"
                if n_total > 0 else "n/a"
            )

            lines.append(
                f"| `{name}` | {update_frac:.4f} | {fresh_str} | {cache_str} | "
                f"{mrr_delta:+.4f} | {ndcg_delta:+.4f} |"
            )
    else:
        # Backward-compat: flat summary (single strategy, no strategy_summaries dict)
        n_total = summary.total_queries
        fresh_rate = summary.freshness_success_rate
        cache_rate = summary.cache_preservation_success_rate
        mrr_delta  = summary.metric_deltas.get("mrr", 0.0)
        ndcg_delta = summary.metric_deltas.get("ndcg_at_10", 0.0)
        lines.append(
            f"| `selective` | {summary.candidate_update_fraction:.4f} | "
            f"{fresh_rate:.3f} (n={n_total}) | "
            f"{cache_rate:.3f} (n={n_total}) | "
            f"{mrr_delta:+.4f} | {ndcg_delta:+.4f} |"
        )

    # Phase 4.1: Pareto frontier section
    if getattr(summary, "strategy_summaries", None):
        real_summaries = {k: v for k, v in summary.strategy_summaries.items()
                          if not k.startswith("__")}
        if len(real_summaries) >= 2:
            pareto_frontier = compute_pareto_frontier(real_summaries)

            lines.extend([
                "",
                "## Cost vs. Quality Pareto Frontier",
                "",
                "A strategy is **Pareto-optimal** if no other strategy is simultaneously "
                "cheaper (lower update cost) and fresher (higher freshness rate). "
                "Strategies on the frontier represent the best achievable tradeoffs.",
                "",
                "**Pareto-optimal strategies:** "
                + (", ".join(f"`{s}`" for s in pareto_frontier) if pareto_frontier else "none"),
                "",
                "| Strategy | Update Cost ↓ | Freshness Rate ↑ | Pareto-Optimal |",
                "| :--- | :---: | :---: | :---: |",
            ])

            for name, stats in sorted(real_summaries.items(),
                                      key=lambda x: x[1].get("candidate_update_fraction", 1.0)):
                is_optimal = "✅ Yes" if name in pareto_frontier else "❌ No"
                cost  = stats.get("candidate_update_fraction", 0.0)
                fresh = stats.get("freshness_success_rate", 0.0)
                lines.append(f"| `{name}` | {cost:.4f} | {fresh:.4f} | {is_optimal} |")

    # Embedding quality section (unchanged)
    embedding_comparisons_list = list(embedding_comparisons) if embedding_comparisons else []
    if embedding_comparisons_list:
        lines.extend([
            "",
            "## Direct Embedding Quality & Vector Fidelity",
            "",
            "| Strategy | Updated Fraction (Cost) | Mean Cosine Sim (Fidelity) | Min Cosine Sim | P95 Cosine Sim | Total Entities |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for comp in embedding_comparisons_list:
            lines.append(
                f"| `{comp.strategy_name}` | {comp.updated_fraction:.4f} | "
                f"{comp.mean_cosine_similarity:.4f} | {comp.min_cosine_similarity:.4f} | "
                f"{comp.p95_cosine_similarity:.4f} | {comp.total_entities} |"
            )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

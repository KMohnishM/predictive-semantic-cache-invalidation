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
# Staleness-cost accessors (summaries written before the staleness block fall
# back to the absolute freshness rate)
# ---------------------------------------------------------------------------

def primary_at_k(stats: Dict[str, Any]) -> Dict[str, Any]:
    """The primary-k entry of a strategy summary's staleness block ({} if absent)."""
    staleness = stats.get("staleness") or {}
    return staleness.get("at_k", {}).get(str(staleness.get("primary_k")), {})


def quality_score(stats: Dict[str, Any]) -> float:
    """Quality axis for cost/quality comparisons: retention@primary_k (share of the
    full re-index's top-k hits the strategy keeps), else the absolute freshness rate."""
    entry = primary_at_k(stats)
    if entry:
        return float(entry.get("retention", 1.0))
    return float(stats.get("freshness_success_rate", 0.0))


def quality_label(strategy_summaries: Dict[str, Dict]) -> str:
    """Axis / column label matching quality_score() for these summaries."""
    for name, stats in strategy_summaries.items():
        if not name.startswith("__") and primary_at_k(stats):
            return f"Retention@{stats['staleness']['primary_k']}"
    return "Freshness Rate"


# ---------------------------------------------------------------------------
# Phase 1.4: Benchmark saturation guard
# ---------------------------------------------------------------------------

def check_and_warn_saturation(
    strategy_summaries: Dict[str, Dict],
    discrimination_threshold: float = 0.05,
    min_effect: float = 0.001,
) -> bool:
    """
    Detect benchmark saturation: strategies differ in update cost but staleness
    has no measurable retrieval cost, so they cannot be ranked on quality.

    With staleness metrics (see staleness_metrics.py), saturated means:
        - candidate_update_fraction spread > 0.10  (strategies DO differ in cost)  AND
        - no strategy has a statistically measurable loss at any k: the lower
          bound of the 95% Wilson interval of loss_rate@k is <= min_effect
          (default 0.1%) for every strategy and every k.

    A fixed tolerance on the point estimate would call a significant 0.4% loss
    "saturated" while a large-n run is perfectly able to separate the strategies;
    the confidence bound scales with the number of queries instead. Stale gains
    are not quality and are ignored here.

    Summaries without staleness metrics fall back to the old absolute rule
    (freshness and cache-preservation rate spreads < discrimination_threshold).

    Returns:
        True if benchmark is saturated (also logs a prominent WARNING).
    """
    real_summaries = {k: v for k, v in strategy_summaries.items() if not k.startswith("__")}
    if len(real_summaries) < 2:
        return False  # Cannot detect saturation with only one strategy

    update_vals   = [s.get("candidate_update_fraction", 0.0) for s in real_summaries.values()]
    update_spread = max(update_vals) - min(update_vals)

    if all(s.get("staleness") for s in real_summaries.values()):
        strongest = (None, None, 0.0, 0.0)  # (strategy, k, CI lower bound, loss rate)
        for name, stats in real_summaries.items():
            for k, entry in stats["staleness"].get("at_k", {}).items():
                lower = (entry.get("loss_rate_ci_95") or [0.0, 0.0])[0]
                if lower > strongest[2]:
                    strongest = (name, k, lower, entry.get("loss_rate", 0.0))
        name, k, lower, rate = strongest
        is_saturated = update_spread > 0.10 and lower <= min_effect
        if is_saturated:
            logger.warning("=" * 70)
            logger.warning("BENCHMARK SATURATED — STALENESS HAS NO MEASURABLE RETRIEVAL COST")
            logger.warning(f"  Update fraction spread: {update_spread:.4f} (strategies DO differ in cost)")
            logger.warning(
                f"  Strongest loss vs full re-index: {rate:.4%} ({name or '-'}, k={k or '-'}), "
                f"95% CI lower bound {lower:.4%} <= {min_effect:.2%}"
            )
            logger.warning("  No strategy loses a measurable share of the full re-index's hits at any k,")
            logger.warning("  so they can only be compared on cost. Likely cause: re-embedding changes few")
            logger.warning("  vectors beyond the entities whose own source changed (thin call-graph")
            logger.warning("  context), or the queries rarely target the entities that did change.")
            logger.warning("=" * 70)
        return is_saturated

    freshness_vals = [s.get("freshness_success_rate", 0.0)          for s in real_summaries.values()]
    cache_vals     = [s.get("cache_preservation_success_rate", 0.0) for s in real_summaries.values()]

    freshness_spread = max(freshness_vals) - min(freshness_vals)
    cache_spread     = max(cache_vals)     - min(cache_vals)

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
        y: quality_score()            — HIGHER is better: retention@primary_k (share of the
           full re-index's top-k hits kept), or the freshness rate for older summaries

    A strategy S1 is Pareto-dominated by S2 if:
        S2 costs <= S1 on update fraction  AND
        S2 is >= S1 on quality             AND
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
        (name, s.get("candidate_update_fraction", 1.0), quality_score(s))
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
            entry = primary_at_k(stats)
            if entry:
                aggregated[strategy_name]["loss_rate_primary_k"].append(entry.get("loss_rate", 0.0))
                aggregated[strategy_name]["gain_rate_primary_k"].append(entry.get("gain_rate", 0.0))

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
        f"Aggregated over **{n_seeds} disjoint commit windows** (each run ends further back in history).",
        "",
        "Loss / gain rates are at the primary k, relative to a full re-index of the same window "
        "(see staleness_metrics.py); stale gains are not credited.",
        "",
        "| Strategy | Update Cost (mean ± std) | Loss rate (mean ± std) | Stale-gain rate (mean ± std) "
        "| Freshness (mean ± std) | Cache Pres. (mean ± std) | MRR Δ (mean ± std) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    def fmt(d: Dict) -> str:
        """Format mean and standard deviation dictionary into markdown string."""
        return f"{d.get('mean', 0.0):.3f} ± {d.get('std', 0.0):.3f}"

    for strategy_name, metrics in aggregated.items():
        lines.append(
            f"| `{strategy_name}` "
            f"| {fmt(metrics.get('candidate_update_fraction', {}))} "
            f"| {fmt(metrics.get('loss_rate_primary_k', {}))} "
            f"| {fmt(metrics.get('gain_rate_primary_k', {}))} "
            f"| {fmt(metrics.get('freshness_success_rate', {}))} "
            f"| {fmt(metrics.get('cache_preservation_success_rate', {}))} "
            f"| {fmt(metrics.get('mrr_delta', {}))} |"
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Main report writer
# ---------------------------------------------------------------------------

def _append_staleness_section(lines: List[str], strategy_summaries: Dict[str, Dict]) -> None:
    """Staleness cost vs. a full re-index (staleness_metrics.py), per strategy and k."""
    real = {k: v for k, v in strategy_summaries.items() if not k.startswith("__") and v.get("staleness")}
    if not real:
        return
    first = next(iter(real.values()))["staleness"]
    k_values = list(first.get("at_k", {}).keys())
    primary_k = first.get("primary_k")

    lines.extend([
        "",
        "## Staleness Cost vs. Full Re-index",
        "",
        f"For each query the target's rank in the strategy's index is compared with its rank in a "
        f"full re-index of the same commit. **Lost@k**: the full re-index has the target in the "
        f"top-k and the strategy does not (rate = lost / full-re-index hits, 95% Wilson CI). "
        f"**Stale gains@k**: the reverse — a stale vector beating the fresh one; reported, never "
        f"credited. Primary k = {primary_k}. *Stale-target* queries are those whose target's vector "
        f"in the strategy's index differs from the full re-index.",
        "",
        "| Strategy | Update Cost | "
        + " | ".join(f"Lost@{k}" for k in k_values)
        + f" | Stale gains@{primary_k} | Rank degraded | Stale-target queries | Lost@{primary_k} (stale-target) |",
        "| :--- | :---: | " + " | ".join(":---:" for _ in k_values) + " | :---: | :---: | :---: | :---: |",
    ])
    for name, stats in real.items():
        st = stats["staleness"]
        cells = []
        for k in k_values:
            e = st["at_k"][k]
            ci = e.get("loss_rate_ci_95", [0.0, 0.0])
            cells.append(f"{e['lost']}/{e['reference_hits']} = {e['loss_rate']:.2%} [{ci[0]:.2%}, {ci[1]:.2%}]")
        prim = st["at_k"].get(str(primary_k), {})
        sub = st.get("stale_target", {})
        sub_prim = sub.get("at_k", {}).get(str(primary_k), {})
        sub_cell = (
            f"{sub_prim['lost']}/{sub_prim['reference_hits']} = {sub_prim['loss_rate']:.2%}"
            if sub_prim else "–"
        )
        lines.append(
            f"| `{name}` | {stats.get('candidate_update_fraction', 0.0):.4f} | "
            + " | ".join(cells)
            + f" | {prim.get('gained', 0)} | {st.get('rank_degraded_rate', 0.0):.2%} "
            f"| {sub.get('n_queries', 0)} / {st.get('n_queries', 0)} | {sub_cell} |"
        )


def write_summary_report(
    output_dir: str,
    summary: BenchmarkSummary,
    embedding_comparisons: Optional[Iterable[StrategyEmbeddingComparisonResult]] = None,
) -> Path:
    """Write markdown summary report for benchmark execution.

    Args:
        output_dir: Directory where report will be saved.
        summary: BenchmarkSummary data object.
        embedding_comparisons: Optional iterable of embedding comparison results.

    Returns:
        Path object pointing to summary_report.md.
    """
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
            "> **BENCHMARK SATURATED** — strategies differ in update cost, but none of them loses a",
            "> measurable share (95% CI lower bound > 0.1%) of a full re-index's hits at any k. They can only be",
            "> compared on cost. Likely causes: re-embedding changes few vectors beyond the entities",
            "> whose own source changed, or the queries rarely target the entities that did change.",
        ])

    if getattr(summary, "strategy_summaries", None):
        _append_staleness_section(lines, summary.strategy_summaries)

    # Phase 3.2: strategy table with Wilson CIs — no "Passed" column
    lines.extend([
        "",
        "## Absolute Retrieval Quality",
        "",
        "Hit rates in the strategy's own index. These are dominated by the embedding model's "
        "retrieval quality (a full re-index scores the same way), so compare strategies on the "
        "staleness cost above, not on these.",
        "",
        "| Strategy | Update Cost | Freshness [95% CI] ($N_{\\text{changed}}$) | Cache Pres. [95% CI] ($N_{\\text{unchanged}}$) | Relative Baseline Agreement | nDCG Ratio |",
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
            rel_fresh   = stats.get("relative_freshness_rate", 1.0)
            ndcg_ratio  = stats.get("ndcg_ratio", 1.0)
            update_frac = stats.get("candidate_update_fraction", 0.0)

            n_changed   = stats.get("changed_queries", n_total)
            n_unchanged = stats.get("unchanged_queries", n_total)
            fresh_ci = stats.get("freshness_ci_95") or wilson_ci(n_fresh, n_changed)
            cache_ci = stats.get("cache_preservation_ci_95") or wilson_ci(n_cache, n_unchanged)

            lines.append(
                f"| `{name}` | {update_frac:.4f} | "
                f"{fresh_rate:.3f} [{fresh_ci[0]:.3f}, {fresh_ci[1]:.3f}] (n={n_changed}) | "
                f"{cache_rate:.3f} [{cache_ci[0]:.3f}, {cache_ci[1]:.3f}] (n={n_unchanged}) | "
                f"**{rel_fresh:.4f}** | **{ndcg_ratio:.4f}** |"
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
            q_label = quality_label(real_summaries)

            lines.extend([
                "",
                "## Cost vs. Quality Pareto Frontier",
                "",
                "A strategy is **Pareto-optimal** if no other strategy is simultaneously "
                f"cheaper (lower update cost) and better on quality ({q_label}). "
                "Strategies on the frontier represent the best achievable tradeoffs.",
                "",
                "**Pareto-optimal strategies:** "
                + (", ".join(f"`{s}`" for s in pareto_frontier) if pareto_frontier else "none"),
                "",
                f"| Strategy | Update Cost ↓ | {q_label} ↑ | Pareto-Optimal |",
                "| :--- | :---: | :---: | :---: |",
            ])

            for name, stats in sorted(real_summaries.items(),
                                      key=lambda x: x[1].get("candidate_update_fraction", 1.0)):
                is_optimal = "✅ Yes" if name in pareto_frontier else "❌ No"
                cost  = stats.get("candidate_update_fraction", 0.0)
                lines.append(f"| `{name}` | {cost:.4f} | {quality_score(stats):.4f} | {is_optimal} |")

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

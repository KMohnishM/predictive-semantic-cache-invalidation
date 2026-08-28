"""Human-readable benchmark reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .types import BenchmarkSummary


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
        "",
        "## Strategy Performance Comparison",
        "",
        "| Strategy | Update Cost (Fraction) | Freshness Success Rate | Cache Preservation Rate | MRR Delta | nDCG@10 Delta | Passed |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    if hasattr(summary, "strategy_summaries") and summary.strategy_summaries:
        for name, stats in summary.strategy_summaries.items():
            deltas = stats.get("metric_deltas", {})
            mrr_delta = deltas.get("mrr", 0.0)
            ndcg_delta = deltas.get("ndcg_at_10", 0.0)
            lines.append(
                f"| `{name}` | {stats.get('candidate_update_fraction', 0.0):.4f} | "
                f"{stats.get('freshness_success_rate', 0.0):.4f} | "
                f"{stats.get('cache_preservation_success_rate', 0.0):.4f} | "
                f"{mrr_delta:+.4f} | {ndcg_delta:+.4f} | {stats.get('benchmark_passed', False)} |"
            )
    else:
        mrr_delta = summary.metric_deltas.get("mrr", 0.0)
        ndcg_delta = summary.metric_deltas.get("ndcg_at_10", 0.0)
        lines.append(
            f"| `selective` | {summary.candidate_update_fraction:.4f} | "
            f"{summary.freshness_success_rate:.4f} | "
            f"{summary.cache_preservation_success_rate:.4f} | "
            f"{mrr_delta:+.4f} | {ndcg_delta:+.4f} | {summary.benchmark_passed} |"
        )

    if embedding_comparisons:
        lines.extend([
            "",
            "## Direct Embedding Quality & Vector Fidelity",
            "",
            "| Strategy | Updated Fraction (Cost) | Mean Cosine Sim (Fidelity) | Min Cosine Sim | P95 Cosine Sim | Total Entities |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for comp in embedding_comparisons:
            lines.append(
                f"| `{comp.strategy_name}` | {comp.updated_fraction:.4f} | {comp.mean_cosine_similarity:.4f} | {comp.min_cosine_similarity:.4f} | {comp.p95_cosine_similarity:.4f} | {comp.total_entities} |"
            )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


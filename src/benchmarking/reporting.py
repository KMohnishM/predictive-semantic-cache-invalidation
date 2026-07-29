"""Human-readable benchmark reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.benchmarking.types import BenchmarkSummary


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
        f"- Freshness success rate: {summary.freshness_success_rate:.4f}",
        f"- Cache preservation success rate: {summary.cache_preservation_success_rate:.4f}",
        f"- Candidate update fraction: {summary.candidate_update_fraction:.4f}",
        f"- Benchmark passed: {summary.benchmark_passed}",
        "",
        "## Metric Deltas",
    ]
    for key, value in summary.metric_deltas.items():
        lines.append(f"- {key}: {value:.4f}")

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


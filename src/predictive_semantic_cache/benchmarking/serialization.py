"""Serialization helpers for benchmark artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .types import BenchmarkConfig, BenchmarkSummary, CommitPair, PerQueryResult, QueryCase


def ensure_output_dir(path: str) -> Path:
    """Ensure directory exists at specified path string and return resolved Path object.

    Args:
        path: Path string.

    Returns:
        Resolved Path object.
    """
    output_dir = Path(path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: object) -> None:
    """Serialize payload object to JSON file at path.

    Args:
        path: Path object.
        payload: JSON-serializable object.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    """Serialize dictionary rows to JSON Lines file at path.

    Args:
        path: Path object.
        rows: Iterable of dictionary rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def persist_run(
    output_dir: str,
    config: BenchmarkConfig,
    commit_pairs: Iterable[CommitPair],
    queries: Iterable[QueryCase],
    results: Iterable[PerQueryResult],
    summary: BenchmarkSummary,
    embedding_comparisons: Optional[Iterable[StrategyEmbeddingComparisonResult]] = None,
) -> Path:
    """Persist all benchmark run artifacts (config, commit pairs, queries, results, summary) to output directory.

    Args:
        output_dir: Destination directory path.
        config: BenchmarkConfig object.
        commit_pairs: Iterable of CommitPair objects.
        queries: Iterable of QueryCase objects.
        results: Iterable of PerQueryResult objects.
        summary: BenchmarkSummary object.
        embedding_comparisons: Optional iterable of embedding comparison objects.

    Returns:
        Resolved output directory Path object.
    """
    run_dir = ensure_output_dir(output_dir)
    write_json(run_dir / "benchmark_config.json", config.to_dict())
    write_json(run_dir / "commit_pairs.json", [item.to_dict() for item in commit_pairs])
    write_json(run_dir / "queries.json", [item.to_dict() for item in queries])
    write_jsonl(run_dir / "per_query_results.jsonl", [item.to_dict() for item in results])
    write_json(run_dir / "summary_metrics.json", summary.to_dict())

    if embedding_comparisons:
        write_json(
            run_dir / "embedding_comparisons.json",
            [comp.to_dict() for comp in embedding_comparisons],
        )

    return run_dir


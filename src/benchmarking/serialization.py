"""Serialization helpers for benchmark artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from benchmarking.types import BenchmarkConfig, BenchmarkSummary, CommitPair, PerQueryResult, QueryCase


def ensure_output_dir(path: str) -> Path:
    output_dir = Path(path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
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
) -> Path:
    run_dir = ensure_output_dir(output_dir)
    write_json(run_dir / "benchmark_config.json", config.to_dict())
    write_json(run_dir / "commit_pairs.json", [item.to_dict() for item in commit_pairs])
    write_json(run_dir / "queries.json", [item.to_dict() for item in queries])
    write_jsonl(run_dir / "per_query_results.jsonl", [item.to_dict() for item in results])
    write_json(run_dir / "summary_metrics.json", summary.to_dict())
    return run_dir

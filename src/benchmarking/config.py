"""Benchmark configuration helpers."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Optional

from benchmarking.types import BenchmarkConfig


DEFAULT_REPO_URL = "https://github.com/psf/black.git"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the retrieval benchmark pipeline")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--repo-path", default="workspace/black")
    parser.add_argument("--output-dir", default="benchmark_runs")
    parser.add_argument("--benchmark-version", default="1.0")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--num-commits", type=int, default=10)
    parser.add_argument("--commit-stride", type=int, default=1)
    parser.add_argument("--sampling-mode", choices=["adjacent", "stride", "manual"], default="adjacent")
    parser.add_argument("--query-mode", choices=["synthetic", "curated", "hybrid"], default="synthetic")
    parser.add_argument("--curated-queries-path", default=None)
    parser.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--clean-mode", action="store_true")
    parser.add_argument("--top-k-values", default="1,5,10")
    parser.add_argument("--max-queries-per-entity", type=int, default=2)
    return parser


def parse_top_k_values(raw_value: str) -> list[int]:
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return sorted({int(value) for value in values})


def build_config(args: argparse.Namespace) -> BenchmarkConfig:
    repo_path = str(Path(args.repo_path).resolve())
    output_dir = str(Path(args.output_dir).resolve())
    return BenchmarkConfig(
        repo_url=args.repo_url,
        repo_path=repo_path,
        output_dir=output_dir,
        benchmark_version=args.benchmark_version,
        seed=args.seed,
        num_commits=args.num_commits,
        commit_stride=args.commit_stride,
        sampling_mode=args.sampling_mode,
        query_mode=args.query_mode,
        curated_queries_path=args.curated_queries_path,
        model_name=args.model_name,
        clean_mode=args.clean_mode,
        top_k_values=parse_top_k_values(args.top_k_values),
        max_queries_per_entity=args.max_queries_per_entity,
    )


def load_config(argv: Optional[list[str]] = None) -> BenchmarkConfig:
    parser = build_parser()
    args = parser.parse_args(argv)
    return build_config(args)

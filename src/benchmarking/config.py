"""Benchmark configuration helpers."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Optional

from src.benchmarking.types import BenchmarkConfig


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
    parser.add_argument("--strategies", default="changed_only", help="Comma-separated list of candidate invalidation strategies")
    parser.add_argument("--compare-embeddings", action="store_true", default=True, help="Perform direct vector embedding similarity comparison")
    parser.add_argument("--no-compare-embeddings", action="store_false", dest="compare_embeddings")
    parser.add_argument("--store-raw-vectors", action="store_true", default=True, help="Include raw full float vectors in comparison output")
    parser.add_argument("--no-store-raw-vectors", action="store_false", dest="store_raw_vectors")
    parser.add_argument("--config", default=None, help="Path to JSON configuration file to load options from")
    parser.add_argument("--parser-mode", choices=["tree_sitter", "ast"], default="tree_sitter", help="Repository parser mode")
    parser.add_argument("--predictions-path", default=None, help="Path to JSON file containing precomputed ML predictions mapping entity_id to boolean")
    return parser


def parse_top_k_values(raw_value: str) -> list[int]:
    if isinstance(raw_value, list):
        return sorted({int(value) for value in raw_value})
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return sorted({int(value) for value in values})


def parse_strategies(raw_value: str) -> list[str]:
    if isinstance(raw_value, list):
        return raw_value
    strategies = [item.strip() for item in raw_value.split(",") if item.strip()]
    return list(dict.fromkeys(strategies)) if strategies else ["changed_only"]


def build_config(args: argparse.Namespace) -> BenchmarkConfig:
    repo_path = str(Path(args.repo_path).resolve())
    output_dir = str(Path(args.output_dir).resolve())
    raw_strategies = getattr(args, "strategies", "changed_only")
    compare_embeddings = getattr(args, "compare_embeddings", True)
    store_raw_vectors = getattr(args, "store_raw_vectors", True)
    parser_mode = getattr(args, "parser_mode", "ast")
    predictions_path = getattr(args, "predictions_path", None)
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
        strategies=parse_strategies(raw_strategies),
        compare_embeddings=compare_embeddings,
        store_raw_vectors=store_raw_vectors,
        parser_mode=parser_mode,
        predictions_path=predictions_path,
    )


def load_config(argv: Optional[list[str]] = None) -> BenchmarkConfig:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    # If JSON config is specified, load and merge it
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            import json
            with config_path.open("r", encoding="utf-8") as f:
                json_config = json.load(f)
                for key, value in json_config.items():
                    if hasattr(args, key) and getattr(args, key) == parser.get_default(key):
                        setattr(args, key, value)
                        
    return build_config(args)


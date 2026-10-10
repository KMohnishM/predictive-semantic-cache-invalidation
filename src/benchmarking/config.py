"""Benchmark configuration helpers."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path
from typing import Optional

from .types import BenchmarkConfig

logger = logging.getLogger("benchmarking")


DEFAULT_REPO_URL = "https://github.com/psf/black.git"
DEFAULT_CONFIG_FILENAME = "benchmark_settings.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _default_config_path() -> Optional[Path]:
    """Locate benchmark_settings.json in the working directory, else the project root."""
    for candidate in (Path.cwd() / DEFAULT_CONFIG_FILENAME, PROJECT_ROOT / DEFAULT_CONFIG_FILENAME):
        if candidate.exists():
            return candidate
    return None


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for benchmarking configuration.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(description="Run the retrieval benchmark pipeline")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--repo-path", default="workspace/black")
    parser.add_argument("--output-dir", default="benchmark_runs")
    parser.add_argument("--benchmark-version", default="1.0")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--num-commits", type=int, default=10)
    parser.add_argument("--commit-stride", type=int, default=1)
    parser.add_argument("--sampling-mode", choices=["adjacent", "stride", "manual"], default="adjacent")
    # Phase 1.3: default changed from "synthetic" to "hybrid"
    parser.add_argument(
        "--query-mode",
        choices=["synthetic", "curated", "hybrid"],
        default="hybrid",
        help="Query generation mode: synthetic (auto-generated), curated (hand-authored), "
             "or hybrid (curated + synthetic supplement). Default: hybrid",
    )
    # Phase 4.2: default curated path registered
    parser.add_argument(
        "--curated-queries-path",
        default="src/benchmarking/data/curated_queries.json",
        help="Path to curated queries JSON or CSV file",
    )
    parser.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--clean-mode", action="store_true")
    parser.add_argument("--top-k-values", default="1,5,10")
    parser.add_argument("--max-queries-per-entity", type=int, default=2)
    # Phase 2.4: predictive_ml and fixed_hop in default strategies
    parser.add_argument(
        "--strategies",
        default="changed_only,fixed_hop,predictive_ml,full_reindex",
        help="Comma-separated list of candidate invalidation strategies",
    )
    parser.add_argument(
        "--compare-embeddings",
        action="store_true",
        default=True,
        help="Perform direct vector embedding similarity comparison",
    )
    parser.add_argument("--no-compare-embeddings", action="store_false", dest="compare_embeddings")
    parser.add_argument(
        "--store-raw-vectors",
        action="store_true",
        default=True,
        help="Include raw full float vectors in comparison output",
    )
    parser.add_argument("--no-store-raw-vectors", action="store_false", dest="store_raw_vectors")
    parser.add_argument(
        "--context-chunking",
        action="store_true",
        default=True,
        help="Embed entities with one-hop call-graph context (same text as Pipeline A training)",
    )
    parser.add_argument("--no-context-chunking", action="store_false", dest="context_chunking")
    parser.add_argument(
        "--config",
        default=None,
        help=f"Path to JSON configuration file (default: {DEFAULT_CONFIG_FILENAME} if present)",
    )
    parser.add_argument(
        "--parser-mode",
        choices=["tree_sitter"],
        default="tree_sitter",
        help="Repository parser mode (tree_sitter only — uses Pipeline A TreeSitterRepoParser)",
    )
    parser.add_argument(
        "--predictions-path",
        default=None,
        help="[Deprecated] Path to JSON file containing Pipeline A's ML predictions",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Path to trained DriftPredictor .pkl model artifact for dynamic inference",
    )
    # Phase 2.3: hop depth for fixed_hop
    parser.add_argument(
        "--hop-k",
        type=int,
        default=2,
        help="Hop depth for fixed_hop strategy (default: 2)",
    )
    # Phase 2.3: score threshold for predictive_ml
    parser.add_argument(
        "--ml-threshold",
        type=float,
        default=None,
        help="Probability threshold for predictive_ml (default: the threshold chosen at training time)",
    )
    # Phase 3.3: multi-seed aggregation
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=1,
        help="Number of runs on disjoint, successively older commit windows, aggregated as mean ± std (default: 1)",
    )
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git ref (branch, tag or commit) the sampled commit window ends at (default: HEAD)",
    )
    parser.add_argument(
        "--history-offset",
        type=int,
        default=0,
        help="End the sampled commit window this many commits before HEAD (default: 0)",
    )
    return parser


def parse_top_k_values(raw_value: str) -> list[int]:
    """Parse comma-separated top-K values string into sorted integer list.

    Args:
        raw_value: Comma-separated string or list of values.

    Returns:
        Sorted list of unique integer K cutoffs.
    """
    if isinstance(raw_value, list):
        return sorted({int(value) for value in raw_value})
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return sorted({int(value) for value in values})


def parse_strategies(raw_value: str) -> list[str]:
    """Parse comma-separated strategy names string into ordered list.

    Args:
        raw_value: Comma-separated string or list of strategy names.

    Returns:
        List of unique strategy names.
    """
    if isinstance(raw_value, list):
        return raw_value
    strategies = [item.strip() for item in raw_value.split(",") if item.strip()]
    return list(dict.fromkeys(strategies)) if strategies else ["changed_only"]


def build_config(args: argparse.Namespace) -> BenchmarkConfig:
    """Build BenchmarkConfig instance from parsed CLI arguments.

    Args:
        args: Parsed argparse.Namespace object.

    Returns:
        Constructed BenchmarkConfig object.
    """
    repo_path = str(Path(args.repo_path).resolve())
    output_dir = str(Path(args.output_dir).resolve())
    raw_strategies = getattr(args, "strategies", "changed_only,fixed_hop,predictive_ml,full_reindex")
    compare_embeddings = getattr(args, "compare_embeddings", True)
    store_raw_vectors = getattr(args, "store_raw_vectors", True)
    parser_mode = getattr(args, "parser_mode", "ast")
    predictions_path = getattr(args, "predictions_path", None)
    model_path = getattr(args, "model_path", None)
    hop_k = getattr(args, "hop_k", 2)
    ml_threshold = getattr(args, "ml_threshold", None)
    n_seeds = getattr(args, "n_seeds", 1)
    history_offset = getattr(args, "history_offset", 0)
    ref = getattr(args, "ref", "HEAD")
    context_chunking = getattr(args, "context_chunking", True)
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
        model_path=model_path,
        hop_k=hop_k,
        ml_threshold=ml_threshold,
        n_seeds=n_seeds,
        history_offset=history_offset,
        ref=ref,
        context_chunking=context_chunking,
    )


def _explicit_cli_dests(parser: argparse.ArgumentParser, argv: Optional[list[str]] = None) -> set:
    """Destinations the user actually passed on the command line (even if equal to the default)."""
    import copy
    probe = copy.deepcopy(parser)
    for action in probe._actions:
        action.default = argparse.SUPPRESS
    explicit, _ = probe.parse_known_args(argv)
    return set(vars(explicit))


def load_config(argv: Optional[list[str]] = None) -> BenchmarkConfig:
    """Load benchmark configuration by merging CLI flags and JSON config file if present.

    Args:
        argv: Command-line arguments list or None to use sys.argv.

    Returns:
        Constructed BenchmarkConfig instance.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # JSON config: explicit --config, else benchmark_settings.json if present.
    # CLI overrides JSON.
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            raise FileNotFoundError(f"--config file not found: {config_path}")
    else:
        config_path = _default_config_path()

    if config_path is not None:
        import json
        logger.info(f"Loading benchmark configuration from {config_path.resolve()}")
        with config_path.open("r", encoding="utf-8") as f:
            json_config = json.load(f)
        explicit = _explicit_cli_dests(parser, argv)
        for key, value in json_config.items():
            if not hasattr(args, key):
                logger.warning(f"Ignoring unknown key {key!r} in {config_path}")
                continue
            if key not in explicit:  # CLI flags always win over the JSON file
                setattr(args, key, value)
    else:
        logger.info(f"No --config given and no {DEFAULT_CONFIG_FILENAME} found; using CLI defaults.")

    return build_config(args)

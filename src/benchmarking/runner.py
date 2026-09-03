"""Orchestrator for the standalone benchmark pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
import sys
from typing import Dict, List, Optional

import numpy as np

# Ensure project root and src directory are in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from embedder.embedding_manager import EmbeddingManager
    from parser.git_helper import GitHelper
except ImportError:
    try:
        from src.embedder.embedding_manager import EmbeddingManager
        from src.parser.git_helper import GitHelper
    except ImportError:
        from ..embedder.embedding_manager import EmbeddingManager
        from ..parser.git_helper import GitHelper

from .commit_sampler import sample_commit_pairs
from .config import load_config
from .dataset_builder import build_dataset
from .embedding_comparator import compare_index_snapshots
from .index_builder import build_index_snapshot, build_selective_snapshot, retrieve_top_k
from .metrics import mean_reciprocal_rank, ndcg_at_k, rank_delta, recall_at_k, score_delta
from .query_sources import build_queries
from .reporting import (
    aggregate_multi_run_results,
    check_and_warn_saturation,
    write_aggregated_report,
    write_summary_report,
)
from .serialization import persist_run
from .strategy_runner import decide_updated_entities
from .repository_snapshot import build_repository_snapshot
from .types import (
    BenchmarkConfig,
    BenchmarkSummary,
    PerQueryResult,
    StrategyEmbeddingComparisonResult,
)

logger = logging.getLogger("benchmarking")


def _build_run_id(config: BenchmarkConfig, commit_before: str, commit_after: str) -> str:
    return f"benchmark_v{config.benchmark_version}_seed{config.seed}_{commit_before[:8]}_{commit_after[:8]}"


# ---------------------------------------------------------------------------
# Phase 3.3: multi-seed entry point
# ---------------------------------------------------------------------------

def run_benchmark(config: BenchmarkConfig) -> Path:
    """
    Entry point for the benchmark pipeline.

    Phase 3.3: when config.n_seeds > 1, runs the benchmark n_seeds times with
    different seeds and writes an aggregated report with mean ± std metrics.
    When n_seeds == 1 (default), delegates directly to _run_single_benchmark().
    """
    if config.n_seeds <= 1:
        return _run_single_benchmark(config)

    # Multi-seed aggregation mode
    all_run_strategy_summaries: List[Dict] = []
    output_dirs: List[Path] = []

    for seed_idx in range(config.n_seeds):
        seed_val = seed_idx * 17 + config.seed   # deterministic, non-overlapping seeds
        seeded_config = replace(config, seed=seed_val, n_seeds=1)
        logger.info(f"\n{'='*60}")
        logger.info(f"Multi-seed run {seed_idx + 1}/{config.n_seeds}  (seed={seed_val})")
        logger.info(f"{'='*60}")

        out_dir = _run_single_benchmark(seeded_config)
        output_dirs.append(out_dir)

        # Load strategy_summaries from persisted JSON
        summary_file = out_dir / "summary_metrics.json"
        if summary_file.exists():
            with summary_file.open("r", encoding="utf-8") as f:
                run_data = json.load(f)
            strat_summaries = run_data.get("strategy_summaries", {})
            if strat_summaries:
                all_run_strategy_summaries.append(strat_summaries)

    if all_run_strategy_summaries:
        aggregated = aggregate_multi_run_results(all_run_strategy_summaries)
        agg_path = Path(config.output_dir) / "aggregated_report.md"
        write_aggregated_report(str(agg_path), aggregated, config.n_seeds)
        logger.info(f"Aggregated report ({config.n_seeds} seeds) written to: {agg_path}")

    # Return last single-run dir for compatibility
    return output_dirs[-1] if output_dirs else Path(config.output_dir)


# ---------------------------------------------------------------------------
# Core single-run logic (was run_benchmark before Phase 3.3)
# ---------------------------------------------------------------------------

def _run_single_benchmark(config: BenchmarkConfig) -> Path:
    logger.info("==================================================================")
    logger.info("Initializing Retrieval & Embedding Quality Benchmarking Pipeline")
    logger.info(f"Repository Path : {config.repo_path}")
    logger.info(f"Output Root     : {config.output_dir}")
    logger.info(f"Embedding Model : {config.model_name}")
    logger.info(f"Strategies      : {config.strategies}")
    logger.info(f"Query Mode      : {config.query_mode}")
    logger.info(f"hop_k           : {config.hop_k}")
    logger.info(f"ml_threshold    : {config.ml_threshold}")
    logger.info("==================================================================")

    git_helper = GitHelper(config.repo_path)
    embedding_manager = EmbeddingManager(model_name=config.model_name, clean_mode=config.clean_mode)

    # Load ML predictions if provided (Phase 2.1/3.2: float score support)
    ml_predictions: Optional[Dict] = None
    if config.predictions_path:
        pred_path = Path(config.predictions_path)
        if pred_path.exists():
            logger.info(f"Loading ML predictions from {pred_path}")
            with pred_path.open("r", encoding="utf-8") as f:
                ml_predictions = json.load(f)
            # Log score distribution for sanity-checking
            if ml_predictions:
                scores = [v for v in ml_predictions.values() if isinstance(v, float)]
                if scores:
                    logger.info(
                        f"  Predictions loaded: {len(ml_predictions)} entries, "
                        f"score range [{min(scores):.4f}, {max(scores):.4f}], "
                        f"mean={sum(scores)/len(scores):.4f}"
                    )
        else:
            logger.warning(f"Predictions path {pred_path} does not exist — predictive_ml will fall back to changed_only.")

    logger.info(f"Sampling commit pairs (num_commits={config.num_commits}, mode='{config.sampling_mode}')...")
    commit_pairs = sample_commit_pairs(
        git_helper,
        num_commits=config.num_commits,
        sampling_mode=config.sampling_mode,
        commit_stride=config.commit_stride,
    )
    if not commit_pairs:
        raise RuntimeError("No commit pairs available for benchmarking")

    logger.info(f"Sampled {len(commit_pairs)} commit pair(s) for benchmarking.")

    all_results: List[PerQueryResult] = []
    all_embedding_comparisons: List[StrategyEmbeddingComparisonResult] = []
    all_queries = []
    run_id = _build_run_id(config, commit_pairs[0].commit_before, commit_pairs[0].commit_after)

    for pair_idx, commit_pair in enumerate(commit_pairs, start=1):
        logger.info(
            f"\n--- [Commit Pair {pair_idx}/{len(commit_pairs)}] "
            f"{commit_pair.commit_before[:8]} -> {commit_pair.commit_after[:8]} ---"
        )

        logger.info(f"Parsing repository snapshot at commit_before (mode={config.parser_mode})...")
        # Phase 1.2: build_repository_snapshot now returns snapshot with .graph and .parser populated
        before_snapshot = build_repository_snapshot(
            git_helper,
            commit_pair.commit_before,
            parser_mode=config.parser_mode,
        )
        logger.info(f"  Extracted {len(before_snapshot.entities)} entities at commit {commit_pair.commit_before[:8]}.")

        logger.info(f"Parsing repository snapshot at commit_after (mode={config.parser_mode})...")
        after_snapshot = build_repository_snapshot(
            git_helper,
            commit_pair.commit_after,
            parser_mode=config.parser_mode,
        )
        logger.info(f"  Extracted {len(after_snapshot.entities)} entities at commit {commit_pair.commit_after[:8]}.")

        modified_files = set(git_helper.get_modified_files(commit_pair.commit_before, commit_pair.commit_after))
        changed_entity_ids = [
            entity_id for entity_id, entity in after_snapshot.entities.items()
            if entity.file_path in modified_files
        ]
        all_entity_ids = list(after_snapshot.entities.keys())
        logger.info(
            f"  Modified files: {len(modified_files)}, "
            f"Modified entities: {len(changed_entity_ids)}"
        )

        logger.info("Generating evaluation queries...")
        # Phase 1.2: pass after_snapshot.graph for caller-perspective synthetic queries
        queries = build_queries(
            snapshot=after_snapshot,
            commit_pair=commit_pair,
            query_mode=config.query_mode,
            curated_queries_path=config.curated_queries_path,
            max_queries_per_entity=config.max_queries_per_entity,
            modified_entity_ids=set(changed_entity_ids),
            repo_graph=after_snapshot.graph,  # Phase 1.2
        )
        all_queries.extend(queries)
        logger.info(f"  Generated {len(queries)} query case(s).")
        dataset_rows = build_dataset(commit_pair, queries)

        logger.info("Generating Baseline index embeddings for commit_after (Full Re-index)...")
        baseline_snapshot = build_index_snapshot(after_snapshot, embedding_manager)

        logger.info("Generating Cached index embeddings for commit_before...")
        before_index_snapshot = build_index_snapshot(before_snapshot, embedding_manager)

        for strategy_name in config.strategies:
            logger.info(f"\nEvaluating Candidate Strategy: '{strategy_name}'...")
            # Phase 2.2: pass repo_parser (from snapshot.parser) and strategy_params
            strategy_decision = decide_updated_entities(
                strategy_name,
                changed_entity_ids,
                len(after_snapshot.entities),
                all_entity_ids=all_entity_ids,
                ml_predictions=ml_predictions,
                repo_parser=after_snapshot.parser,          # Phase 2.2
                strategy_params={                            # Phase 2.2/2.3
                    "hop_k":        config.hop_k,
                    "ml_threshold": config.ml_threshold,
                },
            )
            logger.info(
                f"  Strategy '{strategy_name}' re-embeds "
                f"{len(strategy_decision.updated_entity_ids)}/{len(after_snapshot.entities)} "
                f"entities ({strategy_decision.updated_fraction:.2%})."
            )

            candidate_snapshot = build_selective_snapshot(
                baseline_snapshot,
                before_index_snapshot,
                strategy_decision.updated_entity_ids,
            )

            if config.compare_embeddings:
                logger.info(f"  Computing direct vector embedding similarity for '{strategy_name}'...")
                comp_result = compare_index_snapshots(
                    baseline_snapshot=baseline_snapshot,
                    candidate_snapshot=candidate_snapshot,
                    modified_files=modified_files,
                    strategy_name=strategy_name,
                    store_raw_vectors=config.store_raw_vectors,
                    before_entity_ids=set(before_snapshot.entities.keys()),
                    updated_entity_ids=strategy_decision.updated_entity_ids,
                )
                all_embedding_comparisons.append(comp_result)
                logger.info(
                    f"  [Embedding Similarity] Mean: {comp_result.mean_cosine_similarity:.4f} | "
                    f"Min: {comp_result.min_cosine_similarity:.4f} | "
                    f"P95: {comp_result.p95_cosine_similarity:.4f}"
                )

            logger.info(
                f"  Running retrieval queries ({len(dataset_rows)} cases) "
                f"against Baseline and '{strategy_name}' Candidate indices..."
            )
            for query_idx, query_row in enumerate(dataset_rows, start=1):
                if query_idx % 10 == 0 or query_idx == len(dataset_rows):
                    logger.info(f"    Retrieval progress: {query_idx}/{len(dataset_rows)} queries processed.")

                baseline_result = retrieve_top_k(
                    query_row.query.query_text, baseline_snapshot, embedding_manager,
                    top_k=max(config.top_k_values)
                )
                selective_result = retrieve_top_k(
                    query_row.query.query_text, candidate_snapshot, embedding_manager,
                    top_k=max(config.top_k_values)
                )

                target_id = query_row.query.target_entity_id
                baseline_rank = (
                    baseline_result.ranked_entity_ids.index(target_id) + 1
                    if target_id in baseline_result.ranked_entity_ids
                    else len(baseline_result.ranked_entity_ids) + 1
                )
                selective_rank = (
                    selective_result.ranked_entity_ids.index(target_id) + 1
                    if target_id in selective_result.ranked_entity_ids
                    else len(selective_result.ranked_entity_ids) + 1
                )
                baseline_score = (
                    baseline_result.ranked_scores[baseline_rank - 1]
                    if baseline_rank - 1 < len(baseline_result.ranked_scores) else 0.0
                )
                selective_score = (
                    selective_result.ranked_scores[selective_rank - 1]
                    if selective_rank - 1 < len(selective_result.ranked_scores) else 0.0
                )

                top_k = max(config.top_k_values)
                all_results.append(
                    PerQueryResult(
                        run_id=run_id,
                        commit_before=query_row.commit_before,
                        commit_after=query_row.commit_after,
                        query_id=query_row.query.query_id,
                        query_text=query_row.query.query_text,
                        query_source=query_row.query.query_source,
                        category=query_row.query.category,
                        target_entity_id=target_id,
                        target_entity_name=query_row.query.target_entity_name,
                        expected_behavior=query_row.query.expected_behavior,
                        baseline_rank=baseline_rank,
                        selective_rank=selective_rank,
                        baseline_score=baseline_score,
                        selective_score=selective_score,
                        top_k_hit_baseline=recall_at_k(baseline_result.ranked_entity_ids, target_id, top_k) > 0,
                        top_k_hit_selective=recall_at_k(selective_result.ranked_entity_ids, target_id, top_k) > 0,
                        freshness_pass=(
                            query_row.query.expected_behavior == "latest_snapshot"
                            and target_id in selective_result.ranked_entity_ids[:top_k]
                        ),
                        cache_preservation_pass=(
                            query_row.query.expected_behavior != "latest_snapshot"
                            and target_id in selective_result.ranked_entity_ids[:top_k]
                        ),
                        rank_delta=rank_delta(baseline_rank, selective_rank),
                        score_delta=score_delta(baseline_score, selective_score),
                        updated_entity_fraction=strategy_decision.updated_fraction,
                        strategy_name=strategy_decision.strategy_name,
                    )
                )

    logger.info("\nAggregating benchmark results across all commit pairs and strategies...")

    total_queries = len(all_results)
    changed_query_count = sum(1 for r in all_results if r.category == "changed_entity")
    unchanged_query_count = total_queries - changed_query_count

    # Group results by strategy
    results_by_strategy: Dict[str, List[PerQueryResult]] = {}
    for result in all_results:
        results_by_strategy.setdefault(result.strategy_name, []).append(result)

    strategy_summaries: Dict = {}
    for strategy_name, strategy_results in results_by_strategy.items():
        strat_queries = len(strategy_results)
        n_freshness_successes = sum(1 for r in strategy_results if r.freshness_pass)
        n_cache_successes     = sum(1 for r in strategy_results if r.cache_preservation_pass)
        strat_freshness_success = n_freshness_successes / strat_queries if strat_queries else 0.0
        strat_cache_success     = n_cache_successes     / strat_queries if strat_queries else 0.0
        # Phase 3.1: benchmark_passed REMOVED — Wilson CIs computed in reporting.py instead

        strat_baseline_mrr = float(
            sum(1.0 / r.baseline_rank for r in strategy_results) / strat_queries
        ) if strat_queries else 0.0
        strat_baseline_ndcg = float(
            sum(
                1.0 / np.log2(r.baseline_rank + 1) if r.baseline_rank <= 10 else 0.0
                for r in strategy_results
            ) / strat_queries
        ) if strat_queries else 0.0

        strat_selective_mrr = float(
            sum(1.0 / r.selective_rank for r in strategy_results) / strat_queries
        ) if strat_queries else 0.0
        strat_selective_ndcg = float(
            sum(
                1.0 / np.log2(r.selective_rank + 1) if r.selective_rank <= 10 else 0.0
                for r in strategy_results
            ) / strat_queries
        ) if strat_queries else 0.0

        # Get update fraction from embedding comparisons (if available)
        strat_update_fraction = 0.0
        if all_embedding_comparisons:
            for comp in all_embedding_comparisons:
                if comp.strategy_name == strategy_name:
                    strat_update_fraction = comp.updated_fraction
                    break
        else:
            # Fall back to fraction from any result row for this strategy
            for r in strategy_results:
                strat_update_fraction = r.updated_entity_fraction
                break

        strategy_summaries[strategy_name] = {
            "baseline_metrics":  {"mrr": strat_baseline_mrr,  "ndcg_at_10": strat_baseline_ndcg},
            "selective_metrics": {"mrr": strat_selective_mrr, "ndcg_at_10": strat_selective_ndcg},
            "metric_deltas": {
                "mrr":        strat_selective_mrr  - strat_baseline_mrr,
                "ndcg_at_10": strat_selective_ndcg - strat_baseline_ndcg,
            },
            "freshness_success_rate":          strat_freshness_success,
            "cache_preservation_success_rate": strat_cache_success,
            "candidate_update_fraction":       strat_update_fraction,
            # Phase 3.1: raw counts stored so reporting.py can compute Wilson CIs
            "freshness_successes": n_freshness_successes,
            "cache_successes":     n_cache_successes,
            "total_queries":       strat_queries,
            # benchmark_passed REMOVED (was: strat_freshness_success >= 0.5 and strat_cache_success >= 0.5)
        }

    # Phase 1.4: run saturation guard after strategy_summaries are built
    is_saturated = check_and_warn_saturation(strategy_summaries)
    if is_saturated:
        strategy_summaries["__saturation_warning__"] = {
            "message": (
                "Benchmark saturated: strategies are indistinguishable on retrieval metrics "
                "despite differing update costs. Results should not be used for comparison. "
                "See logs for details."
            )
        }

    # Backward-compat flat fields (first strategy)
    first_strat = config.strategies[0] if config.strategies else "selective"
    first_summary = strategy_summaries.get(first_strat, {})

    baseline_metrics      = first_summary.get("baseline_metrics",  {"mrr": 0.0, "ndcg_at_10": 0.0})
    selective_metrics     = first_summary.get("selective_metrics", {"mrr": 0.0, "ndcg_at_10": 0.0})
    metric_deltas         = first_summary.get("metric_deltas",     {"mrr": 0.0, "ndcg_at_10": 0.0})
    freshness_success_rate    = first_summary.get("freshness_success_rate", 0.0)
    cache_success_rate        = first_summary.get("cache_preservation_success_rate", 0.0)
    candidate_update_fraction = first_summary.get("candidate_update_fraction", 0.0)

    embedding_summaries = (
        [comp.to_dict() for comp in all_embedding_comparisons]
        if all_embedding_comparisons else None
    )

    # Phase 3.1: BenchmarkSummary no longer has benchmark_passed; saturation_warning added
    summary = BenchmarkSummary(
        run_id=run_id,
        total_queries=total_queries,
        changed_query_count=changed_query_count,
        unchanged_query_count=unchanged_query_count,
        baseline_metrics=baseline_metrics,
        selective_metrics=selective_metrics,
        metric_deltas=metric_deltas,
        freshness_success_rate=freshness_success_rate,
        cache_preservation_success_rate=cache_success_rate,
        candidate_update_fraction=candidate_update_fraction,
        saturation_warning=is_saturated,                    # Phase 1.4
        embedding_comparison_summaries=embedding_summaries,
        strategy_summaries=strategy_summaries,
    )

    output_dir = Path(config.output_dir).resolve() / run_id
    logger.info(f"Persisting run artifacts to: {output_dir}")
    persist_run(
        str(output_dir),
        config,
        commit_pairs,
        all_queries,
        all_results,
        summary,
        embedding_comparisons=all_embedding_comparisons,
    )
    write_summary_report(str(output_dir), summary, embedding_comparisons=all_embedding_comparisons)
    logger.info(f"Benchmark run complete. Report saved to: {output_dir / 'summary_report.md'}")
    return output_dir


def main(argv: list[str] | None = None) -> Path:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    config = load_config(argv)
    return run_benchmark(config)


if __name__ == "__main__":
    main()
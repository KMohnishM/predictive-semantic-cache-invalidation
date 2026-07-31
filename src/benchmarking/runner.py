"""Orchestrator for the standalone benchmark pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import List
from dataclasses import replace

# Ensure project root and src directory are in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from embedding_manager import EmbeddingManager
from git_helper import GitHelper

from benchmarking.commit_sampler import sample_commit_pairs
from benchmarking.config import load_config
from benchmarking.dataset_builder import build_dataset
from benchmarking.embedding_comparator import compare_index_snapshots
from benchmarking.index_builder import build_index_snapshot, build_selective_snapshot, retrieve_top_k
from benchmarking.metrics import mean_reciprocal_rank, ndcg_at_k, rank_delta, recall_at_k, score_delta
from benchmarking.query_sources import build_queries
from benchmarking.reporting import write_summary_report
from benchmarking.serialization import persist_run
from benchmarking.strategy_runner import decide_updated_entities
from benchmarking.repository_snapshot import build_repository_snapshot
from benchmarking.types import (
    BenchmarkConfig,
    BenchmarkSummary,
    PerQueryResult,
    StrategyEmbeddingComparisonResult,
)

logger = logging.getLogger("benchmarking")


def _build_run_id(config: BenchmarkConfig, commit_before: str, commit_after: str) -> str:
    return f"benchmark_v{config.benchmark_version}_seed{config.seed}_{commit_before[:8]}_{commit_after[:8]}"


def run_benchmark(config: BenchmarkConfig) -> Path:
    logger.info("==================================================================")
    logger.info("Initializing Retrieval & Embedding Quality Benchmarking Pipeline")
    logger.info(f"Repository Path : {config.repo_path}")
    logger.info(f"Output Root     : {config.output_dir}")
    logger.info(f"Embedding Model : {config.model_name}")
    logger.info(f"Strategies      : {config.strategies}")
    logger.info(f"Query Mode      : {config.query_mode}")
    logger.info("==================================================================")

    git_helper = GitHelper(config.repo_path)
    embedding_manager = EmbeddingManager(model_name=config.model_name, clean_mode=config.clean_mode)

    # Initialize Joern Session if joern_only mode is chosen
    joern_session = None
    if config.parser_mode == "joern_only":
        try:
            sys.path.insert(0, str(project_root / "joern_helper"))
            from joern_interactive import JoernSession
            joern_session = JoernSession(config.repo_path)
            logger.info("Joern session successfully connected for benchmarking.")
        except Exception as e:
            logger.warning(f"Failed to connect Joern session: {e}. Falling back to AST parser_mode.")
            config = replace(config, parser_mode="ast")

    # Load ML predictions if provided
    ml_predictions = None
    if config.predictions_path:
        pred_path = Path(config.predictions_path)
        if pred_path.exists():
            import json
            logger.info(f"Loading ML predictions from {pred_path}")
            with pred_path.open("r", encoding="utf-8") as f:
                ml_predictions = json.load(f)
        else:
            logger.warning(f"Predictions path {pred_path} does not exist.")

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
        logger.info(f"\n--- [Commit Pair {pair_idx}/{len(commit_pairs)}] {commit_pair.commit_before[:8]} -> {commit_pair.commit_after[:8]} ---")

        logger.info(f"Parsing repository snapshot at commit_before (mode={config.parser_mode})...")
        before_snapshot = build_repository_snapshot(git_helper, commit_pair.commit_before, parser_mode=config.parser_mode, joern_session=joern_session)
        logger.info(f"  Extracted {len(before_snapshot.entities)} entities at commit {commit_pair.commit_before[:8]}.")

        logger.info(f"Parsing repository snapshot at commit_after (mode={config.parser_mode})...")
        after_snapshot = build_repository_snapshot(git_helper, commit_pair.commit_after, parser_mode=config.parser_mode, joern_session=joern_session)
        logger.info(f"  Extracted {len(after_snapshot.entities)} entities at commit {commit_pair.commit_after[:8]}.")

        modified_files = set(git_helper.get_modified_files(commit_pair.commit_before, commit_pair.commit_after))
        changed_entity_ids = [entity_id for entity_id, entity in after_snapshot.entities.items() if entity.file_path in modified_files]
        all_entity_ids = list(after_snapshot.entities.keys())
        logger.info(f"  Modified files count: {len(modified_files)}, Modified entities count: {len(changed_entity_ids)}")

        logger.info("Generating evaluation queries...")
        queries = build_queries(
            snapshot=after_snapshot,
            commit_pair=commit_pair,
            query_mode=config.query_mode,
            curated_queries_path=config.curated_queries_path,
            max_queries_per_entity=config.max_queries_per_entity,
            modified_entity_ids=set(changed_entity_ids),
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
            strategy_decision = decide_updated_entities(
                strategy_name,
                changed_entity_ids,
                len(after_snapshot.entities),
                all_entity_ids=all_entity_ids,
                ml_predictions=ml_predictions,
            )
            logger.info(f"  Strategy '{strategy_name}' re-embeds {len(strategy_decision.updated_entity_ids)}/{len(after_snapshot.entities)} entities ({strategy_decision.updated_fraction:.2%}).")

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
                logger.info(f"  [Embedding Similarity Metrics] Mean: {comp_result.mean_cosine_similarity:.4f} | Min: {comp_result.min_cosine_similarity:.4f} | P95: {comp_result.p95_cosine_similarity:.4f}")

            logger.info(f"  Running retrieval queries ({len(dataset_rows)} cases) against Baseline and '{strategy_name}' Candidate indices...")
            for query_idx, query_row in enumerate(dataset_rows, start=1):
                if query_idx % 10 == 0 or query_idx == len(dataset_rows):
                    logger.info(f"    Retrieval progress: {query_idx}/{len(dataset_rows)} queries processed.")

                baseline_result = retrieve_top_k(query_row.query.query_text, baseline_snapshot, embedding_manager, top_k=max(config.top_k_values))
                selective_result = retrieve_top_k(query_row.query.query_text, candidate_snapshot, embedding_manager, top_k=max(config.top_k_values))

                baseline_rank = baseline_result.ranked_entity_ids.index(query_row.query.target_entity_id) + 1 if query_row.query.target_entity_id in baseline_result.ranked_entity_ids else len(baseline_result.ranked_entity_ids) + 1
                selective_rank = selective_result.ranked_entity_ids.index(query_row.query.target_entity_id) + 1 if query_row.query.target_entity_id in selective_result.ranked_entity_ids else len(selective_result.ranked_entity_ids) + 1
                baseline_score = baseline_result.ranked_scores[baseline_rank - 1] if baseline_rank - 1 < len(baseline_result.ranked_scores) else 0.0
                selective_score = selective_result.ranked_scores[selective_rank - 1] if selective_rank - 1 < len(selective_result.ranked_scores) else 0.0

                all_results.append(
                    PerQueryResult(
                        run_id=run_id,
                        commit_before=query_row.commit_before,
                        commit_after=query_row.commit_after,
                        query_id=query_row.query.query_id,
                        query_text=query_row.query.query_text,
                        query_source=query_row.query.query_source,
                        category=query_row.query.category,
                        target_entity_id=query_row.query.target_entity_id,
                        target_entity_name=query_row.query.target_entity_name,
                        expected_behavior=query_row.query.expected_behavior,
                        baseline_rank=baseline_rank,
                        selective_rank=selective_rank,
                        baseline_score=baseline_score,
                        selective_score=selective_score,
                        top_k_hit_baseline=recall_at_k(baseline_result.ranked_entity_ids, query_row.query.target_entity_id, max(config.top_k_values)) > 0,
                        top_k_hit_selective=recall_at_k(selective_result.ranked_entity_ids, query_row.query.target_entity_id, max(config.top_k_values)) > 0,
                        freshness_pass=query_row.query.expected_behavior == "latest_snapshot" and query_row.query.target_entity_id in selective_result.ranked_entity_ids[: max(config.top_k_values)],
                        cache_preservation_pass=query_row.query.expected_behavior != "latest_snapshot" and query_row.query.target_entity_id in selective_result.ranked_entity_ids[: max(config.top_k_values)],
                        rank_delta=rank_delta(baseline_rank, selective_rank),
                        score_delta=score_delta(baseline_score, selective_score),
                        updated_entity_fraction=strategy_decision.updated_fraction,
                        strategy_name=strategy_decision.strategy_name,
                    )
                )

    logger.info("\nAggregating benchmark results across all commit pairs and strategies...")
    import numpy as np

    total_queries = len(all_results)
    changed_query_count = sum(1 for result in all_results if result.category == "changed_entity")
    unchanged_query_count = total_queries - changed_query_count

    # Group results by strategy
    results_by_strategy = {}
    for result in all_results:
        results_by_strategy.setdefault(result.strategy_name, []).append(result)

    strategy_summaries = {}
    for strategy_name, strategy_results in results_by_strategy.items():
        strat_queries = len(strategy_results)
        strat_freshness_success = sum(1 for r in strategy_results if r.freshness_pass) / strat_queries if strat_queries else 0.0
        strat_cache_success = sum(1 for r in strategy_results if r.cache_preservation_pass) / strat_queries if strat_queries else 0.0
        strat_passed = strat_freshness_success >= 0.5 and strat_cache_success >= 0.5

        strat_baseline_mrr = float(sum(1.0 / r.baseline_rank for r in strategy_results) / strat_queries) if strat_queries else 0.0
        strat_baseline_ndcg = float(sum(1.0 / np.log2(r.baseline_rank + 1) if r.baseline_rank <= 10 else 0.0 for r in strategy_results) / strat_queries) if strat_queries else 0.0

        strat_selective_mrr = float(sum(1.0 / r.selective_rank for r in strategy_results) / strat_queries) if strat_queries else 0.0
        strat_selective_ndcg = float(sum(1.0 / np.log2(r.selective_rank + 1) if r.selective_rank <= 10 else 0.0 for r in strategy_results) / strat_queries) if strat_queries else 0.0

        strat_update_fraction = 0.0
        if all_embedding_comparisons:
            for comp in all_embedding_comparisons:
                if comp.strategy_name == strategy_name:
                    strat_update_fraction = comp.updated_fraction
                    break

        strategy_summaries[strategy_name] = {
            "baseline_metrics": {"mrr": strat_baseline_mrr, "ndcg_at_10": strat_baseline_ndcg},
            "selective_metrics": {"mrr": strat_selective_mrr, "ndcg_at_10": strat_selective_ndcg},
            "metric_deltas": {
                "mrr": strat_selective_mrr - strat_baseline_mrr,
                "ndcg_at_10": strat_selective_ndcg - strat_baseline_ndcg,
            },
            "freshness_success_rate": strat_freshness_success,
            "cache_preservation_success_rate": strat_cache_success,
            "candidate_update_fraction": strat_update_fraction,
            "benchmark_passed": strat_passed,
        }

    # For backward compatibility, default to the first strategy's metrics in the flat fields
    first_strat = config.strategies[0] if config.strategies else "selective"
    first_summary = strategy_summaries.get(first_strat, {})

    baseline_metrics = first_summary.get("baseline_metrics", {"mrr": 0.0, "ndcg_at_10": 0.0})
    selective_metrics = first_summary.get("selective_metrics", {"mrr": 0.0, "ndcg_at_10": 0.0})
    metric_deltas = first_summary.get("metric_deltas", {"mrr": 0.0, "ndcg_at_10": 0.0})
    freshness_success_rate = first_summary.get("freshness_success_rate", 0.0)
    cache_success_rate = first_summary.get("cache_preservation_success_rate", 0.0)
    candidate_update_fraction = first_summary.get("candidate_update_fraction", 0.0)
    benchmark_passed = first_summary.get("benchmark_passed", False)

    embedding_summaries = [comp.to_dict() for comp in all_embedding_comparisons] if all_embedding_comparisons else None

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
        benchmark_passed=benchmark_passed,
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
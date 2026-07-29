"""Orchestrator for the standalone benchmark pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import List

# Ensure project root is in sys.path for direct script execution or module runs
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.embedding_manager import EmbeddingManager
from src.git_helper import GitHelper

from src.benchmarking.commit_sampler import sample_commit_pairs
from src.benchmarking.config import load_config
from src.benchmarking.dataset_builder import build_dataset
from src.benchmarking.embedding_comparator import compare_index_snapshots
from src.benchmarking.index_builder import build_index_snapshot, build_selective_snapshot, retrieve_top_k
from src.benchmarking.metrics import mean_reciprocal_rank, ndcg_at_k, rank_delta, recall_at_k, score_delta
from src.benchmarking.query_sources import build_queries
from src.benchmarking.reporting import write_summary_report
from src.benchmarking.serialization import persist_run
from src.benchmarking.strategy_runner import decide_updated_entities
from src.benchmarking.repository_snapshot import build_repository_snapshot
from src.benchmarking.types import (
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

        logger.info("Parsing AST repository snapshot at commit_before...")
        before_snapshot = build_repository_snapshot(git_helper, commit_pair.commit_before)
        logger.info(f"  Extracted {len(before_snapshot.entities)} entities at commit {commit_pair.commit_before[:8]}.")

        logger.info("Parsing AST repository snapshot at commit_after...")
        after_snapshot = build_repository_snapshot(git_helper, commit_pair.commit_after)
        logger.info(f"  Extracted {len(after_snapshot.entities)} entities at commit {commit_pair.commit_after[:8]}.")

        logger.info("Generating evaluation queries...")
        queries = build_queries(
            snapshot=after_snapshot,
            commit_pair=commit_pair,
            query_mode=config.query_mode,
            curated_queries_path=config.curated_queries_path,
            max_queries_per_entity=config.max_queries_per_entity,
        )
        all_queries.extend(queries)
        logger.info(f"  Generated {len(queries)} query case(s).")
        dataset_rows = build_dataset(commit_pair, queries)

        logger.info("Generating Baseline index embeddings for commit_after (Full Re-index)...")
        baseline_snapshot = build_index_snapshot(after_snapshot, embedding_manager)

        logger.info("Generating Cached index embeddings for commit_before...")
        before_index_snapshot = build_index_snapshot(before_snapshot, embedding_manager)

        modified_files = set(git_helper.get_modified_files(commit_pair.commit_before, commit_pair.commit_after))
        changed_entity_ids = [entity_id for entity_id, entity in after_snapshot.entities.items() if entity.file_path in modified_files]
        all_entity_ids = list(after_snapshot.entities.keys())
        logger.info(f"  Modified files count: {len(modified_files)}, Modified entities count: {len(changed_entity_ids)}")

        for strategy_name in config.strategies:
            logger.info(f"\nEvaluating Candidate Strategy: '{strategy_name}'...")
            strategy_decision = decide_updated_entities(
                strategy_name,
                changed_entity_ids,
                len(after_snapshot.entities),
                all_entity_ids=all_entity_ids,
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
    total_queries = len(all_results)
    changed_query_count = sum(1 for result in all_results if result.category == "changed_entity")
    unchanged_query_count = total_queries - changed_query_count
    freshness_success_rate = sum(1 for result in all_results if result.freshness_pass) / total_queries if total_queries else 0.0
    cache_success_rate = sum(1 for result in all_results if result.cache_preservation_pass) / total_queries if total_queries else 0.0
    benchmark_passed = freshness_success_rate >= 0.5 and cache_success_rate >= 0.5

    baseline_metrics = {
        "mrr": float(sum(1.0 / result.baseline_rank for result in all_results) / total_queries) if total_queries else 0.0,
        "ndcg_at_10": float(sum(1.0 / result.baseline_rank for result in all_results) / total_queries) if total_queries else 0.0,
    }
    selective_metrics = {
        "mrr": float(sum(1.0 / result.selective_rank for result in all_results) / total_queries) if total_queries else 0.0,
        "ndcg_at_10": float(sum(1.0 / result.selective_rank for result in all_results) / total_queries) if total_queries else 0.0,
    }
    metric_deltas = {key: selective_metrics[key] - baseline_metrics[key] for key in baseline_metrics}

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
        candidate_update_fraction=all_embedding_comparisons[0].updated_fraction if all_embedding_comparisons else 0.0,
        benchmark_passed=benchmark_passed,
        embedding_comparison_summaries=embedding_summaries,
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
"""Orchestrator for the standalone benchmark pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import List

from embedding_manager import EmbeddingManager
from git_helper import GitHelper

from benchmarking.commit_sampler import sample_commit_pairs
from benchmarking.config import load_config
from benchmarking.dataset_builder import build_dataset
from benchmarking.index_builder import build_index_snapshot, build_selective_snapshot, retrieve_top_k
from benchmarking.metrics import mean_reciprocal_rank, ndcg_at_k, rank_delta, recall_at_k, score_delta
from benchmarking.query_sources import build_queries
from benchmarking.reporting import write_summary_report
from benchmarking.serialization import persist_run
from benchmarking.strategy_runner import decide_updated_entities
from benchmarking.repository_snapshot import build_repository_snapshot
from benchmarking.types import BenchmarkConfig, BenchmarkSummary, PerQueryResult


def _build_run_id(config: BenchmarkConfig, commit_before: str, commit_after: str) -> str:
    return f"benchmark_v{config.benchmark_version}_seed{config.seed}_{commit_before[:8]}_{commit_after[:8]}"


def run_benchmark(config: BenchmarkConfig) -> Path:
    git_helper = GitHelper(config.repo_path)
    embedding_manager = EmbeddingManager(model_name=config.model_name, clean_mode=config.clean_mode)

    commit_pairs = sample_commit_pairs(
        git_helper,
        num_commits=config.num_commits,
        sampling_mode=config.sampling_mode,
        commit_stride=config.commit_stride,
    )
    if not commit_pairs:
        raise RuntimeError("No commit pairs available for benchmarking")

    all_results: List[PerQueryResult] = []
    run_id = _build_run_id(config, commit_pairs[0].commit_before, commit_pairs[0].commit_after)

    for commit_pair in commit_pairs:
        before_snapshot = build_repository_snapshot(git_helper, commit_pair.commit_before)
        after_snapshot = build_repository_snapshot(git_helper, commit_pair.commit_after)
        queries = build_queries(
            snapshot=after_snapshot,
            commit_pair=commit_pair,
            query_mode=config.query_mode,
            curated_queries_path=config.curated_queries_path,
            max_queries_per_entity=config.max_queries_per_entity,
        )
        dataset_rows = build_dataset(commit_pair, queries)
        baseline_snapshot = build_index_snapshot(after_snapshot, embedding_manager)

        modified_files = set(git_helper.get_modified_files(commit_pair.commit_before, commit_pair.commit_after))
        changed_entity_ids = [entity_id for entity_id, entity in after_snapshot.entities.items() if entity.file_path in modified_files]
        strategy_decision = decide_updated_entities("changed_only", changed_entity_ids, len(after_snapshot.entities))
        before_index_snapshot = build_index_snapshot(before_snapshot, embedding_manager)
        selective_snapshot = build_selective_snapshot(baseline_snapshot, before_index_snapshot, strategy_decision.updated_entity_ids)

        for query_row in dataset_rows:
            baseline_result = retrieve_top_k(query_row.query.query_text, baseline_snapshot, embedding_manager, top_k=max(config.top_k_values))
            selective_result = retrieve_top_k(query_row.query.query_text, selective_snapshot, embedding_manager, top_k=max(config.top_k_values))

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
        candidate_update_fraction=strategy_decision.updated_fraction,
        benchmark_passed=benchmark_passed,
    )

    output_dir = Path(config.output_dir).resolve() / run_id
    persist_run(str(output_dir), config, commit_pairs, queries, all_results, summary)
    write_summary_report(str(output_dir), summary)
    return output_dir


def main(argv: list[str] | None = None) -> Path:
    config = load_config(argv)
    return run_benchmark(config)

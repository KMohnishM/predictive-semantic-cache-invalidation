"""Orchestrator for the standalone benchmark pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

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
    from extractor.semantic_modification import (
        compute_semantic_modified_entities,
        compute_source_changed_entities,
    )
    from parser.git_helper import GitHelper
except ImportError:
    try:
        from src.embedder.embedding_manager import EmbeddingManager
        from src.extractor.semantic_modification import (
            compute_semantic_modified_entities,
            compute_source_changed_entities,
        )
        from src.parser.git_helper import GitHelper
    except ImportError:
        from ..embedder.embedding_manager import EmbeddingManager
        from ..extractor.semantic_modification import (
            compute_semantic_modified_entities,
            compute_source_changed_entities,
        )
        from ..parser.git_helper import GitHelper

from .commit_sampler import sample_commit_pairs
from .config import load_config
from .dataset_builder import build_dataset
from .embedding_comparator import compare_index_snapshots
from .index_builder import build_entity_texts, build_index_snapshot, build_selective_snapshot
from .metrics import rank_delta, score_delta
from .query_sources import build_queries
from .reporting import (
    aggregate_multi_run_results,
    check_and_warn_saturation,
    wilson_ci,
    write_aggregated_report,
    write_summary_report,
)
from .serialization import persist_run
from .visualizer import generate_benchmark_charts
from .strategy_runner import decide_updated_entities
from .repository_snapshot import build_repository_snapshot
from .cache_tracker import StatefulCacheTracker
from .model_runner import ModelRunner
from .types import (
    BenchmarkConfig,
    BenchmarkSummary,
    PerQueryResult,
    StrategyEmbeddingComparisonResult,
)

logger = logging.getLogger("benchmarking")


def _build_run_id(config: BenchmarkConfig, commit_before: str, commit_after: str) -> str:
    """Build unique run identifier string from benchmark config and commit hashes.

    Args:
        config: BenchmarkConfig instance.
        commit_before: Previous commit hash string.
        commit_after: Target commit hash string.

    Returns:
        Formatted run ID string.
    """
    return f"benchmark_v{config.benchmark_version}_seed{config.seed}_{commit_before[:8]}_{commit_after[:8]}"


def _target_ranks_and_scores(
    query_matrix: np.ndarray,
    snapshot,
    target_ids: List[str],
) -> tuple:
    """Exact 1-indexed rank (over the FULL index) and score of each query's target.

    rank = 1 + number of entities scoring strictly higher than the target.
    A target missing from the index gets rank len(index) + 1 and score 0.0.
    """
    entity_ids = list(snapshot.entity_embeddings.keys())
    index_of = {eid: i for i, eid in enumerate(entity_ids)}
    matrix = np.asarray([snapshot.entity_embeddings[eid] for eid in entity_ids], dtype=float)
    scores = query_matrix @ matrix.T                      # (n_queries, n_entities)
    ranks = np.full(len(target_ids), len(entity_ids) + 1, dtype=int)
    target_scores = np.zeros(len(target_ids), dtype=float)
    for row, target in enumerate(target_ids):
        col = index_of.get(target)
        if col is None:
            continue
        target_scores[row] = scores[row, col]
        ranks[row] = 1 + int(np.sum(scores[row] > scores[row, col]))
    return ranks, target_scores


# ---------------------------------------------------------------------------
# Phase 3.3: multi-seed entry point
# ---------------------------------------------------------------------------

def run_benchmark(config: BenchmarkConfig) -> Path:
    """
    Entry point for the benchmark pipeline.

    When config.n_seeds > 1, runs the benchmark n_seeds times on DISJOINT commit
    windows (run i ends i * window_span commits further back in history) and
    writes an aggregated report with mean ± std across windows. The pipeline is
    deterministic, so repeating it on the same window would add no information.
    When n_seeds == 1 (default), delegates directly to _run_single_benchmark().
    """
    if config.n_seeds <= 1:
        return _run_single_benchmark(config)

    # Multi-seed aggregation mode
    all_run_strategy_summaries: List[Dict] = []
    output_dirs: List[Path] = []

    window_span = max(1, (config.num_commits - 1) * max(1, config.commit_stride))
    for seed_idx in range(config.n_seeds):
        seed_val = seed_idx * 17 + config.seed   # labels the run; windows differ via offset
        offset = config.history_offset + seed_idx * window_span
        seeded_config = replace(config, seed=seed_val, n_seeds=1, history_offset=offset)
        logger.info(f"\n{'='*60}")
        logger.info(
            f"Multi-window run {seed_idx + 1}/{config.n_seeds}  "
            f"(seed={seed_val}, window ends {offset} commits before HEAD)"
        )
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
    """Execute a single benchmark run for the given configuration.

    Args:
        config: BenchmarkConfig instance.

    Returns:
        Path pointing to output directory containing benchmark artifacts.
    """
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

    # Load dynamic .pkl model artifact if provided (Phase 3.2: full switch to .pkl).
    # A configured-but-missing model is a hard error: silently falling back would
    # report changed_only numbers under the predictive_ml name.
    model_runner: Optional[ModelRunner] = None
    if getattr(config, "model_path", None):
        model_file = Path(config.model_path)
        if not model_file.exists():
            raise FileNotFoundError(
                f"model_path {model_file} does not exist. Train a DriftPredictor with "
                f"run_experiment.py (it writes results/<run>/drift_predictor.pkl) and point "
                f"model_path at it, or remove predictive_ml from strategies."
            )
        logger.info(f"Loading dynamic .pkl model artifact from {model_file}...")
        model_runner = ModelRunner(str(model_file))

    # Load ML predictions if provided (legacy fallback)
    ml_predictions: Optional[Dict] = None
    if getattr(config, "predictions_path", None) and not model_runner:
        pred_path = Path(config.predictions_path)
        if pred_path.exists():
            logger.info(f"Loading legacy ML predictions from {pred_path}")
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
            raise FileNotFoundError(f"predictions_path {pred_path} does not exist.")

    if "predictive_ml" in config.strategies and model_runner is None and ml_predictions is None:
        raise ValueError(
            "Strategy 'predictive_ml' requested but no model is configured. Set model_path "
            "(see benchmark_settings.json) or remove predictive_ml from strategies."
        )

    logger.info(f"Sampling commit pairs (num_commits={config.num_commits}, mode='{config.sampling_mode}')...")
    commit_pairs = sample_commit_pairs(
        git_helper,
        num_commits=config.num_commits,
        sampling_mode=config.sampling_mode,
        commit_stride=config.commit_stride,
        history_offset=config.history_offset,
        ref=config.ref,
    )
    if not commit_pairs:
        raise RuntimeError("No commit pairs available for benchmarking")

    logger.info(f"Sampled {len(commit_pairs)} commit pair(s) for benchmarking.")

    all_results: List[PerQueryResult] = []
    all_embedding_comparisons: List[StrategyEmbeddingComparisonResult] = []
    all_queries = []
    run_id = _build_run_id(config, commit_pairs[0].commit_before, commit_pairs[0].commit_after)

    # Initialize per-strategy stateful cache trackers and active cached vector snapshots
    cache_trackers: Dict[str, StatefulCacheTracker] = {
        s: StatefulCacheTracker(strategy_name=s) for s in config.strategies
    }
    cached_index_snapshots: Dict[str, Any] = {}
    # Re-embedding cost summed over ALL commit pairs (not just the first).
    updated_totals: Dict[str, int] = {s: 0 for s in config.strategies}
    entity_totals: Dict[str, int] = {s: 0 for s in config.strategies}
    ndcg_k = 10 if 10 in config.top_k_values else max(config.top_k_values)
    hit_k = max(config.top_k_values)

    # Raw TreeSitterRepoParser per commit, so ModelRunner can diff an entity's
    # anchor commit against the current one exactly as training does.
    parsers_by_commit: Dict[str, Any] = {}
    # Running feature state for predictive_ml, mirroring run_experiment.py:
    # entity -> commits where it was semantically modified, and entity -> last
    # observed embedding drift (known only for entities that were re-embedded).
    ml_modification_history: Dict[str, List[str]] = {}
    ml_previous_drifts: Dict[str, float] = {}

    def _raw_parser(snapshot) -> Any:
        return getattr(snapshot.parser, "_parser", snapshot.parser)

    for pair_idx, commit_pair in enumerate(commit_pairs, start=1):
        logger.info(
            f"\n--- [Commit Pair {pair_idx}/{len(commit_pairs)}] "
            f"{commit_pair.commit_before[:8]} -> {commit_pair.commit_after[:8]} ---"
        )

        logger.info(f"Parsing repository snapshot at commit_before (mode={config.parser_mode})...")
        before_snapshot = build_repository_snapshot(
            git_helper,
            commit_pair.commit_before,
        )
        logger.info(f"  Extracted {len(before_snapshot.entities)} entities at commit {commit_pair.commit_before[:8]}.")

        logger.info(f"Parsing repository snapshot at commit_after (mode={config.parser_mode})...")
        after_snapshot = build_repository_snapshot(
            git_helper,
            commit_pair.commit_after,
        )
        logger.info(f"  Extracted {len(after_snapshot.entities)} entities at commit {commit_pair.commit_after[:8]}.")

        parsers_by_commit[commit_pair.commit_before] = _raw_parser(before_snapshot)
        parsers_by_commit[commit_pair.commit_after] = _raw_parser(after_snapshot)

        modified_files = set(git_helper.get_modified_files(commit_pair.commit_before, commit_pair.commit_after))
        # Entities whose OWN source changed (what changed_only re-embeds).
        source_changed_ids = sorted(compute_source_changed_entities(
            parsers_by_commit[commit_pair.commit_before],
            parsers_by_commit[commit_pair.commit_after],
            modified_files,
        ))
        # Entities whose EMBEDDED TEXT changed (own source or call-graph context):
        # these are the targets whose fresh vector differs, i.e. "changed" queries.
        texts_before = build_entity_texts(before_snapshot, embedding_manager, contextual=config.context_chunking)
        texts_after = build_entity_texts(after_snapshot, embedding_manager, contextual=config.context_chunking)
        prepare = embedding_manager._prepare_text
        changed_entity_ids = [
            eid for eid, text in texts_after.items()
            if eid not in texts_before or prepare(texts_before[eid]) != prepare(text)
        ]
        all_entity_ids = list(after_snapshot.entities.keys())
        file_level = sum(1 for e in after_snapshot.entities.values() if e.file_path in modified_files)
        logger.info(
            f"  Modified files: {len(modified_files)}, entities in modified files: {file_level}, "
            f"source-changed: {len(source_changed_ids)}, embedded-text-changed: {len(changed_entity_ids)}"
        )

        logger.info("Generating evaluation queries...")
        queries = build_queries(
            snapshot=after_snapshot,
            commit_pair=commit_pair,
            query_mode=config.query_mode,
            curated_queries_path=config.curated_queries_path,
            max_queries_per_entity=config.max_queries_per_entity,
            modified_entity_ids=set(changed_entity_ids),
            repo_graph=after_snapshot.graph,
        )
        n_generated = len(queries)
        queries = [q for q in queries if q.target_entity_id in after_snapshot.entities]
        if len(queries) < n_generated:
            logger.info(
                f"  Dropped {n_generated - len(queries)} query case(s) whose target entity "
                f"does not exist at {commit_pair.commit_after[:8]}."
            )
        all_queries.extend(queries)
        logger.info(f"  Generated {len(queries)} query case(s).")
        dataset_rows = build_dataset(commit_pair, queries)
        unique_texts = sorted({row.query.query_text for row in dataset_rows})
        text_vectors = (
            embedding_manager.generate_embeddings_batch({f"query::{t}": t for t in unique_texts})
            if unique_texts else {}
        )
        query_matrix = np.asarray(
            [text_vectors[f"query::{row.query.query_text}"] for row in dataset_rows], dtype=float
        ).reshape(len(dataset_rows), -1)
        target_ids = [row.query.target_entity_id for row in dataset_rows]
        baseline_ranks, baseline_scores = np.array([], dtype=int), np.array([])

        logger.info("Generating Baseline index embeddings for commit_after (Full Re-index)...")
        baseline_snapshot = build_index_snapshot(
            after_snapshot, embedding_manager, contextual=config.context_chunking
        )

        if dataset_rows:
            baseline_ranks, baseline_scores = _target_ranks_and_scores(query_matrix, baseline_snapshot, target_ids)

        # On the very first pair, initialize stateful trackers and cached vector indices with before_snapshot
        if pair_idx == 1:
            initial_before_index = build_index_snapshot(
                before_snapshot, embedding_manager, contextual=config.context_chunking
            )
            for s in config.strategies:
                cache_trackers[s].initialize(before_snapshot.entities.keys(), commit_pair.commit_before)
                cached_index_snapshots[s] = initial_before_index

        for strategy_name in config.strategies:
            logger.info(f"\nEvaluating Candidate Strategy: '{strategy_name}'...")
            tracker = cache_trackers[strategy_name]
            prev_cached_index = cached_index_snapshots.get(strategy_name)

            # Underlying repo_parser instance for dependency resolution and code metrics
            raw_parser = _raw_parser(after_snapshot)

            strategy_decision = decide_updated_entities(
                strategy_name,
                source_changed_ids,
                len(after_snapshot.entities),
                all_entity_ids=all_entity_ids,
                ml_predictions=ml_predictions,
                repo_parser=raw_parser,
                strategy_params={
                    "hop_k": config.hop_k,
                    "ml_threshold": config.ml_threshold,
                },
                cache_tracker=tracker,
                model_runner=model_runner,
                git_helper=git_helper,
                current_commit=commit_pair.commit_after,
                parser_provider=parsers_by_commit.get,
                modification_history=ml_modification_history,
                previous_drifts=ml_previous_drifts,
            )
            logger.info(
                f"  Strategy '{strategy_name}' re-embeds "
                f"{len(strategy_decision.updated_entity_ids)}/{len(after_snapshot.entities)} "
                f"entities ({strategy_decision.updated_fraction:.2%})."
            )

            # Build selective candidate snapshot combining baseline with statefully cached vectors
            candidate_snapshot = build_selective_snapshot(
                baseline_snapshot,
                prev_cached_index if prev_cached_index is not None else baseline_snapshot,
                strategy_decision.updated_entity_ids,
            )

            if strategy_name == "predictive_ml" and prev_cached_index is not None:
                # Drift is observable only for entities we actually re-embedded.
                for eid in strategy_decision.updated_entity_ids:
                    old_vec = prev_cached_index.entity_embeddings.get(eid)
                    new_vec = baseline_snapshot.entity_embeddings.get(eid)
                    if old_vec is not None and new_vec is not None:
                        ml_previous_drifts[eid] = float(1.0 - np.dot(old_vec, new_vec))

            # Entities absent from the cache were embedded fresh at commit_after:
            # start tracking them so later edits to them are detected.
            prev_ids = prev_cached_index.entity_embeddings if prev_cached_index is not None else {}
            tracker.register_new_entities(
                [eid for eid in candidate_snapshot.entity_embeddings if eid not in prev_ids],
                commit_pair.commit_after,
            )

            updated_totals[strategy_name] += len(strategy_decision.updated_entity_ids)
            entity_totals[strategy_name] += len(after_snapshot.entities)

            # Advance stateful anchor pointers and update cached vector index for this strategy
            tracker.mark_updated(strategy_decision.updated_entity_ids, commit_pair.commit_after)
            cached_index_snapshots[strategy_name] = candidate_snapshot

            if config.compare_embeddings:
                logger.info(f"  Computing direct vector embedding similarity for '{strategy_name}'...")
                before_ids = (
                    set(prev_cached_index.entity_embeddings.keys())
                    if prev_cached_index is not None
                    else set(before_snapshot.entities.keys())
                )
                comp_result = compare_index_snapshots(
                    baseline_snapshot=baseline_snapshot,
                    candidate_snapshot=candidate_snapshot,
                    modified_files=modified_files,
                    strategy_name=strategy_name,
                    store_raw_vectors=config.store_raw_vectors,
                    before_entity_ids=before_ids,
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
            selective_ranks, selective_scores = (
                _target_ranks_and_scores(query_matrix, candidate_snapshot, target_ids)
                if dataset_rows else (np.array([], dtype=int), np.array([]))
            )
            for query_idx, query_row in enumerate(dataset_rows):
                target_id = query_row.query.target_entity_id
                baseline_rank = int(baseline_ranks[query_idx])
                selective_rank = int(selective_ranks[query_idx])
                baseline_score = float(baseline_scores[query_idx])
                selective_score = float(selective_scores[query_idx])

                top_k_hit_b = baseline_rank <= hit_k
                top_k_hit_s = selective_rank <= hit_k
                b_ndcg = 1.0 / np.log2(baseline_rank + 1) if baseline_rank <= ndcg_k else 0.0
                s_ndcg = 1.0 / np.log2(selective_rank + 1) if selective_rank <= ndcg_k else 0.0

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
                        top_k_hit_baseline=top_k_hit_b,
                        top_k_hit_selective=top_k_hit_s,
                        freshness_pass=(
                            query_row.query.expected_behavior == "latest_snapshot"
                            and top_k_hit_s
                        ),
                        cache_preservation_pass=(
                            query_row.query.expected_behavior != "latest_snapshot"
                            and top_k_hit_s
                        ),
                        rank_delta=rank_delta(baseline_rank, selective_rank),
                        score_delta=score_delta(baseline_score, selective_score),
                        updated_entity_fraction=strategy_decision.updated_fraction,
                        strategy_name=strategy_decision.strategy_name,
                        rank_agreement=(selective_rank == baseline_rank),
                        relative_freshness_pass=(top_k_hit_s if top_k_hit_b else True),
                        ndcg_ratio=(s_ndcg / b_ndcg if b_ndcg > 0 else 1.0),
                    )
                )

        # Update the running modification history after this pair's predictions,
        # matching training (history used for a pair excludes that pair itself).
        for eid in compute_semantic_modified_entities(
            parsers_by_commit[commit_pair.commit_before],
            parsers_by_commit[commit_pair.commit_after],
            modified_files,
        ):
            ml_modification_history.setdefault(eid, []).append(commit_pair.commit_after)

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
        changed_queries_strat = sum(1 for r in strategy_results if r.expected_behavior == "latest_snapshot")
        unchanged_queries_strat = strat_queries - changed_queries_strat

        n_freshness_successes = sum(1 for r in strategy_results if r.freshness_pass)
        n_cache_successes     = sum(1 for r in strategy_results if r.cache_preservation_pass)

        strat_freshness_success = (
            n_freshness_successes / changed_queries_strat if changed_queries_strat > 0 else 0.0
        )
        strat_cache_success = (
            n_cache_successes / unchanged_queries_strat if unchanged_queries_strat > 0 else 0.0
        )

        # Baseline Agreement Metrics
        baseline_hits = sum(1 for r in strategy_results if r.top_k_hit_baseline)
        relative_freshness_successes = sum(
            1 for r in strategy_results if r.top_k_hit_baseline and r.top_k_hit_selective
        )
        relative_freshness_rate = (
            relative_freshness_successes / baseline_hits if baseline_hits > 0 else 1.0
        )

        rank_agreements = sum(1 for r in strategy_results if r.rank_agreement)
        rank_agreement_rate = rank_agreements / strat_queries if strat_queries > 0 else 1.0

        strat_baseline_mrr = float(
            sum(1.0 / r.baseline_rank for r in strategy_results) / strat_queries
        ) if strat_queries else 0.0
        strat_baseline_ndcg = float(
            sum(
                1.0 / np.log2(r.baseline_rank + 1) if r.baseline_rank <= ndcg_k else 0.0
                for r in strategy_results
            ) / strat_queries
        ) if strat_queries else 0.0

        strat_selective_mrr = float(
            sum(1.0 / r.selective_rank for r in strategy_results) / strat_queries
        ) if strat_queries else 0.0
        strat_selective_ndcg = float(
            sum(
                1.0 / np.log2(r.selective_rank + 1) if r.selective_rank <= ndcg_k else 0.0
                for r in strategy_results
            ) / strat_queries
        ) if strat_queries else 0.0

        mrr_ratio = strat_selective_mrr / strat_baseline_mrr if strat_baseline_mrr > 0 else 1.0
        ndcg_ratio = strat_selective_ndcg / strat_baseline_ndcg if strat_baseline_ndcg > 0 else 1.0

        # Re-embedding cost over ALL commit pairs: total re-embedded / total entities.
        strat_update_fraction = (
            updated_totals.get(strategy_name, 0) / entity_totals[strategy_name]
            if entity_totals.get(strategy_name) else 0.0
        )
        fresh_ci = wilson_ci(n_freshness_successes, changed_queries_strat)
        cache_ci = wilson_ci(n_cache_successes, unchanged_queries_strat)

        strategy_summaries[strategy_name] = {
            "baseline_metrics":  {"mrr": strat_baseline_mrr,  "ndcg_at_10": strat_baseline_ndcg},
            "selective_metrics": {"mrr": strat_selective_mrr, "ndcg_at_10": strat_selective_ndcg},
            "metric_deltas": {
                "mrr":        strat_selective_mrr  - strat_baseline_mrr,
                "ndcg_at_10": strat_selective_ndcg - strat_baseline_ndcg,
            },
            "freshness_success_rate":          strat_freshness_success,
            "cache_preservation_success_rate": strat_cache_success,
            "relative_freshness_rate":         relative_freshness_rate,
            "rank_agreement_rate":             rank_agreement_rate,
            "mrr_ratio":                       mrr_ratio,
            "ndcg_ratio":                      ndcg_ratio,
            "candidate_update_fraction":       strat_update_fraction,
            "freshness_ci_95":                 list(fresh_ci),
            "cache_preservation_ci_95":        list(cache_ci),
            "freshness_successes": n_freshness_successes,
            "cache_successes":     n_cache_successes,
            "changed_queries":     changed_queries_strat,
            "unchanged_queries":   unchanged_queries_strat,
            "total_queries":       strat_queries,
            "ndcg_k":              ndcg_k,
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

    # Auto-generate visual charts alongside the markdown report
    from .reporting import compute_pareto_frontier
    real_summaries = {k: v for k, v in strategy_summaries.items() if not k.startswith("__")}
    pareto = compute_pareto_frontier(real_summaries) if len(real_summaries) >= 2 else []
    chart_paths = generate_benchmark_charts(
        str(output_dir),
        strategy_summaries=strategy_summaries,
        embedding_comparisons=all_embedding_comparisons if all_embedding_comparisons else None,
        pareto_strategies=pareto,
    )
    if chart_paths:
        logger.info(f"Charts generated: {', '.join(p.name for p in chart_paths)}")

    return output_dir


def main(argv: list[str] | None = None) -> Path:
    """CLI entrypoint for standalone benchmark execution.

    Args:
        argv: Optional command-line argument list.

    Returns:
        Path to output directory containing benchmark results.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    config = load_config(argv)
    return run_benchmark(config)


if __name__ == "__main__":
    main()
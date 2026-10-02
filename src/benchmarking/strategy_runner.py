"""Strategy selection for selective re-embedding benchmark paths."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set

from .types import StrategyDecision

logger = logging.getLogger(__name__)


def _get_stateful_changed_entities(
    all_entity_ids: List[str],
    cache_tracker: Any,
    git_helper: Any,
    current_commit: str,
    repo_parser: Any,
) -> List[str]:
    """
    Identify entities that have changed between their respective cache anchor
    commits and current_commit. Groups entities by anchor to minimize git calls.
    """
    if not cache_tracker or not git_helper or not current_commit or not all_entity_ids:
        return []

    anchors = cache_tracker.get_all_anchors()
    anchor_groups: Dict[str, List[str]] = {}
    for eid in all_entity_ids:
        anchor = anchors.get(eid, "")
        anchor_groups.setdefault(anchor, []).append(eid)

    changed: Set[str] = set()
    for anchor, group_eids in anchor_groups.items():
        if not anchor or anchor == current_commit:
            continue
        try:
            modified_files = set(git_helper.get_modified_files(anchor, current_commit))
        except Exception as exc:
            logger.debug(f"Failed to get modified files {anchor[:8]} -> {current_commit[:8]}: {exc}")
            modified_files = set()

        for eid in group_eids:
            ent = getattr(repo_parser, "get_entity", lambda _: None)(eid)
            if ent and ent.file_path in modified_files:
                changed.add(eid)

    return list(changed)


def decide_updated_entities(
    strategy_name: str,
    changed_entity_ids: List[str],
    total_entities: int,
    all_entity_ids: Optional[List[str]] = None,
    ml_predictions: Optional[Dict[str, Any]] = None,
    repo_parser: Optional[Any] = None,
    strategy_params: Optional[Dict[str, Any]] = None,
    cache_tracker: Optional[Any] = None,
    model_runner: Optional[Any] = None,
    git_helper: Optional[Any] = None,
    current_commit: Optional[str] = None,
    intermediate_commits: Optional[List[str]] = None,
) -> StrategyDecision:
    """
    Decide which entities to re-embed for a given invalidation strategy.
    Supports stateful anchor comparisons (C_cached -> C_current) and dynamic .pkl model inference.

    Args:
        strategy_name:       full_reindex, changed_only, fixed_hop, or predictive_ml
        changed_entity_ids:  Entities touched in the immediate adjacent commit step
        total_entities:      Total entity count in the current snapshot
        all_entity_ids:      All entity IDs in the snapshot
        ml_predictions:      Legacy dict of precomputed predictions (fallback)
        repo_parser:         TreeSitterRepoParser instance
        strategy_params:     Config dict containing hop_k, ml_threshold
        cache_tracker:       StatefulCacheTracker instance tracking per-entity anchors
        model_runner:        ModelRunner instance holding loaded .pkl artifact
        git_helper:          GitHelper instance
        current_commit:      Hash of the current evaluation commit
        intermediate_commits: Optional list of commits between anchor and current
    """
    strategy_params = strategy_params or {}
    start_time = time.perf_counter()

    if strategy_name == "full_reindex":
        # Full re-index: re-embed all entities
        updated = list(all_entity_ids) if all_entity_ids is not None else list(changed_entity_ids)

    elif strategy_name == "changed_only":
        if cache_tracker and git_helper and current_commit and all_entity_ids:
            updated = _get_stateful_changed_entities(
                all_entity_ids, cache_tracker, git_helper, current_commit, repo_parser
            )
            logger.info(
                f"changed_only (stateful): {len(updated)}/{len(all_entity_ids)} entities modified since their anchor"
            )
        else:
            updated = list(changed_entity_ids)

    elif strategy_name == "fixed_hop":
        hop_k = int(strategy_params.get("hop_k", 2))
        if cache_tracker and git_helper and current_commit and all_entity_ids:
            base_changed = _get_stateful_changed_entities(
                all_entity_ids, cache_tracker, git_helper, current_commit, repo_parser
            )
        else:
            base_changed = list(changed_entity_ids)

        if repo_parser is not None and hasattr(repo_parser, "get_dependents"):
            expanded = set(base_changed)
            for eid in list(base_changed):
                try:
                    dependents = repo_parser.get_dependents(eid, max_hops=hop_k)
                    expanded.update(dependents)
                except Exception as exc:
                    logger.debug(f"fixed_hop: get_dependents({eid!r}) raised: {exc}")
            updated = list(expanded)
            logger.info(
                f"fixed_hop(k={hop_k}, stateful): {len(base_changed)} anchor-changed entity/entities "
                f"→ {len(updated)} after {hop_k}-hop propagation"
            )
        else:
            logger.warning("fixed_hop: repo_parser not provided or lacks get_dependents(). Falling back to changed_only.")
            updated = list(base_changed)

    elif strategy_name == "predictive_ml":
        threshold = float(strategy_params.get("ml_threshold", 0.5))

        if model_runner is not None and getattr(model_runner, "is_loaded", False) and all_entity_ids and cache_tracker:
            # Dynamic .pkl inference path
            logger.info(
                f"predictive_ml (dynamic .pkl): evaluating {len(all_entity_ids)} entities "
                f"against stateful anchors at commit {current_commit[:8]}..."
            )
            raw_scores = model_runner.predict_entities(
                entity_ids=all_entity_ids,
                anchor_commits=cache_tracker.get_all_anchors(),
                current_commit=current_commit,
                git_helper=git_helper,
                repo_parser=repo_parser,
                ml_threshold=threshold,
            )
            updated = model_runner.evaluate_invalidation(raw_scores, threshold=threshold)
            logger.info(
                f"predictive_ml (dynamic .pkl, threshold={threshold:.3f}): "
                f"{len(updated)}/{len(all_entity_ids)} entities flagged as stale"
            )

        elif ml_predictions is not None and all_entity_ids is not None:
            # Legacy precomputed predictions dictionary path
            sample_val = next(iter(ml_predictions.values()), None)
            if isinstance(sample_val, float):
                updated = [
                    eid for eid in all_entity_ids
                    if ml_predictions.get(eid, 0.0) >= threshold
                ]
                logger.info(
                    f"predictive_ml (legacy float, threshold={threshold:.3f}): "
                    f"{len(updated)}/{len(all_entity_ids)} entities flagged as stale"
                )
            else:
                updated = [eid for eid in all_entity_ids if ml_predictions.get(eid, False)]
                logger.info(f"predictive_ml (legacy bool): {len(updated)} entities flagged as stale")

        else:
            logger.warning(
                "predictive_ml: neither model_runner (.pkl) nor ml_predictions provided. "
                "Falling back to changed_only."
            )
            if cache_tracker and git_helper and current_commit and all_entity_ids:
                updated = _get_stateful_changed_entities(
                    all_entity_ids, cache_tracker, git_helper, current_commit, repo_parser
                )
            else:
                updated = list(changed_entity_ids)

    else:
        logger.warning(f"Unknown strategy '{strategy_name}' — defaulting to changed_only")
        updated = list(changed_entity_ids)

    updated_fraction = len(updated) / total_entities if total_entities else 0.0
    latency = time.perf_counter() - start_time

    return StrategyDecision(
        strategy_name=strategy_name,
        updated_entity_ids=updated,
        updated_fraction=updated_fraction,
        decision_latency_seconds=latency,
    )

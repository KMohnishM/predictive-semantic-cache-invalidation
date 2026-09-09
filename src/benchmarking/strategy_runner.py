"""Strategy selection for selective re-embedding benchmark paths."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .types import StrategyDecision

logger = logging.getLogger(__name__)


def decide_updated_entities(
    strategy_name: str,
    changed_entity_ids: List[str],
    total_entities: int,
    all_entity_ids: Optional[List[str]] = None,
    ml_predictions: Optional[Dict[str, Any]] = None,
    repo_parser=None,                                     # Phase 2.1: for fixed_hop propagation
    strategy_params: Optional[Dict[str, Any]] = None,    # Phase 2.1: hop_k, ml_threshold
) -> StrategyDecision:
    """
    Decide which entities to re-embed for a given invalidation strategy.

    Args:
        strategy_name:       One of: full_reindex, changed_only, fixed_hop, predictive_ml
        changed_entity_ids:  Entities in files touched by the git diff
        total_entities:      Total entity count in the after-commit snapshot
        all_entity_ids:      All entity IDs in the snapshot (needed by full_reindex, predictive_ml)
        ml_predictions:      Dict mapping entity_id -> float score OR bool.
                             Float scores (from Pipeline A export_predictions()) are
                             thresholded by strategy_params["ml_threshold"].
                             Bool values (legacy) are used directly.
        repo_parser:         Parser with get_dependents(entity_id, max_hops=k).
                             Populated from snapshot.parser (Phase 1.2).
                             Required for fixed_hop; logs warning and falls back if absent.
        strategy_params:     Per-strategy config dict. Supported keys:
                               "hop_k" (int, default 2)   — hop depth for fixed_hop
                               "ml_threshold" (float, default 0.5) — cutoff for predictive_ml

    Phase 2.1 fixes:
        - fixed_hop: was stub identical to changed_only; now does real k-hop propagation
          via repo_parser.get_dependents(eid, max_hops=hop_k)
        - predictive_ml: was bool-only; now supports float scores from Pipeline A;
          both branches handled via isinstance check
    """
    strategy_params = strategy_params or {}
    start_time = time.perf_counter()

    if strategy_name == "full_reindex":
        # Update everything — oracle upper bound for freshness
        updated = list(all_entity_ids) if all_entity_ids is not None else list(changed_entity_ids)

    elif strategy_name == "changed_only":
        # Update only entities in files touched by the git diff
        updated = list(changed_entity_ids)

    elif strategy_name == "fixed_hop":
        # Phase 2.1 FIX: Propagate invalidation k hops outward through the call graph.
        # Start with changed entities; expand to their predecessors (callers) recursively.
        # Previously this was: updated = list(set(changed_entity_ids))  <- identical to changed_only
        hop_k = int(strategy_params.get("hop_k", 2))

        if repo_parser is not None and hasattr(repo_parser, "get_dependents"):
            expanded = set(changed_entity_ids)
            for eid in list(changed_entity_ids):
                try:
                    dependents = repo_parser.get_dependents(eid, max_hops=hop_k)
                    expanded.update(dependents)
                except Exception as exc:
                    logger.debug(f"fixed_hop: get_dependents({eid!r}) raised: {exc}")
            updated = list(expanded)
            logger.info(
                f"fixed_hop(k={hop_k}): {len(changed_entity_ids)} changed entity/entities "
                f"→ {len(updated)} after {hop_k}-hop propagation"
            )
        else:
            # Fallback: no parser available — behave like changed_only with a warning
            logger.warning(
                "fixed_hop: repo_parser not provided or lacks get_dependents(). "
                "Falling back to changed_only behaviour. "
                "Pass repo_parser= to enable hop propagation."
            )
            updated = list(set(changed_entity_ids))

    elif strategy_name == "predictive_ml":
        # Phase 2.1 FIX: Support both float scores (Pipeline A continuous output)
        # and legacy boolean predictions.
        if ml_predictions is not None and all_entity_ids is not None:
            sample_val = next(iter(ml_predictions.values()), None)
            if isinstance(sample_val, float):
                # Continuous score path — apply threshold
                threshold = float(strategy_params.get("ml_threshold", 0.5))
                updated = [
                    eid for eid in all_entity_ids
                    if ml_predictions.get(eid, 0.0) >= threshold
                ]
                logger.info(
                    f"predictive_ml (float, threshold={threshold:.3f}): "
                    f"{len(updated)}/{len(all_entity_ids)} entities flagged as stale"
                )
            else:
                # Legacy boolean path
                updated = [eid for eid in all_entity_ids if ml_predictions.get(eid, False)]
                logger.info(f"predictive_ml (bool): {len(updated)} entities flagged as stale")
        else:
            logger.warning(
                "predictive_ml: ml_predictions not provided or all_entity_ids missing. "
                "Falling back to changed_only. "
                "Pass --predictions-path to enable ML-based invalidation."
            )
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

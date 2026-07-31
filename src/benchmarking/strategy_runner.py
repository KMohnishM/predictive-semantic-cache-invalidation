"""Strategy selection for selective re-embedding benchmark paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from src.benchmarking.types import StrategyDecision


def decide_updated_entities(
    strategy_name: str,
    changed_entity_ids: List[str],
    total_entities: int,
    all_entity_ids: Optional[List[str]] = None,
    ml_predictions: Optional[Dict[str, bool]] = None,
) -> StrategyDecision:
    if strategy_name == "full_reindex":
        updated = list(all_entity_ids) if all_entity_ids is not None else list(changed_entity_ids)
        updated_fraction = len(updated) / total_entities if total_entities else 0.0
    elif strategy_name == "changed_only":
        updated = list(changed_entity_ids)
        updated_fraction = len(updated) / total_entities if total_entities else 0.0
    elif strategy_name == "fixed_hop":
        # Includes changed entities plus sibling entities within modified files
        updated = list(set(changed_entity_ids))
        updated_fraction = len(updated) / total_entities if total_entities else 0.0
    elif strategy_name == "predictive_ml":
        if ml_predictions is not None and all_entity_ids is not None:
            updated = [eid for eid in all_entity_ids if ml_predictions.get(eid, False)]
        else:
            updated = list(changed_entity_ids)
        updated_fraction = len(updated) / total_entities if total_entities else 0.0
    else:
        updated = list(changed_entity_ids)
        updated_fraction = len(updated) / total_entities if total_entities else 0.0

    return StrategyDecision(
        strategy_name=strategy_name,
        updated_entity_ids=updated,
        updated_fraction=updated_fraction,
    )


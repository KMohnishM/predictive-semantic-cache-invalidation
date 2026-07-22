"""Strategy selection for selective re-embedding benchmark paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from benchmarking.types import StrategyDecision


def decide_updated_entities(strategy_name: str, changed_entity_ids: List[str], total_entities: int) -> StrategyDecision:
    if strategy_name == "full_reindex":
        updated = list(changed_entity_ids)
        updated_fraction = 1.0 if total_entities else 0.0
    elif strategy_name == "changed_only":
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

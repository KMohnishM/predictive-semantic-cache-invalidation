"""Stateful cache tracker and drift evaluation interfaces for Pipeline B."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Set

logger = logging.getLogger(__name__)


class DriftEvaluator(Protocol):
    """
    Modular protocol for evaluating entity drift between an anchor commit and current commit.
    Allows direct anchor diffing today, while providing an extension hook for
    intermediate commits inspection in the future.
    """

    def evaluate_drift(
        self,
        entity_id: str,
        anchor_commit: str,
        current_commit: str,
        intermediate_commits: Optional[List[str]] = None,
    ) -> bool:
        """
        Evaluate whether an entity has drifted between anchor_commit and current_commit.

        Args:
            entity_id: Identifier of the entity to evaluate.
            anchor_commit: Commit where the entity was last cached/re-embedded.
            current_commit: Target evaluation commit.
            intermediate_commits: Optional list of commits between anchor and current.

        Returns:
            True if entity has drifted and must be re-embedded; False otherwise.
        """
        ...


class StatefulCacheTracker:
    """
    Tracks stateful cache anchors and invalidation lifecycles across a sequence of commits.

    Instead of evaluating adjacent commit steps (C_{t-1} -> C_t), each entity maintains
    a pointer to the exact commit where its vector was last updated (C_cached).
    When an entity is re-embedded, its anchor advances to C_current.
    """

    def __init__(self, strategy_name: str = "default") -> None:
        self.strategy_name = strategy_name
        self.base_commit: Optional[str] = None
        self._anchors: Dict[str, str] = {}
        self._update_counts: Dict[str, int] = {}
        self._history: List[Dict[str, Any]] = []

    def initialize(self, entity_ids: Iterable[str], base_commit: str) -> None:
        """
        Initialize the cache anchor state with the baseline commit.
        """
        self.base_commit = base_commit
        self._anchors = {eid: base_commit for eid in entity_ids}
        self._update_counts = {eid: 0 for eid in entity_ids}
        self._history.append({
            "event": "initialize",
            "commit": base_commit,
            "entity_count": len(self._anchors),
        })
        logger.info(
            f"[{self.strategy_name}] Initialized StatefulCacheTracker for "
            f"{len(self._anchors)} entities at base commit {base_commit[:8]}"
        )

    def get_anchor(self, entity_id: str) -> str:
        """
        Get the commit hash where entity_id was last re-embedded.
        If unknown, defaults to base_commit (or empty string if not yet initialized).
        """
        if entity_id not in self._anchors:
            if self.base_commit:
                self._anchors[entity_id] = self.base_commit
                self._update_counts[entity_id] = 0
            else:
                return ""
        return self._anchors[entity_id]

    def get_all_anchors(self) -> Dict[str, str]:
        """Return a copy of all active entity anchors."""
        return dict(self._anchors)

    def mark_updated(self, entity_ids: Iterable[str], current_commit: str) -> None:
        """
        Advance cache anchor pointers for re-embedded entities to current_commit.
        """
        updated_set = set(entity_ids)
        for eid in updated_set:
            self._anchors[eid] = current_commit
            self._update_counts[eid] = self._update_counts.get(eid, 0) + 1

        self._history.append({
            "event": "update",
            "commit": current_commit,
            "updated_count": len(updated_set),
            "updated_entity_ids": list(updated_set),
        })

    def get_stale_entities(
        self,
        current_entities: Iterable[str],
        current_commit: str,
        evaluator: DriftEvaluator,
        intermediate_commits: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Identify entities whose cached version has drifted relative to current_commit
        using the provided DriftEvaluator.
        """
        stale_entities: List[str] = []
        for eid in current_entities:
            anchor = self.get_anchor(eid)
            if not anchor or anchor == current_commit:
                continue
            is_stale = evaluator.evaluate_drift(
                entity_id=eid,
                anchor_commit=anchor,
                current_commit=current_commit,
                intermediate_commits=intermediate_commits,
            )
            if is_stale:
                stale_entities.append(eid)
        return stale_entities

    def get_stats(self) -> Dict[str, Any]:
        """
        Return aggregate tracking statistics.
        """
        total_tracked = len(self._anchors)
        total_updates = sum(self._update_counts.values())
        return {
            "strategy_name": self.strategy_name,
            "total_tracked_entities": total_tracked,
            "total_reembedding_events": total_updates,
            "avg_updates_per_entity": (total_updates / total_tracked) if total_tracked > 0 else 0.0,
            "history_steps": len(self._history),
        }

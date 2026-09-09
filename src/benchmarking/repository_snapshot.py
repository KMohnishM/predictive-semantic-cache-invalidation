"""Build repository snapshots from a specific git commit.

Uses the Pipeline A TreeSitterRepoParser from src/parser/ for entity extraction
and call-graph construction, so there is no duplicated parsing logic.
"""

from __future__ import annotations

import logging
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import Pipeline A parser (single source of truth for graph building)
# ---------------------------------------------------------------------------
try:
    from parser.git_helper import GitHelper
    from parser.tree_sitter_repo_parser import TreeSitterRepoParser
except ImportError:
    try:
        from src.parser.git_helper import GitHelper
        from src.parser.tree_sitter_repo_parser import TreeSitterRepoParser
    except ImportError:
        from ..parser.git_helper import GitHelper
        from ..parser.tree_sitter_repo_parser import TreeSitterRepoParser

from .types import RepositoryEntity, RepositorySnapshot


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _list_python_files_at_commit(git_helper: GitHelper, commit_hash: str) -> List[str]:
    output = git_helper._run_git_command(["ls-tree", "-r", "--name-only", commit_hash])
    return [
        line.strip()
        for line in output.splitlines()
        if line.strip() and line.strip().endswith(".py")
    ]


def _adapter_entity(pipeline_a_entity: Any, file_path: str) -> RepositoryEntity:
    """Convert a Pipeline A Entity to a benchmarking RepositoryEntity."""
    return RepositoryEntity(
        entity_id=pipeline_a_entity.entity_id,
        entity_type=pipeline_a_entity.entity_type,
        file_path=file_path,
        lineno=pipeline_a_entity.lineno,
        end_lineno=pipeline_a_entity.end_lineno,
        name=pipeline_a_entity.entity_id.split("::")[-1],
        source_code=pipeline_a_entity.source_code,
    )


# ---------------------------------------------------------------------------
# SnapshotParser — wraps TreeSitterRepoParser for fixed_hop propagation
# ---------------------------------------------------------------------------

class SnapshotParser:
    """
    Thin wrapper around the Pipeline A TreeSitterRepoParser stored on
    RepositorySnapshot.  Provides get_dependents(entity_id, max_hops) for
    fixed_hop propagation in strategy_runner.py.
    """

    def __init__(self, repo_parser: TreeSitterRepoParser) -> None:
        self._parser = repo_parser

    def get_dependents(self, entity_id: str, max_hops: int = 2) -> List[str]:
        """
        Return all entities that (transitively) depend on entity_id up to
        max_hops.  Delegates directly to TreeSitterRepoParser.get_dependents()
        which uses the authoritative call graph built by Pipeline A.
        """
        try:
            result: Set[str] = self._parser.get_dependents(entity_id, max_hops=max_hops)
            return list(result - {entity_id})
        except Exception as exc:
            logger.warning("get_dependents(%s) failed: %s", entity_id, exc)
            return []


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------

def build_repository_snapshot(
    git_helper: GitHelper,
    commit_hash: str,
) -> RepositorySnapshot:
    """
    Build a RepositorySnapshot for a given commit.

    Entity extraction and call-graph construction are delegated entirely to
    TreeSitterRepoParser from src/parser/ (Pipeline A's authoritative parser).
    No duplicated graph-building logic lives here.

    The resulting RepositorySnapshot carries:
        .graph   — the nx.DiGraph from TreeSitterRepoParser.get_graph()
        .parser  — a SnapshotParser wrapping the same TreeSitterRepoParser,
                   used by decide_updated_entities() for fixed_hop propagation
                   and by build_queries() for caller-perspective query generation.
    """
    py_files = _list_python_files_at_commit(git_helper, commit_hash)

    # Check out all Python files from the commit into a temp directory so the
    # Pipeline A parser (which reads from disk) can process them.
    with tempfile.TemporaryDirectory(prefix="bench_snapshot_") as tmp_dir:
        tmp_root = Path(tmp_dir)

        for rel_path in py_files:
            source = git_helper.get_file_content_at_commit(commit_hash, rel_path)
            if not source:
                continue
            dest = tmp_root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source, encoding="utf-8", errors="replace")

        # Build entities + call graph using Pipeline A's TreeSitterRepoParser
        repo_parser = TreeSitterRepoParser(repo_path=str(tmp_root))
        repo_parser.parse_directory(str(tmp_root))

    # Convert Pipeline A Entity objects to benchmarking RepositoryEntity objects
    entities: Dict[str, RepositoryEntity] = {}
    for entity_id, pa_entity in repo_parser.entities.items():
        bench_entity = _adapter_entity(pa_entity, pa_entity.file_path)
        entities[entity_id] = bench_entity

    graph = repo_parser.get_graph()
    snapshot_parser = SnapshotParser(repo_parser)

    logger.info(
        "Snapshot built for %s: %d entities, %d call edges",
        commit_hash[:8],
        len(entities),
        graph.number_of_edges(),
    )

    return RepositorySnapshot(
        commit_hash=commit_hash,
        entities=entities,
        graph=graph,
        parser=snapshot_parser,
    )

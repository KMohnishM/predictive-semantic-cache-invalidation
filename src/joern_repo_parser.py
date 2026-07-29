"""
Joern-native repository parser.
Constructs NetworkX call graphs and extracts code entities directly from Joern CPG sessions.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Set
import networkx as nx
from pathlib import Path

# Add joern_helper to path for session import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "joern_helper"))
try:
    from joern_interactive import JoernSession
except ImportError:
    JoernSession = None

logger = logging.getLogger(__name__)


class JoernRepoParser:
    """
    Parses repository files and constructs a directed Call Graph G=(V, E)
    using a Joern CPG session instead of Python's built-in ast module.
    """

    def __init__(self, repo_path: str, joern_session: Any = None):
        self.repo_path = Path(repo_path)
        self.joern_session = joern_session
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Dict[str, Any]] = {}  # entity_id -> metadata dict

    def parse_repository(self) -> nx.DiGraph:
        """
        Query Joern CPG to extract all methods/functions and construct the call graph.

        Returns:
            networkx.DiGraph representing the repository call graph.
        """
        if self.joern_session is None:
            logger.error("JoernRepoParser requires an active JoernSession.")
            return self.graph

        logger.info(f"Parsing repository using Joern CPG at {self.repo_path}...")
        self.graph.clear()
        self.entities.clear()

        try:
            # 1. Fetch all files from Joern
            files = self.joern_session.get_all_files()
            if not files or not isinstance(files, list):
                logger.warning("No files found in Joern CPG.")
                return self.graph

            # Filter relevant source files
            py_files = [f for f in files if isinstance(f, str) and (f.endswith(".py") or not f.startswith("<"))]

            all_methods = []
            for file_path in py_files:
                true_names = self.joern_session.get_true_names(file_path)
                if true_names and isinstance(true_names, list):
                    for name_tuple in true_names:
                        if isinstance(name_tuple, (list, tuple)) and len(name_tuple) >= 2:
                            short_name, full_name = name_tuple[0], name_tuple[1]
                            
                            # Filter out internal compiler wrappers
                            if full_name.startswith("<") or "<lambda>" in full_name:
                                continue

                            entity_id = f"{file_path}::{full_name}"
                            self.entities[entity_id] = {
                                "entity_id": entity_id,
                                "name": short_name,
                                "full_name": full_name,
                                "file_path": file_path,
                                "type": "function",
                                "source": f"# Joern parsed entity: {full_name}"
                            }
                            self.graph.add_node(
                                entity_id,
                                name=short_name,
                                file_path=file_path,
                                type="function"
                            )
                            all_methods.append((entity_id, full_name))

            # 2. Extract call edges from Joern
            for entity_id, full_name in all_methods:
                callees = self.joern_session.get_callees(full_name)
                if callees and isinstance(callees, list):
                    for callee_full in callees:
                        # Match callee to existing entity_ids
                        for target_id, target_meta in self.entities.items():
                            if target_meta["full_name"] == callee_full:
                                self.graph.add_edge(entity_id, target_id)

            logger.info(
                f"Joern parsing complete: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges extracted."
            )

        except Exception as e:
            logger.error(f"Error parsing repository with Joern: {e}", exc_info=True)

        return self.graph

    def get_entity_source(self, entity_id: str) -> str:
        """Get source code for an entity (fallback to stub)."""
        entity = self.entities.get(entity_id, {})
        return entity.get("source", "")

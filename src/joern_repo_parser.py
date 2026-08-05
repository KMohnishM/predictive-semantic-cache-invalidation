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
from typing import Optional

# Import Entity from repo_parser to produce compatible objects
try:
    from repo_parser import Entity
except Exception:
    Entity = None

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
            py_files = [
                f for f in files
                if isinstance(f, str) and f.endswith(".py") and not f.startswith("<")
            ]
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
            full_name_to_id = {meta["full_name"]: eid for eid, meta in self.entities.items()}
            for entity_id, full_name in all_methods:
                callees = self.joern_session.get_callees(full_name)
                if callees and isinstance(callees, list):
                    for callee_full in callees:
                        target_id = full_name_to_id.get(callee_full)
                        if target_id is not None:
                            self.graph.add_edge(entity_id, target_id)

            logger.info(
                f"Joern parsing complete: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges extracted."
            )

        except Exception as e:
            logger.error(f"Error parsing repository with Joern: {e}", exc_info=True)

        return self.graph

    # --- Adapter methods to match RepoParser interface ---
    def parse_directory(self, directory: str) -> None:
        """
        Adapter for RepoParser.parse_directory: trigger Joern parse.
        """
        # Joern parsing does not need the directory arg because the CPG
        # already contains the repository snapshot; call parse_repository.
        self.parse_repository()

    def get_graph(self) -> nx.DiGraph:
        """Return the constructed call graph (NetworkX DiGraph)."""
        return self.graph

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Return an Entity-like object for the given entity_id, or None."""
        meta = self.entities.get(entity_id)
        if not meta:
            return None

        # If repo_parser.Entity is available, construct one for compatibility
        if Entity is not None:
            try:
                # Joern doesn't expose lineno info here; use 0 as placeholder
                return Entity(entity_id=meta.get("entity_id", entity_id),
                              entity_type=meta.get("type", "function"),
                              file_path=meta.get("file_path", ""),
                              lineno=0,
                              end_lineno=0,
                              source_code=meta.get("source", ""))
            except Exception:
                pass

        # Fallback: return a simple object with expected attributes
        class _SimpleEntity:
            def __init__(self, eid, etype, fpath, src):
                self.entity_id = eid
                self.entity_type = etype
                self.file_path = fpath
                self.lineno = 0
                self.end_lineno = 0
                self.source_code = src

        return _SimpleEntity(meta.get("entity_id", entity_id),
                             meta.get("type", "function"),
                             meta.get("file_path", ""),
                             meta.get("source", ""))

    def get_all_entities(self) -> List[Any]:
        """Return all entities as a list of Entity-like objects."""
        result = []
        for eid, meta in self.entities.items():
            ent = self.get_entity(eid)
            if ent is not None:
                result.append(ent)
        return result

    def get_entity_source(self, entity_id: str) -> str:
        """Get source code for an entity (fallback to stub)."""
        entity = self.entities.get(entity_id, {})
        return entity.get("source", "")

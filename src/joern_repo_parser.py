"""
Joern-native repository parser.
Constructs NetworkX call graphs and extracts code entities directly from Joern CPG sessions.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Set, Optional
import networkx as nx
from pathlib import Path

# Add src directory to path if needed for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from repo_parser import RepoParser, Entity
except Exception:
    RepoParser = object
    Entity = None

# Add joern_helper to path for session import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "joern_helper"))
try:
    from joern_interactive import JoernSession
except ImportError:
    JoernSession = None

logger = logging.getLogger(__name__)


class JoernRepoParser(RepoParser):
    """
    Parses repository files and constructs a directed Call Graph G=(V, E)
    using a Joern CPG session instead of Python's built-in ast module.
    """

    def __init__(self, repo_path: str, joern_session: Any = None):
        if RepoParser is not object:
            super().__init__(repo_path)
        else:
            self.repo_path = Path(repo_path)
            self.graph = nx.DiGraph()
            self.entities: Dict[str, Dict[str, Any]] = {}
        self.joern_session = joern_session

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
        parsed_entity_count = 0

        try:
            # 1. Bulk-fetch methods from Joern if supported
            methods_data = []
            if hasattr(self.joern_session, "get_all_methods_with_files"):
                methods_data = self.joern_session.get_all_methods_with_files()

            if not methods_data or not isinstance(methods_data, list):
                logger.info("  [JOERN ENTITY STATE] Querying Joern CPG files individually...")
                files = self.joern_session.get_all_files()
                if isinstance(files, list):
                    py_files = [f for f in files if isinstance(f, str) and f.endswith(".py") and not f.startswith("<")]
                    logger.info(f"  [JOERN ENTITY STATE] Found {len(py_files)} Python source files in Joern CPG")
                    for file_path in py_files:
                        logger.info(f"  [JOERN ENTITY STATE] Attempting to parse file: {file_path}")
                        true_names = self.joern_session.get_true_names(file_path)
                        if true_names and isinstance(true_names, list):
                            logger.info(f"  [JOERN ENTITY STATE] Found {len(true_names)} raw method nodes in file {file_path}")
                            for name_tuple in true_names:
                                if isinstance(name_tuple, (list, tuple)) and len(name_tuple) >= 2:
                                    short_name, full_name = str(name_tuple[0]), str(name_tuple[1])
                                    methods_data.append((short_name, full_name, file_path))
                                    logger.info(f"  [JOERN ENTITY FOUND] Found raw method node: short_name={short_name}, full_name={full_name}")
                        else:
                            logger.info(f"  [JOERN ENTITY STATE] No methods extracted for file {file_path}")

            all_methods = []
            for item in methods_data:
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                short_name, full_name, file_path = str(item[0]), str(item[1]), str(item[2])

                # Filter compiler wrappers / internal lambdas
                if full_name.startswith("<") or "<lambda>" in full_name or not file_path.endswith(".py"):
                    logger.info(f"  [JOERN ENTITY SKIPPED] Filtered out compiler wrapper/internal entity: {full_name}")
                    continue

                file_path_clean = file_path.replace("\\", "/")
                try:
                    p = Path(file_path_clean)
                    if p.is_absolute():
                        rel_file_path = str(p.relative_to(self.repo_path)).replace("\\", "/")
                    else:
                        repo_name = self.repo_path.name
                        if repo_name in p.parts:
                            idx = p.parts.index(repo_name)
                            rel_file_path = "/".join(p.parts[idx+1:])
                        else:
                            rel_file_path = str(p).replace("\\", "/")
                except Exception:
                    rel_file_path = file_path_clean.replace("\\", "/")

                # Standardize entity_id to match AST format: file_path::[Class::]func
                clean_name = full_name
                if ":<module>." in full_name:
                    clean_name = full_name.split(":<module>.", 1)[1].replace(".", "::")
                elif ":<module>" in full_name:
                    clean_name = full_name.split(":<module>", 1)[1].strip(".").replace(".", "::")
                
                if not clean_name:
                    clean_name = short_name

                entity_id = f"{rel_file_path}::{clean_name}"

                source_code = f"# Joern parsed entity: {full_name}"
                lineno = 1
                end_lineno = 1
                abs_file_path = self.repo_path / rel_file_path
                if abs_file_path.exists():
                    try:
                        with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            if lines:
                                lineno = 1
                                end_lineno = len(lines)
                                source_code = "".join(lines)
                    except Exception:
                        pass

                entity_type = "method" if "::" in clean_name else "function"

                if Entity is not None:
                    try:
                        entity = Entity(
                            entity_id=entity_id,
                            entity_type=entity_type,
                            file_path=rel_file_path,
                            lineno=lineno,
                            end_lineno=end_lineno,
                            source_code=source_code
                        )
                    except Exception:
                        entity = {
                            "entity_id": entity_id,
                            "name": short_name,
                            "full_name": full_name,
                            "file_path": rel_file_path,
                            "type": entity_type,
                            "source": source_code
                        }
                else:
                    entity = {
                        "entity_id": entity_id,
                        "name": short_name,
                        "full_name": full_name,
                        "file_path": rel_file_path,
                        "type": entity_type,
                        "source": source_code
                    }

                self.entities[entity_id] = entity
                self.graph.add_node(
                    entity_id,
                    name=short_name,
                    file_path=rel_file_path,
                    type=entity_type
                )
                all_methods.append((entity_id, full_name))
                parsed_entity_count += 1
                logger.info(f"  [JOERN ENTITY PARSED SUCCESS] Successfully parsed & indexed entity #{parsed_entity_count}: {entity_id} (type={entity_type}, file={rel_file_path})")

            # 2. Extract call edges from Joern
            full_name_to_id = {full_name: eid for eid, full_name in all_methods}
            call_edges_data = []
            if hasattr(self.joern_session, "get_all_call_edges"):
                call_edges_data = self.joern_session.get_all_call_edges()

            if call_edges_data and isinstance(call_edges_data, list):
                for edge_entry in call_edges_data:
                    if isinstance(edge_entry, (list, tuple)) and len(edge_entry) >= 2:
                        caller_full, callees = str(edge_entry[0]), edge_entry[1]
                        caller_id = full_name_to_id.get(caller_full)
                        if caller_id and isinstance(callees, list):
                            for callee_full in callees:
                                target_id = full_name_to_id.get(str(callee_full))
                                if target_id is not None:
                                    self.graph.add_edge(caller_id, target_id)
                                    logger.info(f"  [JOERN EDGE STATE] Added call edge: {caller_id} -> {target_id}")
            else:
                for entity_id, full_name in all_methods:
                    callees = self.joern_session.get_callees(full_name)
                    if callees and isinstance(callees, list):
                        for callee_full in callees:
                            target_id = full_name_to_id.get(str(callee_full))
                            if target_id is not None:
                                self.graph.add_edge(entity_id, target_id)
                                logger.info(f"  [JOERN EDGE STATE] Added call edge: {entity_id} -> {target_id}")

            logger.info(
                f"[JOERN PARSING COMPLETE] {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges extracted from Joern CPG."
            )
            logger.info(f"[JOERN PARSING SUMMARY] Parsed {parsed_entity_count} Joern entities from {self.repo_path}")

        except Exception as e:
            logger.error(f"Error parsing repository with Joern: {e}", exc_info=True)

        return self.graph

    # --- Adapter methods to match RepoParser interface ---
    def parse_directory(self, directory: Optional[str] = None) -> None:
        if directory:
            self.repo_path = Path(directory)
        self.parse_repository()

    def get_graph(self) -> nx.DiGraph:
        return self.graph

    def get_entity(self, entity_id: str) -> Optional[Any]:
        entity = self.entities.get(entity_id)
        if entity is not None:
            return entity
        return None

    def get_all_entities(self) -> List[Any]:
        return list(self.entities.values())

    def get_entity_source(self, entity_id: str) -> str:
        entity = self.entities.get(entity_id)
        if entity is not None:
            if hasattr(entity, "source_code"):
                return entity.source_code
            if isinstance(entity, dict):
                return entity.get("source", "")
        return ""

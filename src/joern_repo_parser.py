"""
Joern-native repository parser.
Constructs NetworkX call graphs and extracts code entities directly from Joern CPG sessions.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Set, Optional, Tuple
import networkx as nx
from pathlib import Path

# Add joern_helper to path for session import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "joern_helper"))
try:
    from joern_interactive import JoernSession
except ImportError:
    JoernSession = None

# Add src directory to path if needed for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_parser import RepoParser, Entity

logger = logging.getLogger(__name__)


class JoernRepoParser(RepoParser):
    """
    Parses repository files and constructs a directed Call Graph G=(V, E)
    using a Joern CPG session instead of Python's built-in ast module.
    """

    def __init__(self, repo_path: str, joern_session: Any = None):
        super().__init__(repo_path)
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
            # 1. Fetch all methods across the CPG in a single bulk query
            methods_data = []
            if hasattr(self.joern_session, "get_all_methods_with_files"):
                methods_data = self.joern_session.get_all_methods_with_files()

            if not methods_data or not isinstance(methods_data, list):
                logger.warning("No methods returned via bulk query. Trying file fallback...")
                files = self.joern_session.get_all_files()
                if isinstance(files, list):
                    for f_path in files:
                        if isinstance(f_path, str) and f_path.endswith(".py") and not f_path.startswith("<"):
                            tn = self.joern_session.get_true_names(f_path)
                            if isinstance(tn, list):
                                for item in tn:
                                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                                        methods_data.append((item[0], item[1], f_path))

            all_methods = []
            for item in methods_data:
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                short_name, full_name, file_path = str(item[0]), str(item[1]), str(item[2])

                # Filter out compiler wrappers, internal lambdas, or non-Python files
                if full_name.startswith("<") or "<lambda>" in full_name or not file_path.endswith(".py"):
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

                entity = Entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    file_path=rel_file_path,
                    lineno=lineno,
                    end_lineno=end_lineno,
                    source_code=source_code
                )
                self.entities[entity_id] = entity
                self.graph.add_node(
                    entity_id,
                    name=short_name,
                    file_path=rel_file_path,
                    type=entity_type
                )
                all_methods.append((entity_id, full_name))
                parsed_entity_count += 1
                logger.debug(f"Parsed Joern entity: {entity_id}")

            # 2. Extract call edges from Joern (bulk if available)
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
            else:
                for entity_id, full_name in all_methods:
                    callees = self.joern_session.get_callees(full_name)
                    if callees and isinstance(callees, list):
                        for callee_full in callees:
                            target_id = full_name_to_id.get(str(callee_full))
                            if target_id is not None:
                                self.graph.add_edge(entity_id, target_id)

            logger.info(
                f"Joern parsing complete: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges extracted."
            )
            logger.info(f"Parsed {parsed_entity_count} Joern entities from {self.repo_path}")

        except Exception as e:
            logger.error(f"Error parsing repository with Joern: {e}", exc_info=True)

        return self.graph

    def parse_directory(self, directory: Optional[str] = None) -> None:
        """RepoParser-compatible entry point that reparses the current repository snapshot."""
        if directory:
            self.repo_path = Path(directory)
        self.parse_repository()

    def get_entity_source(self, entity_id: str) -> str:
        """Get source code for an entity."""
        entity = self.entities.get(entity_id)
        if entity and hasattr(entity, 'source_code'):
            return entity.source_code
        return ""

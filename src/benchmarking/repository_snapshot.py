"""Build repository snapshots from a specific git commit without checking out the tree."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from parser.git_helper import GitHelper
except ImportError:
    try:
        from src.parser.git_helper import GitHelper
    except ImportError:
        from ..parser.git_helper import GitHelper

from .types import RepositoryEntity, RepositorySnapshot


def _list_python_files_at_commit(git_helper: GitHelper, commit_hash: str) -> List[str]:
    output = git_helper._run_git_command(["ls-tree", "-r", "--name-only", commit_hash])
    return [line.strip() for line in output.splitlines() if line.strip() and line.strip().endswith(".py")]


def _extract_source(node: ast.AST, source_lines: List[str]) -> str:
    start = node.lineno - 1
    end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start + 1
    return "\n".join(source_lines[start:end])


def _get_entity_id(file_path: str, class_name: Optional[str], func_name: str) -> str:
    return f"{file_path}::{class_name}::{func_name}" if class_name else f"{file_path}::{func_name}"


def _parse_entities(file_path: str, source: str) -> List[RepositoryEntity]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    source_lines = source.splitlines()
    entities: List[RepositoryEntity] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_id = _get_entity_id(file_path, None, node.name)
            entities.append(
                RepositoryEntity(
                    entity_id=class_id,
                    entity_type="class",
                    file_path=file_path,
                    lineno=node.lineno,
                    end_lineno=getattr(node, "end_lineno", node.lineno),
                    name=node.name,
                    source_code=_extract_source(node, source_lines),
                )
            )
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_id = _get_entity_id(file_path, node.name, item.name)
                    entities.append(
                        RepositoryEntity(
                            entity_id=method_id,
                            entity_type="method",
                            file_path=file_path,
                            lineno=item.lineno,
                            end_lineno=getattr(item, "end_lineno", item.lineno),
                            name=item.name,
                            source_code=_extract_source(item, source_lines),
                        )
                    )
        elif isinstance(node, ast.FunctionDef):
            is_method = any(
                isinstance(parent, ast.ClassDef) and node in parent.body
                for parent in ast.walk(tree)
            )
            if not is_method:
                func_id = _get_entity_id(file_path, None, node.name)
                entities.append(
                    RepositoryEntity(
                        entity_id=func_id,
                        entity_type="function",
                        file_path=file_path,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", node.lineno),
                        name=node.name,
                        source_code=_extract_source(node, source_lines),
                    )
                )

    return entities


def _parse_entities_tree_sitter(file_path: str, source: str, language_name: str = "python") -> List[RepositoryEntity]:
    try:
        import tree_sitter_languages  # lazy import — optional dependency
        parser = tree_sitter_languages.get_parser(language_name)
        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
    except Exception:
        # tree_sitter_languages not installed or parse failed — fall back to AST parser
        return _parse_entities(file_path, source)

    entities: List[RepositoryEntity] = []

    def _traverse(node: Any, current_class: Optional[str] = None) -> None:
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            class_name = name_node.text.decode("utf-8", errors="ignore") if name_node else "UnknownClass"
            class_id = _get_entity_id(file_path, None, class_name)
            snippet = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            entities.append(
                RepositoryEntity(
                    entity_id=class_id,
                    entity_type="class",
                    file_path=file_path,
                    lineno=node.start_point[0] + 1,
                    end_lineno=node.end_point[0] + 1,
                    name=class_name,
                    source_code=snippet,
                )
            )
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    _traverse(child, current_class=class_name)

        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            func_name = name_node.text.decode("utf-8", errors="ignore") if name_node else "unknown_func"
            entity_type = "method" if current_class else "function"
            entity_id = _get_entity_id(file_path, current_class, func_name)
            snippet = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            entities.append(
                RepositoryEntity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    file_path=file_path,
                    lineno=node.start_point[0] + 1,
                    end_lineno=node.end_point[0] + 1,
                    name=func_name,
                    source_code=snippet,
                )
            )
        else:
            for child in node.children:
                if child.type not in ("class_definition", "function_definition"):
                    _traverse(child, current_class=current_class)

    _traverse(tree.root_node, current_class=None)
    return entities


def _build_call_graph(entities: Dict[str, RepositoryEntity]) -> Any:
    """
    Phase 1.2: Build a lightweight call graph (nx.DiGraph) from entity source code.

    Edges: caller_entity_id -> callee_entity_id
    Uses simple name-matching: if any other entity's short name appears as a token
    in the source code of an entity, we add a call edge.

    This is a heuristic (not full AST call analysis) but sufficient for fixed_hop
    propagation and caller-perspective query generation.
    """
    try:
        import networkx as nx
    except ImportError:
        return None

    graph = nx.DiGraph()

    # Add all entity nodes
    for entity_id in entities:
        graph.add_node(entity_id)

    # Build name -> entity_id lookup for fast matching
    name_to_ids: Dict[str, List[str]] = {}
    for entity_id, entity in entities.items():
        name_to_ids.setdefault(entity.name, []).append(entity_id)

    # For each entity, scan its source for calls to other entities
    import re
    for entity_id, entity in entities.items():
        source = entity.source_code
        for callee_name, callee_ids in name_to_ids.items():
            if callee_name == entity.name:
                continue  # skip self-reference
            # Look for callee_name( pattern — simple call site detection
            if re.search(r'\b' + re.escape(callee_name) + r'\s*\(', source):
                for callee_id in callee_ids:
                    if callee_id != entity_id:
                        graph.add_edge(entity_id, callee_id)

    return graph


def build_repository_snapshot(
    git_helper: GitHelper,
    commit_hash: str,
    parser_mode: str = "tree_sitter",
    joern_session: Any = None,  # kept for backward-compat; unused
) -> RepositorySnapshot:
    """
    Build a RepositorySnapshot for a given commit.

    Phase 1.2: Also builds and attaches a call graph (graph) and a lightweight
    parser-like object (parser) to the snapshot. These are used by:
        - build_queries() for caller-perspective synthetic query generation
        - decide_updated_entities() for fixed_hop propagation
    """
    entities: Dict[str, RepositoryEntity] = {}
    for file_path in _list_python_files_at_commit(git_helper, commit_hash):
        file_source = git_helper.get_file_content_at_commit(commit_hash, file_path)
        if not file_source:
            continue
        if parser_mode == "tree_sitter":
            parsed = _parse_entities_tree_sitter(file_path, file_source)
        else:
            parsed = _parse_entities(file_path, file_source)

        for entity in parsed:
            entities[entity.entity_id] = entity

    # Phase 1.2: build call graph and wrap in a SnapshotParser for fixed_hop
    graph = _build_call_graph(entities)
    snapshot_parser = SnapshotParser(graph) if graph is not None else None

    return RepositorySnapshot(
        commit_hash=commit_hash,
        entities=entities,
        graph=graph,
        parser=snapshot_parser,
    )


class SnapshotParser:
    """
    Phase 1.2: Lightweight parser wrapper stored on RepositorySnapshot.

    Provides get_dependents(entity_id, max_hops) for fixed_hop propagation
    in strategy_runner.py, backed by the call graph built at snapshot time.
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    def get_dependents(self, entity_id: str, max_hops: int = 2) -> List[str]:
        """
        Return all entities that (transitively) depend on entity_id up to max_hops.

        In the call graph, an edge A->B means A calls B. A "dependent" of B is
        any entity that calls B (directly or transitively) — i.e., predecessors
        in the graph. We walk predecessor edges up to max_hops levels.
        """
        if self._graph is None or entity_id not in self._graph:
            return []

        visited: set = set()
        frontier = {entity_id}

        for _ in range(max_hops):
            next_frontier: set = set()
            for node in frontier:
                try:
                    for pred in self._graph.predecessors(node):
                        if pred not in visited and pred != entity_id:
                            next_frontier.add(pred)
                except Exception:
                    pass
            visited.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break

        return list(visited)

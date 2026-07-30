"""Build repository snapshots from a specific git commit without checking out the tree."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..git_helper import GitHelper

from src.benchmarking.types import RepositoryEntity, RepositorySnapshot


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
            is_method = any(isinstance(parent, ast.ClassDef) and node in parent.body for parent in ast.walk(tree))
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


def build_repository_snapshot(
    git_helper: GitHelper,
    commit_hash: str,
    parser_mode: str = "ast",
    joern_session: Optional[object] = None,
) -> RepositorySnapshot:
    if parser_mode == "joern_only" and joern_session is not None:
        # Checkout commit to disk so Joern can parse the files
        git_helper.checkout_commit(commit_hash)

        # Re-parse directory to update CPG in Joern session
        if hasattr(joern_session, "_build_cpg") and hasattr(joern_session, "_import_cpg"):
            try:
                joern_session.cpg_path = joern_session._build_cpg()
                joern_session._import_cpg()
            except Exception as e:
                import logging
                logging.getLogger("benchmarking").warning(f"Failed to re-import CPG in Joern: {e}")

        entities: Dict[str, RepositoryEntity] = {}
        try:
            files = joern_session.get_all_files()
            if files:
                py_files = [f for f in files if isinstance(f, str) and (f.endswith(".py") or not f.startswith("<"))]
                for file_path in py_files:
                    true_names = joern_session.get_true_names(file_path)
                    if true_names:
                        for name_tuple in true_names:
                            if isinstance(name_tuple, (list, tuple)) and len(name_tuple) >= 2:
                                short_name, full_name = name_tuple[0], name_tuple[1]
                                if full_name.startswith("<") or "<lambda>" in full_name:
                                    continue
                                entity_id = f"{file_path}::{full_name}"
                                entities[entity_id] = RepositoryEntity(
                                    entity_id=entity_id,
                                    entity_type="function",
                                    file_path=file_path,
                                    lineno=1,
                                    end_lineno=1,
                                    name=short_name,
                                    source_code=f"# Joern parsed entity: {full_name}"
                                )
        except Exception as e:
            import logging
            logging.getLogger("benchmarking").error(f"Error querying Joern snapshot: {e}")

        return RepositorySnapshot(commit_hash=commit_hash, entities=entities)

    entities: Dict[str, RepositoryEntity] = {}
    for file_path in _list_python_files_at_commit(git_helper, commit_hash):
        file_source = git_helper.get_file_content_at_commit(commit_hash, file_path)
        if not file_source:
            continue
        for entity in _parse_entities(file_path, file_source):
            entities[entity.entity_id] = entity
    return RepositorySnapshot(commit_hash=commit_hash, entities=entities)

"""Shared definition of "semantically modified entity" between two commits.

Used by both Pipeline A training (run_experiment.py / notebooks) and Pipeline B
inference (src/benchmarking/model_runner.py), so the ``is_modified`` /
distance-to-modified features mean the same thing at train and serve time.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Iterable, Optional, Set

_CANONICALIZE_EXEMPT_NAMES = {"self", "cls"}


class _LocalNameCollector(ast.NodeVisitor):
    """Collects local bindings (assignment targets and function parameters)
    in first-appearance order, so they can be alpha-renamed to canonical
    placeholders before comparing two versions of an entity's source.

    Deliberately does NOT touch call targets, attribute access, imports, or
    string/docstring literals — only names bound as locals or parameters.
    """

    def __init__(self):
        self.order: list = []
        self._seen: set = set()

    def _register(self, name: str) -> None:
        if name in _CANONICALIZE_EXEMPT_NAMES or name in self._seen:
            return
        self._seen.add(name)
        self.order.append(name)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self._register(node.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        self._register(node.arg)
        self.generic_visit(node)


class _LocalNameRenamer(ast.NodeTransformer):
    """Renames local-binding Name/arg nodes per a precomputed mapping."""

    def __init__(self, mapping: dict):
        self.mapping = mapping

    def visit_Name(self, node):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node

    def visit_arg(self, node):
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        return node


def _canonicalize_local_names(tree):
    collector = _LocalNameCollector()
    collector.visit(tree)
    mapping = {name: f"_v{i}" for i, name in enumerate(collector.order)}
    return _LocalNameRenamer(mapping).visit(tree)


def normalize_source(code: str) -> str:
    """AST-canonicalize source so cosmetic diffs and local renames compare equal."""
    try:
        tree = ast.parse(code)
        tree = _canonicalize_local_names(tree)
        return ast.dump(tree, annotate_fields=False)
    except Exception:
        # Language-agnostic fallback: strip comments and collapse whitespace
        code_clean = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code_clean = re.sub(r'//.*', '', code_clean)
        code_clean = re.sub(r'#.*', '', code_clean)
        return " ".join(code_clean.split())


def compute_semantic_modified_entities(
    parser_prev: Optional[Any],
    parser_curr: Any,
    modified_files: Iterable[str],
    entity_ids: Optional[Iterable[str]] = None,
) -> Set[str]:
    """Entities of ``parser_curr`` that semantically changed since ``parser_prev``.

    An entity counts as modified when its file appears in ``modified_files`` AND
    it is new (absent from ``parser_prev``) or its normalized source differs.

    Args:
        parser_prev: Parser at the earlier commit (None -> every candidate counts as modified).
        parser_curr: Parser at the later commit.
        modified_files: Files changed between the two commits (git diff --name-only).
        entity_ids: Optional restriction of the candidate entity set.
    """
    modified_files = set(modified_files)
    allowed = set(entity_ids) if entity_ids is not None else None

    modified: Set[str] = set()
    for entity in parser_curr.get_all_entities():
        if entity.file_path not in modified_files:
            continue
        if allowed is not None and entity.entity_id not in allowed:
            continue
        prev_entity = parser_prev.entities.get(entity.entity_id) if parser_prev else None
        if prev_entity is None:
            modified.add(entity.entity_id)
        elif normalize_source(prev_entity.source_code) != normalize_source(entity.source_code):
            modified.add(entity.entity_id)
    return modified


def compute_source_changed_entities(
    parser_prev: Optional[Any],
    parser_curr: Any,
    modified_files: Iterable[str],
    entity_ids: Optional[Iterable[str]] = None,
) -> Set[str]:
    """Entities of ``parser_curr`` whose own source text changed since ``parser_prev``.

    This is the cache-invalidation notion of "changed" used by the benchmark: the
    entity's embedded text changed (new entity, or any edit to its source —
    including comments, which are embedded). Entities that merely share a file
    with an edit are NOT changed. Contrast compute_semantic_modified_entities(),
    the model's is_modified feature, which also ignores cosmetic edits.
    """
    modified_files = set(modified_files)
    allowed = set(entity_ids) if entity_ids is not None else None

    changed: Set[str] = set()
    for entity in parser_curr.get_all_entities():
        if entity.file_path not in modified_files:
            continue
        if allowed is not None and entity.entity_id not in allowed:
            continue
        prev_entity = parser_prev.entities.get(entity.entity_id) if parser_prev else None
        if prev_entity is None or prev_entity.source_code != entity.source_code:
            changed.add(entity.entity_id)
    return changed

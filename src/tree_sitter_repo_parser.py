"""Tree-sitter based Python repository parser and dependency graph builder."""

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import networkx as nx
import logging
import tree_sitter_languages

try:
    from src.repo_parser import Entity
except ImportError:
    from repo_parser import Entity

logger = logging.getLogger(__name__)


class TreeSitterRepoParser:
    """Parses Python source files using Tree-sitter and builds dependency graph."""

    def __init__(self, repo_path: str, language: str = 'python'):
        """
        Initialize repository parser.

        Args:
            repo_path: Path to the repository root
            language: Programming language to parse ('python')
        """
        self.repo_path = Path(repo_path).resolve()
        self.language_name = language.lower()
        self.parser = tree_sitter_languages.get_parser(self.language_name)
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Entity] = {}
        self.symbol_table: Dict[str, Dict[str, str]] = {}  # RelPath -> {ImportName: Target}

    def _get_entity_id(self, file_path: str, class_name: Optional[str],
                       func_name: str) -> str:
        """Generate unique entity ID."""
        if class_name:
            return f"{file_path}::{class_name}::{func_name}"
        else:
            return f"{file_path}::{func_name}"

    def _get_relative_path(self, absolute_path: str) -> str:
        """Convert absolute path to relative path from repo root."""
        return str(Path(absolute_path).relative_to(self.repo_path)).replace("\\", "/")

    def _analyze_tree_sitter_metrics(self, node) -> Dict[str, float]:
        """Extract Python code complexity metrics directly from Tree-sitter node."""
        decision_types = {
            'if_statement', 'for_statement', 'while_statement',
            'except_clause', 'boolean_operator', 'conditional_expression',
            'case_clause'
        }
        nesting_types = {
            'if_statement', 'for_statement', 'while_statement',
            'try_statement', 'with_statement'
        }

        branch_count = 0
        node_count = 0
        max_depth = 0
        return_count = 0

        def walk(n, current_depth):
            nonlocal branch_count, node_count, max_depth, return_count
            node_count += 1

            if n.type in decision_types:
                branch_count += 1
                if n.type == 'if_statement':
                    for c in n.children:
                        if c.type == 'elif_clause':
                            branch_count += 1

            if n.type == 'return_statement':
                return_count += 1

            next_depth = current_depth + 1 if n.type in nesting_types else current_depth
            max_depth = max(max_depth, current_depth)

            for c in n.children:
                walk(c, next_depth)

        walk(node, 0)

        params_node = node.child_by_field_name('parameters')
        param_count = len(params_node.children) if params_node else 0.0

        return {
            'cyclomatic_complexity': float(1 + branch_count),
            'ast_node_count': float(node_count),
            'max_nesting_depth': float(max_depth),
            'param_count': float(param_count),
            'return_count': float(return_count)
        }

    def _build_symbol_table(self, root_node, file_path: str,
                             source_bytes: bytes) -> Dict[str, str]:
        """Build symbol table for imports in a file using Tree-sitter."""
        symbol_table = {}

        def _traverse_imports(node):
            if node.type in ('import_statement', 'import_from_statement'):
                if node.type == 'import_statement':
                    for child in node.children:
                        if child.type in ('dotted_name', 'aliased_import'):
                            text = child.text.decode('utf-8', errors='ignore')
                            if ' as ' in text:
                                orig, alias = text.split(' as ')
                                symbol_table[alias.strip()] = f"import:{orig.strip()}"
                            else:
                                symbol_table[text.strip()] = f"import:{text.strip()}"

                elif node.type == 'import_from_statement':
                    module_name = ""
                    module_node = node.child_by_field_name('module_name')
                    if module_node:
                        module_name = module_node.text.decode('utf-8', errors='ignore')

                    for child in node.children:
                        if child.type == 'dotted_name' and child != module_node:
                            alias = child.text.decode('utf-8', errors='ignore')
                            full = f"{module_name}.{alias}" if module_name else alias
                            symbol_table[alias] = f"import:{full}"
                        elif child.type == 'aliased_import':
                            text = child.text.decode('utf-8', errors='ignore')
                            if ' as ' in text:
                                orig, alias = text.split(' as ')
                                full = f"{module_name}.{orig.strip()}" if module_name else orig.strip()
                                symbol_table[alias.strip()] = f"import:{full}"

            for child in node.children:
                _traverse_imports(child)

        _traverse_imports(root_node)
        return symbol_table

    def _parse_file(self, file_path: str) -> Tuple[List[Entity], Dict[str, str]]:
        """Parse a Python source file using Tree-sitter and extract entities."""
        try:
            with open(file_path, 'rb') as f:
                source_bytes = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return [], {}

        try:
            tree = self.parser.parse(source_bytes)
        except Exception as e:
            logger.error(f"Tree-sitter parse error in {file_path}: {e}")
            return [], {}

        rel_path = self._get_relative_path(file_path)
        entities = []
        symbol_table = self._build_symbol_table(tree.root_node, rel_path, source_bytes)

        def _traverse_nodes(node, current_class: Optional[str] = None):
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                class_name = name_node.text.decode('utf-8', errors='ignore') if name_node else "UnknownClass"
                class_id = self._get_entity_id(rel_path, None, class_name)

                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                code_snippet = source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
                ts_metrics = self._analyze_tree_sitter_metrics(node)

                class_entity = Entity(
                    entity_id=class_id,
                    entity_type="class",
                    file_path=rel_path,
                    lineno=start_line,
                    end_lineno=end_line,
                    source_code=code_snippet,
                    cyclomatic_complexity=ts_metrics['cyclomatic_complexity'],
                    ast_node_count=ts_metrics['ast_node_count'],
                    max_nesting_depth=ts_metrics['max_nesting_depth'],
                    param_count=ts_metrics['param_count'],
                    return_count=ts_metrics['return_count']
                )
                entities.append(class_entity)

                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        _traverse_nodes(child, current_class=class_name)

            elif node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                func_name = name_node.text.decode('utf-8', errors='ignore') if name_node else "unknown_func"

                entity_type = "method" if current_class else "function"
                entity_id = self._get_entity_id(rel_path, current_class, func_name)

                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                code_snippet = source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
                ts_metrics = self._analyze_tree_sitter_metrics(node)

                func_entity = Entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    file_path=rel_path,
                    lineno=start_line,
                    end_lineno=end_line,
                    source_code=code_snippet,
                    cyclomatic_complexity=ts_metrics['cyclomatic_complexity'],
                    ast_node_count=ts_metrics['ast_node_count'],
                    max_nesting_depth=ts_metrics['max_nesting_depth'],
                    param_count=ts_metrics['param_count'],
                    return_count=ts_metrics['return_count']
                )
                entities.append(func_entity)

            else:
                for child in node.children:
                    _traverse_nodes(child, current_class=current_class)

        _traverse_nodes(tree.root_node, current_class=None)
        return entities, symbol_table

    def _resolve_external_import(self, import_str: str, local_entities: Dict[str, Entity]) -> Optional[str]:
        """Resolve import string to local entity ID if it exists."""
        if not import_str.startswith("import:"):
            return None

        parts = import_str[len("import:"):].split(".")
        if not parts:
            return None

        for i in range(len(parts), 0, -1):
            module_parts = parts[:i]
            entity_parts = parts[i:]

            possible_paths = [
                "/".join(module_parts) + ".py",
                "src/" + "/".join(module_parts) + ".py"
            ]

            for rel_path in possible_paths:
                rel_path = rel_path.replace("\\", "/")

                file_entities = [
                    ent for ent in local_entities.values()
                    if ent.file_path == rel_path
                ]

                if file_entities:
                    if not entity_parts:
                        return None

                    if len(entity_parts) == 1:
                        ent_id = f"{rel_path}::{entity_parts[0]}"
                        if ent_id in local_entities:
                            return ent_id
                    elif len(entity_parts) == 2:
                        ent_id = f"{rel_path}::{entity_parts[0]}::{entity_parts[1]}"
                        if ent_id in local_entities:
                            return ent_id

        return None

    def _resolve_call_target(self, call_name: str, local_entities: Dict[str, Entity],
                             symbol_table: Dict[str, str]) -> Optional[str]:
        """Resolve function/method call target name to entity ID."""
        if not call_name:
            return None

        if call_name in local_entities:
            return local_entities[call_name].entity_id

        for entity_id, entity in local_entities.items():
            if entity.entity_type in ["method", "function"]:
                if entity_id.endswith(f"::{call_name}"):
                    return entity_id

        if call_name in symbol_table:
            resolved = self._resolve_external_import(symbol_table[call_name], local_entities)
            if resolved:
                return resolved

        return None

    def _extract_edges(self, root_node, file_path: str,
                       local_entities: Dict[str, Entity],
                       symbol_table: Dict[str, str],
                       source_bytes: bytes) -> List[Tuple[str, str]]:
        """Extract caller -> callee dependency edges using Tree-sitter AST nodes."""
        edges = []

        def _scan_calls_and_definitions(node, current_entity_id: Optional[str] = None):
            nonlocal edges
            active_id = current_entity_id

            if node.type in ('function_definition', 'class_definition'):
                name_node = node.child_by_field_name('name')
                name = name_node.text.decode('utf-8', errors='ignore') if name_node else ""
                
                if node.type == 'function_definition':
                    matching_ids = [
                        eid for eid in local_entities.keys()
                        if eid.startswith(file_path) and eid.endswith(f"::{name}")
                    ]
                    if matching_ids:
                        active_id = matching_ids[0]
                elif node.type == 'class_definition':
                    active_id = f"{file_path}::{name}"

            elif node.type == 'call' and active_id:
                func_node = node.child_by_field_name('function')
                if func_node:
                    call_text = func_node.text.decode('utf-8', errors='ignore')
                    call_name = call_text.split('.')[-1]
                    callee_id = self._resolve_call_target(call_name, local_entities, symbol_table)
                    if callee_id and callee_id in local_entities and callee_id != active_id:
                        edges.append((active_id, callee_id))

            for child in node.children:
                _scan_calls_and_definitions(child, current_entity_id=active_id)

        _scan_calls_and_definitions(root_node, current_entity_id=None)
        return edges

    def parse_file(self, file_path: str) -> None:
        """Parse a single file and add entities/edges to graph."""
        if not file_path.endswith('.py'):
            return

        entities, symbol_table = self._parse_file(file_path)

        for entity in entities:
            self.entities[entity.entity_id] = entity
            self.graph.add_node(entity.entity_id, **{
                'type': entity.entity_type,
                'file_path': entity.file_path,
                'lineno': entity.lineno,
                'end_lineno': entity.end_lineno,
                'source_code': entity.source_code
            })

        rel_path = self._get_relative_path(file_path)
        self.symbol_table[rel_path] = symbol_table

        try:
            with open(file_path, 'rb') as f:
                source_bytes = f.read()
            tree = self.parser.parse(source_bytes)
            edges = self._extract_edges(tree.root_node, rel_path, self.entities, symbol_table, source_bytes)

            for caller_id, callee_id in edges:
                self.graph.add_edge(caller_id, callee_id, type='calls')

        except Exception as e:
            logger.error(f"Failed to extract edges from {file_path}: {e}")

    def parse_directory(self, directory: str) -> None:
        """Parse all Python files in a directory using two-pass resolution."""
        dir_path = Path(directory).resolve()
        py_files = []
        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test" in str(py_file).lower():
                continue
            py_files.append(str(py_file.resolve()))

        # Pass 1: Parse entities and symbol tables
        for py_file in py_files:
            entities, symbol_table = self._parse_file(py_file)

            for entity in entities:
                self.entities[entity.entity_id] = entity
                self.graph.add_node(entity.entity_id, **{
                    'type': entity.entity_type,
                    'file_path': entity.file_path,
                    'lineno': entity.lineno,
                    'end_lineno': entity.end_lineno,
                    'source_code': entity.source_code
                })

            rel_path = self._get_relative_path(py_file)
            self.symbol_table[rel_path] = symbol_table

        # Pass 2: Extract dependency edges
        for py_file in py_files:
            rel_path = self._get_relative_path(py_file)
            symbol_table = self.symbol_table.get(rel_path, {})
            try:
                with open(py_file, 'rb') as f:
                    source_bytes = f.read()
                tree = self.parser.parse(source_bytes)
                edges = self._extract_edges(tree.root_node, rel_path, self.entities, symbol_table, source_bytes)

                for caller_id, callee_id in edges:
                    self.graph.add_edge(caller_id, callee_id, type='calls')

            except Exception as e:
                logger.error(f"Failed to extract edges from {py_file}: {e}")

    def remove_file(self, file_path: str) -> None:
        """Remove entities and edges for a deleted file."""
        entities_to_remove = [
            entity_id for entity_id, entity in self.entities.items()
            if entity.file_path == file_path
        ]

        for entity_id in entities_to_remove:
            if entity_id in self.graph:
                self.graph.remove_node(entity_id)
            if entity_id in self.entities:
                del self.entities[entity_id]

        if file_path in self.symbol_table:
            del self.symbol_table[file_path]

    def update_file(self, file_path: str) -> None:
        """Update entities and edges for a modified file."""
        self.remove_file(file_path)
        absolute_path = self.repo_path / file_path
        if absolute_path.exists():
            self.parse_file(str(absolute_path))

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_all_entities(self) -> List[Entity]:
        """Get list of all entities."""
        return list(self.entities.values())

    def get_code_metrics(self, entity_id: str) -> Dict[str, float]:
        """Get Tree-sitter extracted Python code complexity metrics for an entity."""
        entity = self.get_entity(entity_id)
        if not entity:
            return {
                "cyclomatic_complexity": 1.0,
                "ast_node_count": 0.0,
                "max_nesting_depth": 0.0,
                "param_count": 0.0,
                "return_count": 0.0
            }
        return {
            "cyclomatic_complexity": entity.cyclomatic_complexity,
            "ast_node_count": entity.ast_node_count,
            "max_nesting_depth": entity.max_nesting_depth,
            "param_count": entity.param_count,
            "return_count": entity.return_count
        }

    def get_graph(self) -> nx.DiGraph:
        """Get NetworkX directed dependency graph."""
        return self.graph

    def get_undirected_graph(self) -> nx.Graph:
        """Get NetworkX undirected graph."""
        return self.graph.to_undirected()

    def get_dependents(self, entity_id: str, max_hops: Optional[int] = None) -> Set[str]:
        """Get all dependent entity IDs downstream."""
        if entity_id not in self.graph:
            return set()

        reverse_graph = self.graph.reverse()
        if max_hops is None:
            return nx.descendants(reverse_graph, entity_id)
        else:
            return set(nx.dfs_preorder_nodes(reverse_graph, entity_id, depth_limit=max_hops))

    def get_dependencies(self, entity_id: str, max_hops: Optional[int] = None) -> Set[str]:
        """Get all dependency entity IDs upstream."""
        if entity_id not in self.graph:
            return set()

        if max_hops is None:
            return nx.descendants(self.graph, entity_id)
        else:
            return set(nx.dfs_preorder_nodes(self.graph, entity_id, depth_limit=max_hops))

    def get_shortest_path_distance(self, source: str, target: str) -> Optional[int]:
        """Get shortest path distance between two entities."""
        try:
            return nx.shortest_path_length(self.graph, source, target)
        except nx.NetworkXNoPath:
            return None

    def get_nearest_modified_distance(self, entity_id: str,
                                       modified_entities: Set[str]) -> Optional[int]:
        """Get shortest distance to nearest modified entity."""
        if entity_id in modified_entities:
            return 0

        distances = []
        undirected_graph = self.get_undirected_graph()

        for modified_id in modified_entities:
            if modified_id in undirected_graph and entity_id in undirected_graph:
                try:
                    dist = nx.shortest_path_length(undirected_graph, entity_id, modified_id)
                    distances.append(dist)
                except nx.NetworkXNoPath:
                    continue

        return min(distances) if distances else None

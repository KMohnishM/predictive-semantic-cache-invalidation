"""AST parser and dependency graph builder."""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import networkx as nx
import logging

logger = logging.getLogger(__name__)


class Entity:
    """Represents a code entity (function, method, or class)."""

    def __init__(self, entity_id: str, entity_type: str, file_path: str,
                 lineno: int, end_lineno: int, source_code: str):
        """
        Initialize an entity.

        Args:
            entity_id: Unique identifier (e.g., "path::class::method")
            entity_type: Type of entity ("function", "method", "class")
            file_path: Path to the file containing this entity
            lineno: Starting line number
            end_lineno: Ending line number
            source_code: Source code of the entity
        """
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.file_path = file_path
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.source_code = source_code

    def __repr__(self):
        return f"Entity({self.entity_id}, {self.entity_type})"


class RepoParser:
    """Parses Python files and builds dependency graph."""

    def __init__(self, repo_path: str):
        """
        Initialize repository parser.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path).resolve()
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Entity] = {}
        self.symbol_table: Dict[str, str] = {}  # Maps imported names to entity IDs

    def _get_entity_id(self, file_path: str, class_name: Optional[str],
                       func_name: str) -> str:
        """
        Generate unique entity ID.

        Args:
            file_path: Relative file path
            class_name: Class name (None for module-level functions)
            func_name: Function/method name

        Returns:
            Unique entity identifier
        """
        if class_name:
            return f"{file_path}::{class_name}::{func_name}"
        else:
            return f"{file_path}::{func_name}"

    def _get_relative_path(self, absolute_path: str) -> str:
        """
        Convert absolute path to relative path from repo root.

        Args:
            absolute_path: Absolute file path

        Returns:
            Relative path from repo root
        """
        return str(Path(absolute_path).relative_to(self.repo_path)).replace("\\", "/")

    def _extract_source(self, node: ast.AST, source_lines: List[str]) -> str:
        """
        Extract source code from AST node.

        Args:
            node: AST node
            source_lines: List of source code lines

        Returns:
            Source code string
        """
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start + 1
        return "\n".join(source_lines[start:end])

    def _build_symbol_table(self, tree: ast.AST, file_path: str,
                            source_lines: List[str]) -> Dict[str, str]:
        """
        Build symbol table for imports in a file.

        Args:
            tree: AST tree
            file_path: Relative file path
            source_lines: Source code lines

        Returns:
            Dictionary mapping imported names to their origins
        """
        symbol_table = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    symbol_table[name] = f"import:{alias.name}"

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    symbol_table[name] = f"import:{full_name}"

        return symbol_table

    def _parse_file(self, file_path: str) -> Tuple[List[Entity], Dict[str, str]]:
        """
        Parse a Python file and extract entities.

        Args:
            file_path: Absolute path to Python file

        Returns:
            Tuple of (list of entities, symbol table)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return [], {}

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return [], {}

        source_lines = source.split('\n')
        rel_path = self._get_relative_path(file_path)
        entities = []
        symbol_table = self._build_symbol_table(tree, rel_path, source_lines)

        # First pass: collect all class and function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Create class entity
                class_id = self._get_entity_id(rel_path, None, node.name)
                class_source = self._extract_source(node, source_lines)
                class_entity = Entity(
                    entity_id=class_id,
                    entity_type="class",
                    file_path=rel_path,
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                    source_code=class_source
                )
                entities.append(class_entity)

                # Create method entities
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_id = self._get_entity_id(rel_path, node.name, item.name)
                        method_source = self._extract_source(item, source_lines)
                        method_entity = Entity(
                            entity_id=method_id,
                            entity_type="method",
                            file_path=rel_path,
                            lineno=item.lineno,
                            end_lineno=item.end_lineno,
                            source_code=method_source
                        )
                        entities.append(method_entity)

            elif isinstance(node, ast.FunctionDef):
                # Module-level function
                # Check if it's not inside a class (already handled above)
                parent = None
                for parent_node in ast.walk(tree):
                    if isinstance(parent_node, ast.ClassDef):
                        if node in parent_node.body:
                            parent = parent_node
                            break

                if parent is None:
                    func_id = self._get_entity_id(rel_path, None, node.name)
                    func_source = self._extract_source(node, source_lines)
                    func_entity = Entity(
                        entity_id=func_id,
                        entity_type="function",
                        file_path=rel_path,
                        lineno=node.lineno,
                        end_lineno=node.end_lineno,
                        source_code=func_source
                    )
                    entities.append(func_entity)

        return entities, symbol_table

    def _resolve_external_import(self, import_str: str, local_entities: Dict[str, Entity]) -> Optional[str]:
        """
        Resolve an import string like 'import:black.parsing.parse_ast'
        to a local entity ID if it exists in the repository.
        """
        if not import_str.startswith("import:"):
            return None

        parts = import_str[len("import:"):].split(".")
        if not parts:
            return None

        # Try different module prefixes to match file paths
        for i in range(len(parts), 0, -1):
            module_parts = parts[:i]
            entity_parts = parts[i:]

            # Try possible relative paths
            possible_paths = [
                "/".join(module_parts) + ".py",
                "src/" + "/".join(module_parts) + ".py"
            ]

            for rel_path in possible_paths:
                rel_path = rel_path.replace("\\", "/")

                # Check if this file exists in parsed entities
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

    def _resolve_call_target(self, call_node: ast.Call, local_entities: Dict[str, Entity],
                             symbol_table: Dict[str, str]) -> Optional[str]:
        """
        Resolve a function call to an entity ID.

        Args:
            call_node: AST Call node
            local_entities: Dictionary of local entities
            symbol_table: Symbol table for imports

        Returns:
            Entity ID if resolved, None otherwise
        """
        # Get the function being called
        func = call_node.func

        # Handle different call patterns
        if isinstance(func, ast.Name):
            # Direct call: func_name()
            name = func.id
            if name in local_entities:
                return local_entities[name].entity_id
            # Check if it's an imported function
            if name in symbol_table:
                resolved = self._resolve_external_import(symbol_table[name], local_entities)
                if resolved:
                    return resolved
            return None

        elif isinstance(func, ast.Attribute):
            # Method call: obj.method() or module.func()
            parts = []
            current = func
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.insert(0, current.id)

            if not parts:
                return None

            # Check if it's a local method call
            if len(parts) >= 2:
                method_name = parts[-1]
                for entity_id, entity in local_entities.items():
                    if entity.entity_type in ["method", "function"]:
                        if entity_id.endswith(f"::{method_name}"):
                            return entity_id

            # Check symbol table
            if parts[0] in symbol_table:
                import_val = symbol_table[parts[0]]
                full_import = f"{import_val}.{'.'.join(parts[1:])}"
                resolved = self._resolve_external_import(full_import, local_entities)
                if resolved:
                    return resolved

        return None

    def _extract_edges(self, tree: ast.AST, file_path: str,
                       local_entities: Dict[str, Entity],
                       symbol_table: Dict[str, str]) -> List[Tuple[str, str]]:
        """
        Extract dependency edges from AST.

        Args:
            tree: AST tree
            file_path: Relative file path
            local_entities: Dictionary of local entities
            symbol_table: Symbol table for imports

        Returns:
            List of (caller_id, callee_id) tuples
        """
        edges = []

        # Find all function/method definitions and their calls
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Determine caller entity
                caller_id = None

                if isinstance(node, ast.FunctionDef):
                    # Check if it's a method
                    caller_id = self._get_entity_id(file_path, None, node.name)
                    # Check if it's actually a method
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef):
                            if node in parent.body:
                                caller_id = self._get_entity_id(
                                    file_path, parent.name, node.name
                                )
                                break

                elif isinstance(node, ast.ClassDef):
                    # Class definition itself
                    caller_id = self._get_entity_id(file_path, None, node.name)

                if not caller_id or caller_id not in local_entities:
                    continue

                # Find all calls within this entity
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        callee_id = self._resolve_call_target(
                            child, local_entities, symbol_table
                        )
                        if callee_id and callee_id in local_entities:
                            edges.append((caller_id, callee_id))

        return edges

    def parse_file(self, file_path: str) -> None:
        """
        Parse a single file and add to graph.

        Args:
            file_path: Absolute path to Python file
        """
        if not file_path.endswith('.py'):
            return

        entities, symbol_table = self._parse_file(file_path)

        # Add entities to graph
        for entity in entities:
            self.entities[entity.entity_id] = entity
            self.graph.add_node(entity.entity_id, **{
                'type': entity.entity_type,
                'file_path': entity.file_path,
                'lineno': entity.lineno,
                'end_lineno': entity.end_lineno,
                'source_code': entity.source_code
            })

        # Update symbol table for this file
        rel_path = self._get_relative_path(file_path)
        self.symbol_table[rel_path] = symbol_table

        # Extract and add edges
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
            edges = self._extract_edges(tree, rel_path, self.entities, symbol_table)

            for caller_id, callee_id in edges:
                self.graph.add_edge(caller_id, callee_id, type='calls')

        except Exception as e:
            logger.error(f"Failed to extract edges from {file_path}: {e}")

    def parse_directory(self, directory: str) -> None:
        """
        Parse all Python files in a directory in two passes.
        Pass 1: Collect all entities.
        Pass 2: Extract call-graph edges (requires complete entity table).

        Args:
            directory: Directory path to parse
        """
        dir_path = Path(directory).resolve()
        py_files = []
        for py_file in dir_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "__pycache__" in str(py_file) or "test" in str(py_file).lower():
                continue
            py_files.append(str(py_file.resolve()))

        # Pass 1: Parse files to populate self.entities and self.symbol_table
        for py_file in py_files:
            entities, symbol_table = self._parse_file(py_file)
            
            # Add entities to graph
            for entity in entities:
                self.entities[entity.entity_id] = entity
                self.graph.add_node(entity.entity_id, **{
                    'type': entity.entity_type,
                    'file_path': entity.file_path,
                    'lineno': entity.lineno,
                    'end_lineno': entity.end_lineno,
                    'source_code': entity.source_code
                })
            
            # Update symbol table
            rel_path = self._get_relative_path(py_file)
            self.symbol_table[rel_path] = symbol_table

        # Pass 2: Extract and add edges
        for py_file in py_files:
            rel_path = self._get_relative_path(py_file)
            symbol_table = self.symbol_table.get(rel_path, {})
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
                edges = self._extract_edges(tree, rel_path, self.entities, symbol_table)

                for caller_id, callee_id in edges:
                    self.graph.add_edge(caller_id, callee_id, type='calls')

            except Exception as e:
                logger.error(f"Failed to extract edges from {py_file}: {e}")

    def remove_file(self, file_path: str) -> None:
        """
        Remove entities and edges for a deleted file.

        Args:
            file_path: Relative file path
        """
        # Find all entities from this file
        entities_to_remove = [
            entity_id for entity_id, entity in self.entities.items()
            if entity.file_path == file_path
        ]

        # Remove from graph and entities dict
        for entity_id in entities_to_remove:
            if entity_id in self.graph:
                self.graph.remove_node(entity_id)
            if entity_id in self.entities:
                del self.entities[entity_id]

        # Remove from symbol table
        if file_path in self.symbol_table:
            del self.symbol_table[file_path]

    def update_file(self, file_path: str) -> None:
        """
        Update entities and edges for a modified file.

        Args:
            file_path: Relative file path
        """
        # Remove old entities
        self.remove_file(file_path)

        # Parse and add new entities
        absolute_path = self.repo_path / file_path
        if absolute_path.exists():
            self.parse_file(str(absolute_path))

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity object or None
        """
        return self.entities.get(entity_id)

    def get_all_entities(self) -> List[Entity]:
        """
        Get all entities.

        Returns:
            List of all entities
        """
        return list(self.entities.values())

    def get_graph(self) -> nx.DiGraph:
        """
        Get the dependency graph.

        Returns:
            NetworkX directed graph
        """
        return self.graph

    def get_undirected_graph(self) -> nx.Graph:
        """
        Get undirected version of the dependency graph.

        Returns:
            NetworkX undirected graph
        """
        return self.graph.to_undirected()

    def get_dependents(self, entity_id: str, max_hops: Optional[int] = None) -> Set[str]:
        """
        Get all entities that depend on the given entity (downstream).

        Args:
            entity_id: Entity identifier
            max_hops: Maximum number of hops (None for unlimited)

        Returns:
            Set of dependent entity IDs
        """
        if entity_id not in self.graph:
            return set()

        # Reverse graph to find dependents
        reverse_graph = self.graph.reverse()
        if max_hops is None:
            return nx.descendants(reverse_graph, entity_id)
        else:
            return set(nx.dfs_preorder_nodes(
                reverse_graph, entity_id, depth_limit=max_hops
            ))

    def get_dependencies(self, entity_id: str, max_hops: Optional[int] = None) -> Set[str]:
        """
        Get all entities that the given entity depends on (upstream).

        Args:
            entity_id: Entity identifier
            max_hops: Maximum number of hops (None for unlimited)

        Returns:
            Set of dependency entity IDs
        """
        if entity_id not in self.graph:
            return set()

        if max_hops is None:
            return nx.descendants(self.graph, entity_id)
        else:
            return set(nx.dfs_preorder_nodes(
                self.graph, entity_id, depth_limit=max_hops
            ))

    def get_shortest_path_distance(self, source: str, target: str) -> Optional[int]:
        """
        Get shortest path distance between two entities.

        Args:
            source: Source entity ID
            target: Target entity ID

        Returns:
            Distance or None if no path exists
        """
        try:
            return nx.shortest_path_length(self.graph, source, target)
        except nx.NetworkXNoPath:
            return None

    def get_nearest_modified_distance(self, entity_id: str,
                                      modified_entities: Set[str]) -> Optional[int]:
        """
        Get shortest distance to nearest modified entity.

        Args:
            entity_id: Entity identifier
            modified_entities: Set of modified entity IDs

        Returns:
            Minimum distance or None
        """
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
"""Repository parser compatibility wrapper. Aliases RepoParser to TreeSitterRepoParser."""

try:
    from core.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
except ImportError:
    try:
        from src.core.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
    except ImportError:
        from .tree_sitter_repo_parser import TreeSitterRepoParser, Entity

# Clean alias for backward compatibility across all modules
RepoParser = TreeSitterRepoParser
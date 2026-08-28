"""Repository parser compatibility wrapper. Aliases RepoParser to TreeSitterRepoParser."""

try:
    from src.tree_sitter_repo_parser import TreeSitterRepoParser, Entity
except ImportError:
    from tree_sitter_repo_parser import TreeSitterRepoParser, Entity

# Clean alias for backward compatibility across all modules
RepoParser = TreeSitterRepoParser
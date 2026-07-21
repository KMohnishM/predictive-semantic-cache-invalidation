# Problem Statement: Tree-sitter Parsing Migration

## Problem Description
Our current repository parser (`src/repo_parser.py`) is tightly coupled to Python's built-in `ast` module. While sufficient for a Python-only research prototype, this design presents significant challenges for real-world scaling and multi-language codebase indexing:

1.  **Language Lock-in:** The built-in `ast` module only parses Python code. If the cache invalidation system is applied to other languages (like Go, JavaScript, C++, or Java), the entire parsing module has to be re-written from scratch for each language.
2.  **Lack of Incremental Parsing:** The AST parser reads and rebuilds the entire syntax tree from scratch for every file change, wasting CPU cycles on large files during incremental commit checkouts.
3.  **Fragility under Syntax Errors:** Python's built-in parser fails completely and raises a `SyntaxError` if it encounters invalid syntax, which frequently happens during active developer editing sessions or broken commits.

---

## Migration Goals
To resolve these issues, we need to migrate our parsing infrastructure to **Tree-sitter** (utilizing `tree-sitter-languages` for pre-compiled binaries):

*   **Multi-language compatibility:** Define language-agnostic extraction APIs so parsers can be easily swapped or extended.
*   **AST-to-CST parity:** Ensure that the nodes (functions, classes, methods) and calls resolved via Tree-sitter query scripts match our existing dependency graph counts exactly.
*   **Robustness:** The parser must handle partial syntax and incomplete code blocks without crashing or corrupting the global dependency graph.

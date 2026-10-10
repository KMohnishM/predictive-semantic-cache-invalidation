"""Call-graph aware contextual text for entity embeddings.

Single source of truth for the text that gets embedded per entity, shared by
Pipeline A (run_experiment.py / notebooks) and Pipeline B (src/benchmarking/),
so the drift labels the predictor is trained on and the vectors the benchmark
evaluates come from the exact same representation.
"""

from __future__ import annotations

import textwrap
from typing import Any


def extract_signature(entity: Any) -> str:
    """Extract the (possibly multi-line) def/class signature from an entity's source."""
    lines = entity.source_code.splitlines()
    def_idx = -1
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class "):
            def_idx = idx
            break

    if def_idx == -1:
        # Fallback to name-only signature if def/class keyword is not found
        name = entity.entity_id.split("::")[-1]
        return f"def {name}()"

    # Extract signature lines from def_idx until we find the ending colon ':'
    sig_lines = []
    for idx in range(def_idx, len(lines)):
        line = lines[idx]
        sig_lines.append(line)
        clean_line = line.split('#')[0].rstrip()
        if clean_line.endswith(':'):
            return "\n".join(sig_lines)
    return lines[def_idx]


def build_contextual_source(entity: Any, repo_parser: Any, large_context: bool = False) -> str:
    """Return entity source plus one-hop callee stubs (call-graph context).

    Args:
        entity: Entity with ``entity_id`` and ``source_code``.
        repo_parser: TreeSitterRepoParser for the same commit as ``entity``
            (provides ``get_dependencies`` and ``get_entity``).
        large_context: True for 8k+ token models — stubs carry full docstrings
            instead of a single context line.
    """
    source = entity.source_code

    deps = repo_parser.get_dependencies(entity.entity_id, max_hops=1)
    deps = {d for d in deps if d != entity.entity_id}
    if not deps:
        return source

    stubs = []
    for dep_id in sorted(deps):
        dep_entity = repo_parser.get_entity(dep_id)
        if not dep_entity:
            continue

        sig_dedented = textwrap.dedent(extract_signature(dep_entity)).strip()
        if not sig_dedented.endswith(':'):
            sig_dedented += ':'

        if large_context:
            # Large context window (8k+): include full docstrings & signatures
            doc = (getattr(dep_entity, 'docstring', '') or '').replace('"""', r'\"\"\"')
            if doc:
                doc_indented = textwrap.indent(doc, '    ')
                doc_block = f'    """\n{doc_indented}\n    """\n'
            else:
                doc_block = ''
            stub = f"{sig_dedented}\n{doc_block}    pass"
        else:
            # Small context window (<8k): semantic stub with first docstring/body line
            dep_doc = (getattr(dep_entity, 'docstring', '') or '').strip()
            if dep_doc:
                first_line = dep_doc.split('\n')[0].strip()
            else:
                lines = dep_entity.source_code.split('\n')
                body_lines = [
                    l.strip() for l in lines
                    if l.strip() and not l.strip().startswith('def ')
                    and not l.strip().startswith('class ') and not l.strip().startswith('@')
                ]
                first_line = body_lines[0] if body_lines else 'pass'

            # Truncate first line to avoid overly long line stubs
            if len(first_line) > 120:
                first_line = first_line[:117] + '...'
            stub = f"{sig_dedented}\n    # Context: {first_line}\n    pass"

        stubs.append(stub)

    if stubs:
        return source + "\n\n# Call Graph Context\n" + "\n\n".join(stubs)
    return source

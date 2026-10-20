"""Leakage checks for benchmark / ground-truth query sets.

A query must describe what an entity does without handing the retriever a
lexical shortcut to it. The checks here are used both when building a query
set (scripts/build_black_sanitized_dataset.py) and when auditing one.

Rules (all must hold for a query to be valid for its target):
  1. No identifier leakage: the target's full name, its enclosing class name,
     its file name / path, or any name token of >= MIN_NAME_TOKEN_LEN chars
     (``visit_default`` -> "visit", "default") must not appear as a word.
  2. No verbatim copying: the query shares no run of NGRAM_SIZE consecutive
     words with the target's source code (which includes its docstring — the
     text that actually gets embedded).
  3. Unambiguous: the same query text is not used for two different targets.
  4. Coverage: every target has at least MIN_QUERIES_PER_TARGET queries (the
     minimum the ground-truth sign test needs to reach p < 0.05).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set

MIN_NAME_TOKEN_LEN = 4
NGRAM_SIZE = 4
MIN_QUERIES_PER_TARGET = 5

_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_query_text(text: str) -> str:
    """Case/whitespace-insensitive form used for duplicate detection."""
    return " ".join(text.lower().split())


def split_identifier(name: str) -> List[str]:
    """``visit_defaultNode`` -> ["visit", "default", "node"]."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s1)
    return [w.lower() for w in s2.replace("_", " ").split() if w]


def identifier_terms(entity_id: str, file_path: str) -> Set[str]:
    """Words that must not appear in a query targeting ``entity_id``."""
    parts = entity_id.split("::")
    names = parts[1:] if len(parts) > 1 else parts
    terms: Set[str] = set()
    for name in names:
        terms.add(name.lower())
    own_name = parts[-1]
    terms.update(t for t in split_identifier(own_name) if len(t) >= MIN_NAME_TOKEN_LEN)
    if file_path:
        path = Path(file_path)
        terms.add(path.name.lower())
        if len(path.stem) >= MIN_NAME_TOKEN_LEN and path.stem != "__init__":
            terms.add(path.stem.lower())
    return {t for t in terms if t.strip("_")}


def leaked_identifier_terms(query_text: str, entity_id: str, file_path: str) -> List[str]:
    """Identifier terms of the target that appear as whole words in the query."""
    text = query_text.lower()
    hits = []
    for term in identifier_terms(entity_id, file_path):
        if re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", text):
            hits.append(term)
    if file_path and file_path.lower() in text:
        hits.append(file_path.lower())
    return sorted(set(hits))


def word_ngrams(text: str, n: int = NGRAM_SIZE) -> Set[tuple]:
    words = _WORD_RE.findall(text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def shared_ngrams(query_text: str, source_code: str, n: int = NGRAM_SIZE) -> Set[tuple]:
    """Runs of ``n`` consecutive words the query copies from the source."""
    return word_ngrams(query_text, n) & word_ngrams(source_code, n)


def query_violations(query_text: str, entity_id: str, file_path: str, source_code: str) -> List[str]:
    """Per-query rule violations (rules 1 and 2). Empty list == clean."""
    problems = []
    leaked = leaked_identifier_terms(query_text, entity_id, file_path)
    if leaked:
        problems.append(f"identifier:{','.join(leaked)}")
    copied = shared_ngrams(query_text, source_code)
    if copied:
        problems.append(f"verbatim:{' '.join(sorted(copied)[0])}")
    return problems


def audit_query_set(
    queries: Iterable[Mapping],
    sources_by_entity: Mapping[str, str],
    min_queries_per_target: int = MIN_QUERIES_PER_TARGET,
) -> Dict[str, object]:
    """Audit a query set (dicts with query_text/target_entity_id/file_path).

    Args:
        queries: Query rows.
        sources_by_entity: entity_id -> source code for the snapshot the queries
            are meant for. Targets missing from it are reported.
        min_queries_per_target: Coverage requirement (rule 4).
    """
    queries = list(queries)
    targets_by_text: Dict[str, Set[str]] = defaultdict(set)
    per_target: Dict[str, int] = defaultdict(int)
    leaks: List[dict] = []
    missing_targets: Set[str] = set()

    for q in queries:
        eid = q["target_entity_id"]
        per_target[eid] += 1
        targets_by_text[normalize_query_text(q["query_text"])].add(eid)
        source = sources_by_entity.get(eid)
        if source is None:
            missing_targets.add(eid)
            continue
        problems = query_violations(q["query_text"], eid, q.get("file_path", ""), source)
        if problems:
            leaks.append({"query_id": q.get("query_id"), "target": eid,
                          "text": q["query_text"], "problems": problems})

    ambiguous = {t: sorted(s) for t, s in targets_by_text.items() if len(s) > 1}
    under_covered = {eid: n for eid, n in per_target.items() if n < min_queries_per_target}
    return {
        "n_queries": len(queries),
        "n_targets": len(per_target),
        "leaking_queries": leaks,
        "ambiguous_texts": ambiguous,
        "under_covered_targets": under_covered,
        "missing_targets": sorted(missing_targets),
        "ok": not leaks and not ambiguous and not under_covered and not missing_targets,
    }


def first_violation_free(
    candidates: Iterable[str],
    entity_id: str,
    file_path: str,
    source_code: str,
    limit: Optional[int] = None,
) -> List[str]:
    """Filter candidate texts to those passing rules 1 and 2 (deduplicated, order kept)."""
    kept: List[str] = []
    seen: Set[str] = set()
    for text in candidates:
        norm = normalize_query_text(text)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if not query_violations(text, entity_id, file_path, source_code):
            kept.append(" ".join(text.split()))
            if limit is not None and len(kept) >= limit:
                break
    return kept

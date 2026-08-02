#!/usr/bin/env python3
"""
Semantic Cache Invalidation — Dependency-Aware Re-Embedding Pipeline
=====================================================================

Standalone, self-contained implementation. No external project code assumed.

Pipeline:
    [repo @ commit A] --Joern--> [graph A]
    [repo @ commit B] --Joern--> [graph B]
                                     |
                                graph diff
                                     |
                            semantic change filter
                                     |
                          edge-strength scoring (Joern features)
                                     |
                     decay-based impact propagation (blast radius)
                                     |
                          selective re-embed (only stale nodes)

Requirements:
    - A running Joern server (`joern --server`, default port 8080).
    - Python packages: scikit-learn, numpy, cpgqls-client
        pip install scikit-learn numpy cpgqls-client
    - git installed and on PATH, if using weight calibration from history.

Usage:
    python semantic_cache_invalidation.py diff <repo_path> <old_commit> <new_commit> [--server host:port]
    python semantic_cache_invalidation.py calibrate <repo_path> --commits 20 [--server host:port]
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.metrics.pairwise import cosine_similarity


# =====================================================================
# 1. JOERN GRAPH EXTRACTION (via Joern SERVER — HTTP, port 8080)
# =====================================================================
#
# Joern is running in server mode (`joern --server`, default port 8080),
# so extraction talks to it over HTTP using Joern's official Python
# client `cpgqls_client` (pip install cpgqls-client), instead of
# shelling out to joern-parse/joern CLI binaries.
#
# IMPORTANT DESIGN NOTE: for any non-trivial repo, the extracted JSON
# can be many MB. Pushing that through the query/stdout round-trip is
# unreliable (Joern's Ammonite-based REPL echoes every `val` result by
# default, and very large responses get truncated). Instead, the query
# writes the JSON directly to a file on disk (the server process already
# has filesystem access to repo_path, so it can write output there too),
# and Python just checks for a short success marker plus reads the file.
#
# All `val`/`def` statements below end in `;` to suppress the REPL's
# automatic echoing of each intermediate result.

import uuid as _uuid
from cpgqls_client import CPGQLSClient, import_code_query

_DONE_MARKER = "<<<EXTRACTION_DONE>>>"

# {out_path} is substituted with a Scala-string-escaped path before sending.
#
# Everything is nested inside the block passed to println(...). This is the
# key fix: Scala's REPL always echoes top-level `val` bindings regardless of
# trailing semicolons (semicolons only suppress echoing of bare expression
# results). By making every `val`/`def` local to this block, none of them
# are top-level REPL bindings, so the server only ever echoes the single
# println() output below — not a dump of every method in the CPG.
JOERN_EXTRACTION_QUERY_TEMPLATE = r"""
{{
  def q(s: String): String = "\"" + s.replace("\\", "\\\\").replace("\"", "'") + "\""
  def strList(xs: List[String]): String = xs.map(q).mkString("[", ",", "]")

  val methods = cpg.method.filterNot(_.isExternal).l

  val jsonRecords = methods.map {{ m =>
    val name = m.fullName
    val signature = m.signature
    val paramTypes = m.parameter.typeFullName.l
    val returnType = m.methodReturn.typeFullName
    val callers = m.callIn.method.fullName.dedup.l
    val callSiteCount = m.callIn.size
    val callees = m.call.methodFullName.dedup.l
    val callsWithConsumedReturn = m.call.filter {{ c =>
      c.inAssignment.nonEmpty || c.argumentIndex > 0
    }}.methodFullName.dedup.l

    val fields = List(
      q("name") + ":" + q(name),
      q("signature") + ":" + q(signature),
      q("paramTypes") + ":" + strList(paramTypes),
      q("returnType") + ":" + q(returnType),
      q("callers") + ":" + strList(callers),
      q("callSiteCount") + ":" + callSiteCount.toString,
      q("callees") + ":" + strList(callees),
      q("callsWithConsumedReturn") + ":" + strList(callsWithConsumedReturn),
      q("code") + ":" + q(m.code)
    )

    "{{" + fields.mkString(",") + "}}"
  }}

  val jsonOut = "[" + jsonRecords.mkString(",") + "]"

  val pw = new java.io.PrintWriter("{out_path}")
  pw.write(jsonOut)
  pw.close()

  "{done_marker}"
}}
"""


def _scala_escape_path(path: str) -> str:
    """Escapes a filesystem path for embedding inside a Scala string literal."""
    return path.replace("\\", "\\\\").replace('"', '\\"')


def _run_query(client: "CPGQLSClient", query: str) -> dict:
    result = client.execute(query)
    if result.get("stderr"):
        # Non-fatal warnings are common; only raise if there's no stdout at all.
        if not result.get("stdout"):
            raise RuntimeError(f"Joern query failed:\n{result.get('stderr')}")
    return result


def extract_graph_with_joern(
    repo_path: str,
    out_json_path: str,
    server_endpoint: str = "localhost:8080",
) -> None:
    """
    Talks to a running Joern server (joern --server) over HTTP, imports
    the repo at repo_path as a fresh CPG, extracts method-level features,
    and writes them as a JSON snapshot to out_json_path (written directly
    by the server process, not round-tripped through stdout).
    """
    client = CPGQLSClient(server_endpoint)
    project_name = "extract_" + _uuid.uuid4().hex[:8]

    # Step 1: tell the server to parse the repo into a CPG.
    import_query = import_code_query(repo_path.replace("\\", "/"), project_name)
    import_result = _run_query(client, import_query)
    if (import_result.get("stderr") and "error" in import_result.get("stderr", "").lower()) or ("Error:" in import_result.get("stdout", "")):
        raise RuntimeError(f"Failed to import repo into Joern:\n{import_result.get('stderr', '')}\n{import_result.get('stdout', '')}")

    # Step 2: run the extraction query, which writes JSON to out_json_path
    # on the server side and only echoes a short done-marker back to us.
    query = JOERN_EXTRACTION_QUERY_TEMPLATE.format(
        out_path=_scala_escape_path(out_json_path),
        done_marker=_DONE_MARKER,
    )
    extract_result = client.execute(query)   # raw result, not _run_query, so we see everything
    stdout = extract_result.get("stdout", "")

    if _DONE_MARKER not in stdout:
        raise RuntimeError(
            "Joern extraction did not complete (done marker not found). "
            f"Full raw response from server:\n{extract_result}"
        )

    if not os.path.exists(out_json_path):
        raise RuntimeError(
            f"Joern reported success but {out_json_path} was not created. "
            "This usually means the Joern server process cannot see this path "
            "(e.g. it's running in a container/WSL without access to this "
            "Windows path) — check where the Joern server process actually runs."
        )


def load_graph_snapshot(json_path: str) -> Dict[str, dict]:
    """Loads a Joern-extracted JSON snapshot into a dict keyed by method name."""
    with open(json_path) as f:
        records = json.load(f)
    return {r["name"]: r for r in records}


# =====================================================================
# 2. GRAPH DIFF
# =====================================================================

@dataclass
class GraphDiff:
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    changed: List[str] = field(default_factory=list)   # code or signature differs
    unchanged: List[str] = field(default_factory=list)


def diff_graphs(old_graph: Dict[str, dict], new_graph: Dict[str, dict]) -> GraphDiff:
    diff = GraphDiff()
    old_names = set(old_graph)
    new_names = set(new_graph)

    diff.added = sorted(new_names - old_names)
    diff.removed = sorted(old_names - new_names)

    for name in sorted(old_names & new_names):
        old_rec, new_rec = old_graph[name], new_graph[name]
        if old_rec.get("signature") != new_rec.get("signature"):
            diff.changed.append(name)
        elif old_rec.get("code") != new_rec.get("code"):
            diff.changed.append(name)
        else:
            diff.unchanged.append(name)

    return diff


# =====================================================================
# 3. SEMANTIC FILTER (cosmetic vs. semantic)
# =====================================================================

def normalize_source(code: str) -> str:
    """
    Strips variable names / comments / formatting by round-tripping
    through Python's AST, so cosmetic-only edits normalize to the
    same string. Falls back to whitespace-collapsed code if the
    snippet isn't parseable standalone (e.g. a bare method body).
    """
    try:
        tree = ast.parse(code)
        return ast.dump(tree, annotate_fields=False)
    except SyntaxError:
        return " ".join(code.split())


def is_semantic_change(old_code: str, new_code: str) -> bool:
    """True if the change is more than cosmetic (renames/comments/formatting)."""
    return normalize_source(old_code) != normalize_source(new_code)


def classify_changed_nodes(diff: GraphDiff, old_graph: dict, new_graph: dict) -> List[str]:
    """Filters diff.changed down to nodes whose change is semantic, not cosmetic."""
    semantic = []
    for name in diff.changed:
        old_code = old_graph[name].get("code", "")
        new_code = new_graph[name].get("code", "")
        if is_semantic_change(old_code, new_code):
            semantic.append(name)
    # signature changes and additions/removals always count as semantic
    semantic.extend(diff.added)
    semantic.extend(diff.removed)
    return list(dict.fromkeys(semantic))  # de-dup, preserve order


# =====================================================================
# 4. EDGE STRENGTH SCORING
# =====================================================================

# Default weights — replace with fitted weights from calibrate_weights()
# once enough git history has been processed.
DEFAULT_WEIGHTS = {"data_flow": 0.5, "call_freq": 0.3, "signature": 0.2}


def data_flow_coupling(caller: str, callee: str, graph: Dict[str, dict]) -> float:
    """
    Proxy for data-flow coupling: fraction of caller's calls to callee
    whose return value is consumed (assigned/passed on) rather than discarded.
    """
    rec = graph.get(caller)
    if rec is None:
        return 0.0
    consumed = rec.get("callsWithConsumedReturn", [])
    callees = rec.get("callees", [])
    total_calls_to_callee = callees.count(callee)
    if total_calls_to_callee == 0:
        return 0.0
    consumed_calls_to_callee = consumed.count(callee)
    return consumed_calls_to_callee / total_calls_to_callee


def call_frequency_norm(caller: str, callee: str, graph: Dict[str, dict]) -> float:
    """
    Normalized call-frequency signal: how central is this caller to
    the callee, relative to all of the callee's other callers.
    A callee with many callers dilutes any single caller's coupling.
    """
    rec = graph.get(callee)
    if rec is None:
        return 0.0
    num_callers = max(len(rec.get("callers", [])), 1)
    return 1.0 / num_callers


def signature_dependency(callee: str, old_graph: dict, new_graph: dict) -> float:
    """1.0 if callee's signature changed between snapshots, else 0.0."""
    old_rec, new_rec = old_graph.get(callee), new_graph.get(callee)
    if old_rec is None or new_rec is None:
        return 1.0  # added/removed = maximal structural impact
    return 1.0 if old_rec.get("signature") != new_rec.get("signature") else 0.0


def edge_strength(
    caller: str,
    callee: str,
    old_graph: dict,
    new_graph: dict,
    weights: Dict[str, float] = None,
) -> float:
    weights = weights or DEFAULT_WEIGHTS
    df = data_flow_coupling(caller, callee, new_graph)
    cf = call_frequency_norm(caller, callee, new_graph)
    sig = signature_dependency(callee, old_graph, new_graph)

    # signature break overrides the blend — near-certain semantic impact
    if sig == 1.0:
        return 1.0

    return weights["data_flow"] * df + weights["call_freq"] * cf + weights["signature"] * sig


# =====================================================================
# 5. IMPACT PROPAGATION (decay-based blast radius)
# =====================================================================

def build_caller_index(graph: Dict[str, dict]) -> Dict[str, List[str]]:
    """method -> list of methods that call it (reverse of 'callees')."""
    callers_of: Dict[str, List[str]] = {}
    for name, rec in graph.items():
        for callee in rec.get("callees", []):
            callers_of.setdefault(callee, []).append(name)
    return callers_of


def propagate_impact(
    semantic_changes: List[str],
    old_graph: dict,
    new_graph: dict,
    weights: Dict[str, float] = None,
    threshold: float = 0.05,
    max_hops: int = 6,
) -> Dict[str, float]:
    """
    BFS outward from each semantically-changed node along reverse call
    edges (i.e. towards callers), multiplying edge strength at each hop.
    Returns {node_name: propagated_strength} for every node whose
    propagated strength exceeds `threshold`. Multiple paths to the same
    node keep the MAX strength seen.
    """
    callers_of = build_caller_index(new_graph)
    stale: Dict[str, float] = {}

    frontier: List[Tuple[str, float, int]] = [(n, 1.0, 0) for n in semantic_changes]
    visited_strength: Dict[str, float] = {n: 1.0 for n in semantic_changes}

    while frontier:
        node, strength, hops = frontier.pop()
        if hops >= max_hops:
            continue

        for caller in callers_of.get(node, []):
            e = edge_strength(caller, node, old_graph, new_graph, weights)
            propagated = strength * e   # multiplicative decay

            if propagated < threshold:
                continue

            if propagated > visited_strength.get(caller, 0.0):
                visited_strength[caller] = propagated
                stale[caller] = propagated
                frontier.append((caller, propagated, hops + 1))

    # the originally-changed nodes are always stale at strength 1.0
    for n in semantic_changes:
        stale[n] = 1.0

    return stale


# =====================================================================
# 6. EMBEDDING + SIMILARITY (lightweight, no external API required)
# =====================================================================

class Embedder:
    """
    TF-IDF-based embedding as a dependency-free stand-in for a real
    embedding model. Swap `.embed()` for a call to any real embedding
    API/model without changing the rest of the pipeline.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self._fitted = False

    def fit(self, corpus: List[str]) -> None:
        self.vectorizer.fit(corpus)
        self._fitted = True

    def embed(self, texts: List[str]) -> np.ndarray:
        if not self._fitted:
            self.fit(texts)
        return self.vectorizer.transform(texts).toarray()

    @staticmethod
    def drift(vec_before: np.ndarray, vec_after: np.ndarray) -> float:
        sim = cosine_similarity(vec_before.reshape(1, -1), vec_after.reshape(1, -1))[0][0]
        return 1.0 - sim


def selective_reembed(
    stale_nodes: Dict[str, float],
    new_graph: dict,
    embedder: Embedder,
    cache: Dict[str, np.ndarray],
) -> Dict[str, np.ndarray]:
    """Re-embeds only stale nodes, merging into the existing cache."""
    texts = [new_graph[n]["code"] for n in stale_nodes if n in new_graph]
    names = [n for n in stale_nodes if n in new_graph]
    if texts:
        vectors = embedder.embed(texts)
        for name, vec in zip(names, vectors):
            cache[name] = vec
    return cache


# =====================================================================
# 7. WEIGHT CALIBRATION FROM GIT HISTORY
# =====================================================================

def list_recent_commits(repo_path: str, n: int) -> List[str]:
    out = subprocess.run(
        ["git", "-C", repo_path, "log", f"-{n}", "--pretty=%H"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip().splitlines()


def checkout_commit(repo_path: str, commit: str) -> None:
    subprocess.run(["git", "-C", repo_path, "checkout", commit], check=True)


def calibrate_weights(
    repo_path: str,
    num_commits: int = 20,
    server_endpoint: str = "localhost:8080",
) -> Dict[str, float]:
    """
    Walks recent commit history, extracts Joern graphs at each commit,
    measures real embedding drift on direct (1-hop) neighbors of
    changed nodes, and fits w1/w2/w3 via linear regression.
    """
    commits = list_recent_commits(repo_path, num_commits)
    embedder = Embedder()

    features: List[List[float]] = []
    labels: List[float] = []

    for i in range(len(commits) - 1, 0, -1):
        old_commit, new_commit = commits[i], commits[i - 1]

        with tempfile.TemporaryDirectory() as tmp:
            old_json = os.path.join(tmp, "old.json")
            new_json = os.path.join(tmp, "new.json")

            checkout_commit(repo_path, old_commit)
            extract_graph_with_joern(repo_path, old_json, server_endpoint)
            old_graph = load_graph_snapshot(old_json)

            checkout_commit(repo_path, new_commit)
            extract_graph_with_joern(repo_path, new_json, server_endpoint)
            new_graph = load_graph_snapshot(new_json)

        diff = diff_graphs(old_graph, new_graph)
        semantic_changed = classify_changed_nodes(diff, old_graph, new_graph)
        callers_of = build_caller_index(new_graph)

        print(
            f"[{old_commit[:8]}..{new_commit[:8]}] "
            f"old_methods={len(old_graph)} new_methods={len(new_graph)} "
            f"added={len(diff.added)} removed={len(diff.removed)} "
            f"changed={len(diff.changed)} semantic={len(semantic_changed)} "
            f"nodes_with_callers={sum(1 for c in semantic_changed if callers_of.get(c))}",
            file=sys.stderr,
        )

        all_code = [r["code"] for r in new_graph.values()] + [r["code"] for r in old_graph.values()]
        embedder.fit(all_code)

        for changed in semantic_changed:
            for neighbor in callers_of.get(changed, []):  # 1-hop only
                if neighbor not in old_graph or neighbor not in new_graph:
                    continue

                df = data_flow_coupling(neighbor, changed, new_graph)
                cf = call_frequency_norm(neighbor, changed, new_graph)
                sig = signature_dependency(changed, old_graph, new_graph)

                vec_before = embedder.embed([old_graph[neighbor]["code"]])[0]
                vec_after = embedder.embed([new_graph[neighbor]["code"]])[0]
                drift = Embedder.drift(vec_before, vec_after)

                features.append([df, cf, sig])
                labels.append(drift)

    if not features:
        print("No 1-hop samples found — cannot fit weights.", file=sys.stderr)
        return DEFAULT_WEIGHTS

    X = np.array(features)
    y = np.array(labels)
    
    if np.all(y == 0):
        print("All 1-hop neighbors had 0.0 drift (no simultaneous edits). Defaulting to base weights.", file=sys.stderr)
        return DEFAULT_WEIGHTS

    model = LinearRegression().fit(X, y)
    w1, w2, w3 = model.coef_

    return {"data_flow": float(w1), "call_freq": float(w2), "signature": float(w3)}


# =====================================================================
# 8. CLI ORCHESTRATION
# =====================================================================

def run_diff_pipeline(
    repo_path: str,
    old_commit: str,
    new_commit: str,
    threshold: float,
    server_endpoint: str = "localhost:8080",
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        old_json = os.path.join(tmp, "old.json")
        new_json = os.path.join(tmp, "new.json")

        checkout_commit(repo_path, old_commit)
        extract_graph_with_joern(repo_path, old_json, server_endpoint)
        old_graph = load_graph_snapshot(old_json)

        checkout_commit(repo_path, new_commit)
        extract_graph_with_joern(repo_path, new_json, server_endpoint)
        new_graph = load_graph_snapshot(new_json)

    diff = diff_graphs(old_graph, new_graph)
    semantic_changed = classify_changed_nodes(diff, old_graph, new_graph)
    stale = propagate_impact(semantic_changed, old_graph, new_graph, threshold=threshold)

    print(json.dumps({
        "added": diff.added,
        "removed": diff.removed,
        "semantic_changes": semantic_changed,
        "stale_nodes_to_reembed": stale,
    }, indent=2))

    embedder = Embedder()
    cache: Dict[str, np.ndarray] = {}
    selective_reembed(stale, new_graph, embedder, cache)
    print(f"\nRe-embedded {len(cache)} nodes (out of {len(new_graph)} total).")


def main():
    parser = argparse.ArgumentParser(description="Dependency-aware re-embedding pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    diff_p = sub.add_parser("diff", help="Run the full pipeline between two commits")
    diff_p.add_argument("repo_path")
    diff_p.add_argument("old_commit")
    diff_p.add_argument("new_commit")
    diff_p.add_argument("--threshold", type=float, default=0.05)
    diff_p.add_argument("--server", default="localhost:8080", help="Joern server host:port")

    cal_p = sub.add_parser("calibrate", help="Fit strength weights from git history")
    cal_p.add_argument("repo_path")
    cal_p.add_argument("--commits", type=int, default=20)
    cal_p.add_argument("--server", default="localhost:8080", help="Joern server host:port")

    args = parser.parse_args()

    if args.command == "diff":
        run_diff_pipeline(args.repo_path, args.old_commit, args.new_commit, args.threshold, args.server)
    elif args.command == "calibrate":
        weights = calibrate_weights(args.repo_path, args.commits, args.server)
        print(json.dumps(weights, indent=2))


if __name__ == "__main__":
    main()
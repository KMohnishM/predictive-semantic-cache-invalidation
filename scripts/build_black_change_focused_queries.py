#!/usr/bin/env python3
"""Build a leakage-checked query set for psf/black focused on the entities that change.

The 865-query set (build_black_sanitized_dataset.py) covers 173 of ~680 entities,
chosen only by "has a docstring that paraphrases cleanly" — so most entities that
actually change in the training / benchmark windows have no query, and their
staleness is invisible to both the ground-truth labels and the benchmark.

This builder starts from the commit windows instead:
  1. Sample the commits exactly as Pipeline A (settings.json) and the benchmark
     (benchmark_settings.json) do, and read every sampled snapshot from git
     (no checkout).
  2. For every consecutive pair, find the entities whose own source changed and
     the entities whose embedded (call-graph contextual) text changed.
       tier "changed":  either of the above, in any pair of either window
       tier "neighbor": a 1-hop caller/callee of a changed entity (the entities
                        a propagation strategy would consider re-embedding)
       tier "other":    everything else (only with --include-all)
  3. Each target's "purpose" is its docstring summary (newest version in the
     windows) or, failing that, an independently written description from
     --descriptions (entity_id -> text; never generated from the embedding model).
  4. Purposes are paraphrased with the local T5 paraphraser, and each candidate
     must pass src/benchmarking/query_validation.py against EVERY version of the
     entity seen in the windows (no name tokens, no 4-gram copied from source);
     an authored description is itself a candidate.
  5. Fidelity: the T5 sampler sometimes drifts into unrelated text, so a candidate
     is kept only if an independent embedding model (default bge-base-en-v1.5 —
     deliberately NOT the MiniLM model under evaluation) scores its cosine
     similarity to the purpose at >= --min-fidelity.
  6. Texts produced for two targets are dropped; targets with fewer than
     --queries-per-entity clean queries are dropped.

Output: src/benchmarking/data/curated_queries_black_change_focused.json (same
schema as the other curated query files) and a build report next to it that
lists coverage per tier and every changed entity still without queries.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from parser.git_helper import GitHelper  # noqa: E402
from benchmarking.commit_sampler import sample_commit_pairs  # noqa: E402
from benchmarking.repository_snapshot import build_repository_snapshot  # noqa: E402
from benchmarking.query_validation import (  # noqa: E402
    MIN_QUERIES_PER_TARGET,
    audit_query_set,
    normalize_query_text,
    query_violations,
)
from embedder.context_builder import build_contextual_source  # noqa: E402
from extractor.semantic_modification import compute_source_changed_entities  # noqa: E402
from build_black_sanitized_dataset import DEFAULT_MODEL, Paraphraser, entity_purpose  # noqa: E402

DEFAULT_FIDELITY_MODEL = "BAAI/bge-base-en-v1.5"
DEFAULT_OUT = repo_root / "src" / "benchmarking" / "data" / "curated_queries_black_change_focused.json"
DEFAULT_DESCRIPTIONS = repo_root / "src" / "benchmarking" / "data" / "black_entity_descriptions.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def training_window(git_helper: GitHelper, settings: dict) -> List[str]:
    """Sampled commits exactly as run_experiment.py (harvest_commits + build_dataset)."""
    num, stride = int(settings["num_commits"]), int(settings["commit_stride"])
    history = git_helper.get_commit_history(count=num * stride, ref=settings.get("ref", "HEAD"))
    return history[::stride][:num]


def benchmark_window(git_helper: GitHelper, settings: dict) -> List[str]:
    """Sampled commits exactly as the benchmark runner (commit_sampler.sample_commit_pairs)."""
    pairs = sample_commit_pairs(
        git_helper,
        num_commits=int(settings["num_commits"]),
        sampling_mode=settings.get("sampling_mode", "adjacent"),
        commit_stride=int(settings.get("commit_stride", 1)),
        history_offset=int(settings.get("history_offset", 0)),
        ref=settings.get("ref", "HEAD"),
    )
    return [pairs[0].commit_before] + [p.commit_after for p in pairs] if pairs else []


def analyse_windows(git_helper: GitHelper, windows: Dict[str, List[str]]):
    """Per entity: newest source version, all source versions, and its tier."""
    snapshots = {}

    def snap(commit: str):
        if commit not in snapshots:
            print(f"  parsing {commit[:10]} ({len(snapshots) + 1})", end="\r")
            s = build_repository_snapshot(git_helper, commit)
            parser = getattr(s.parser, "_parser", s.parser)
            texts = {eid: build_contextual_source(parser.get_entity(eid) or e, parser)
                     for eid, e in s.entities.items()}
            snapshots[commit] = (s, parser, texts)
        return snapshots[commit]

    changed: Dict[str, Set[str]] = defaultdict(set)      # entity -> {"source", "context"}
    change_pairs: Dict[str, int] = defaultdict(int)       # entity -> #pairs it changed in
    neighbors: Set[str] = set()
    newest: Dict[str, Tuple[int, object]] = {}            # entity -> (order, RepositoryEntity)
    versions: Dict[str, Set[str]] = defaultdict(set)
    order = 0

    for name, commits in windows.items():
        print(f"{name} window: {len(commits)} sampled commits")
        for i, commit in enumerate(commits):
            s, parser, texts = snap(commit)
            order += 1
            for eid, e in s.entities.items():
                versions[eid].add(e.source_code)
                newest[eid] = (order, e)
            if i == 0:
                continue
            before_s, before_parser, before_texts = snap(commits[i - 1])
            modified_files = set(git_helper.get_modified_files(commits[i - 1], commit))
            src_changed = compute_source_changed_entities(before_parser, parser, modified_files)
            ctx_changed = {eid for eid, t in texts.items() if before_texts.get(eid) != t}
            for eid in src_changed:
                changed[eid].add("source")
            for eid in ctx_changed - set(src_changed):
                changed[eid].add("context")
            for eid in set(src_changed) | ctx_changed:
                change_pairs[eid] += 1
                if eid in parser.get_graph():
                    neighbors.update(parser.get_graph().predecessors(eid))
                    neighbors.update(parser.get_graph().successors(eid))
        print()

    tiers = {eid: ("changed" if eid in changed else "neighbor" if eid in neighbors else "other")
             for eid in newest}
    return {eid: e for eid, (_, e) in newest.items()}, versions, tiers, changed, change_pairs


def paraphrase_device(device: str) -> str:
    """Resolve "auto" to cuda/cpu for the fidelity scorer."""
    if device != "auto":
        return device
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def clean_for_all_versions(candidates: List[str], entity, sources: Set[str]) -> List[str]:
    """Candidates passing the leakage rules against every source version (dedup, order kept)."""
    kept, seen = [], set()
    for text in candidates:
        norm = normalize_query_text(text)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if all(not query_violations(text, entity.entity_id, entity.file_path, src) for src in sources):
            kept.append(" ".join(text.split()))
    return kept


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-path", default=str(repo_root / "workspace" / "black"))
    ap.add_argument("--training-settings", default=str(repo_root / "settings.json"))
    ap.add_argument("--benchmark-settings", default=str(repo_root / "benchmark_settings.json"))
    ap.add_argument("--descriptions", default=str(DEFAULT_DESCRIPTIONS),
                    help="JSON {entity_id: independently written description} for entities "
                         "without a usable docstring")
    ap.add_argument("--include-all", action="store_true",
                    help="Also cover entities that never change or neighbour a change")
    ap.add_argument("--paraphrase-model", default=DEFAULT_MODEL)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--queries-per-entity", type=int, default=MIN_QUERIES_PER_TARGET)
    ap.add_argument("--candidates", type=int, default=48, help="Paraphrase samples per entity")
    ap.add_argument("--fidelity-model", default=DEFAULT_FIDELITY_MODEL,
                    help="Independent embedding model scoring paraphrase-to-purpose similarity")
    ap.add_argument("--min-fidelity", type=float, default=0.80,
                    help="Minimum cosine similarity between a candidate and its purpose")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--report-only", action="store_true",
                    help="Analyse the windows and write the coverage report, no paraphrasing")
    ap.add_argument("--dump-missing", default=None,
                    help="Write source of target entities that have no purpose to this JSON file")
    args = ap.parse_args()

    git_helper = GitHelper(args.repo_path)
    windows = {
        "training": training_window(git_helper, _load_json(Path(args.training_settings))),
        "benchmark": benchmark_window(git_helper, _load_json(Path(args.benchmark_settings))),
    }
    entities, versions, tiers, changed, change_pairs = analyse_windows(git_helper, windows)
    wanted = {"changed", "neighbor"} | ({"other"} if args.include_all else set())
    targets = sorted(eid for eid, t in tiers.items() if t in wanted)

    descriptions = _load_json(Path(args.descriptions))
    purposes: Dict[str, Tuple[str, str]] = {}            # eid -> (source, text)
    for eid in targets:
        doc = entity_purpose(entities[eid].source_code, entities[eid].name)
        if doc:
            purposes[eid] = ("docstring", doc)
        elif descriptions.get(eid):
            purposes[eid] = ("description", descriptions[eid])
    no_purpose = [eid for eid in targets if eid not in purposes]

    if args.dump_missing:
        Path(args.dump_missing).write_text(json.dumps(
            {eid: {"tier": tiers[eid], "change": sorted(changed.get(eid, [])),
                   "source": entities[eid].source_code} for eid in no_purpose},
            indent=2), encoding="utf-8")
        print(f"Wrote {len(no_purpose)} entities without a purpose to {args.dump_missing}")

    queries: List[dict] = []
    dropped_few = []
    fidelity_rejected = 0
    if not args.report_only and purposes:
        ids = sorted(purposes)
        paraphraser = Paraphraser(args.paraphrase_model, args.device, args.seed)
        generated = paraphraser.generate([purposes[eid][1] for eid in ids], args.candidates)
        del paraphraser
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        clean = {}
        for eid, cands in zip(ids, generated):
            source, text = purposes[eid]
            pool = ([text] if source == "description" else []) + list(cands)
            clean[eid] = clean_for_all_versions(pool, entities[eid], versions[eid])

        # Fidelity filter (rule 5)
        from sentence_transformers import SentenceTransformer
        scorer = SentenceTransformer(args.fidelity_model, device=paraphrase_device(args.device))
        flat = [(eid, t) for eid in ids for t in clean[eid]]
        cand_vecs = scorer.encode([t for _, t in flat], normalize_embeddings=True, batch_size=64)
        purpose_vecs = dict(zip(ids, scorer.encode([purposes[eid][1] for eid in ids],
                                                   normalize_embeddings=True, batch_size=64)))
        fidelity_rejected = 0
        kept_by_entity = defaultdict(list)
        for (eid, text), vec in zip(flat, cand_vecs):
            if float(vec @ purpose_vecs[eid]) >= args.min_fidelity:
                kept_by_entity[eid].append(text)
            else:
                fidelity_rejected += 1
        clean = {eid: kept_by_entity.get(eid, []) for eid in ids}
        owners = defaultdict(set)
        for eid, texts in clean.items():
            for t in texts:
                owners[normalize_query_text(t)].add(eid)
        shared = {t for t, s in owners.items() if len(s) > 1}
        for eid in ids:
            texts = [t for t in clean[eid] if normalize_query_text(t) not in shared][:args.queries_per_entity]
            if len(texts) < args.queries_per_entity:
                dropped_few.append(eid)
                continue
            e = entities[eid]
            for text in texts:
                queries.append({
                    "query_id": f"black_cf_{len(queries) + 1:05d}",
                    "query_text": text,
                    "category": "changed_entity",
                    "target_entity_id": eid,
                    "target_entity_name": e.name,
                    "expected_behavior": "latest_snapshot",
                    "commit_after": "",
                    "file_path": e.file_path,
                    "entity_type": e.entity_type,
                })
        audit = audit_query_set(queries, {eid: entities[eid].source_code for eid in entities},
                                args.queries_per_entity)
        if not audit["ok"]:
            sys.exit(f"Built query set failed its own audit: {json.dumps(audit, indent=2)[:2000]}")

    covered = {q["target_entity_id"] for q in queries}
    old = {q["target_entity_id"] for q in _load_json(
        repo_root / "src/benchmarking/data/curated_queries_black_sanitized_5x.json") or []}

    def tier_stats(tier: str) -> dict:
        ids = [eid for eid in tiers if tiers[eid] == tier]
        return {
            "entities": len(ids),
            "covered_by_865_set": sum(eid in old for eid in ids),
            "have_docstring_purpose": sum(purposes.get(eid, ("",))[0] == "docstring" for eid in ids),
            "have_description": sum(purposes.get(eid, ("",))[0] == "description" for eid in ids),
            "covered_by_this_set": sum(eid in covered for eid in ids),
        }

    report = {
        "repo": args.repo_path,
        "windows": {k: {"first": v[0], "last": v[-1], "sampled_commits": len(v)} for k, v in windows.items()},
        "paraphrase_model": args.paraphrase_model,
        "seed": args.seed,
        "candidates_per_entity": args.candidates,
        "queries_per_entity": args.queries_per_entity,
        "tiers": {t: tier_stats(t) for t in ("changed", "neighbor", "other")},
        "changed_by_kind": {
            "source_only": sum(1 for k in changed.values() if k == {"source"}),
            "context_only": sum(1 for k in changed.values() if k == {"context"}),
            "both": sum(1 for k in changed.values() if k == {"source", "context"}),
        },
        "queries": len(queries),
        "targets_covered": len(covered),
        "targets_without_purpose": len(no_purpose),
        "targets_dropped_too_few_clean": len(dropped_few),
        "fidelity_model": args.fidelity_model,
        "min_fidelity": args.min_fidelity,
        "candidates_rejected_low_fidelity": fidelity_rejected,
        "uncovered_changed_entities": sorted(
            eid for eid in tiers if tiers[eid] == "changed" and eid not in covered),
    }
    out_path = Path(args.out)
    report_path = out_path.with_name(out_path.stem + "_build_report.json")
    if not args.report_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(queries, indent=2), encoding="utf-8")
        print(f"Saved {len(queries)} queries to {out_path}")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "uncovered_changed_entities"}, indent=2))
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()

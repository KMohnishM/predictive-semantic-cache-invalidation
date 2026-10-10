#!/usr/bin/env python3
"""Build the leakage-checked, paraphrased query set for psf/black.

For every entity in workspace/black at --ref (read from git, no checkout):
  1. Take the entity's docstring summary as its "purpose" (entities without a
     docstring have no independent description and are skipped).
  2. Generate candidate rewordings with a local paraphrase model
     (default: humarin/chatgpt_paraphraser_on_T5_base, runs offline after the
     first download).
  3. Keep only candidates that pass src/benchmarking/query_validation.py:
     no target name / name tokens / class / file name, no run of 4+ words copied
     from the entity's source, and not shared with another target.
  4. Keep entities that end up with >= --queries-per-entity clean queries
     (the ground-truth sign test needs >= 5 to reach p < 0.05); drop the rest.

Output: src/benchmarking/data/curated_queries_black_sanitized_5x.json (same schema
as the other curated query files) and a build report next to it.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))

from parser.git_helper import GitHelper  # noqa: E402
from benchmarking.repository_snapshot import build_repository_snapshot  # noqa: E402
from benchmarking.query_validation import (  # noqa: E402
    MIN_QUERIES_PER_TARGET,
    audit_query_set,
    first_violation_free,
    normalize_query_text,
)

DEFAULT_MODEL = "humarin/chatgpt_paraphraser_on_T5_base"
DEFAULT_OUT = repo_root / "src" / "benchmarking" / "data" / "curated_queries_black_sanitized_5x.json"


def entity_purpose(source_code: str, short_name: str) -> str:
    """Docstring summary (first paragraph, <= 2 sentences) with the entity's own name removed."""
    try:
        tree = ast.parse(textwrap.dedent(source_code))
    except SyntaxError:
        return ""
    if not tree.body or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return ""
    doc = ast.get_docstring(tree.body[0]) or ""
    paragraph = doc.strip().split("\n\n")[0]
    paragraph = " ".join(paragraph.split())
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    purpose = " ".join(sentences[:2])[:300]
    purpose = re.sub(r"`+", "", purpose)
    purpose = re.sub(r"\b" + re.escape(short_name) + r"\b", "this", purpose, flags=re.IGNORECASE)
    return purpose if len(purpose.split()) >= 3 else ""


class Paraphraser:
    """Local seq2seq paraphrase model (T5-style, "paraphrase: " prompt)."""

    def __init__(self, model_name: str, device: str, seed: int) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.torch = torch
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device).eval()
        torch.manual_seed(seed)

    def generate(self, texts, n_candidates: int, batch_size: int = 8):
        """Return a list of candidate lists, one per input text."""
        results = []
        for start in range(0, len(texts), batch_size):
            batch = [f"paraphrase: {t}" for t in texts[start:start + batch_size]]
            enc = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True,
                                 max_length=128).to(self.device)
            with self.torch.no_grad():
                out = self.model.generate(
                    **enc,
                    do_sample=True,
                    top_p=0.95,
                    temperature=1.1,
                    num_return_sequences=n_candidates,
                    max_length=96,
                    no_repeat_ngram_size=2,
                )
            decoded = self.tokenizer.batch_decode(out, skip_special_tokens=True)
            for i in range(len(batch)):
                results.append(decoded[i * n_candidates:(i + 1) * n_candidates])
            print(f"  paraphrased {min(start + batch_size, len(texts))}/{len(texts)}", end="\r")
        print()
        return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-path", default=str(repo_root / "workspace" / "black"))
    ap.add_argument("--ref", default="HEAD", help="Git ref to read entities from (no checkout is done)")
    ap.add_argument("--paraphrase-model", default=DEFAULT_MODEL)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--queries-per-entity", type=int, default=MIN_QUERIES_PER_TARGET)
    ap.add_argument("--candidates", type=int, default=24, help="Paraphrase samples generated per entity")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    black_repo = Path(args.repo_path)
    if not black_repo.exists():
        sys.exit(f"Error: {black_repo} does not exist")

    git_helper = GitHelper(str(black_repo))
    commit = git_helper._run_git_command(["rev-parse", args.ref])
    print(f"Reading entities from {black_repo} at {args.ref} ({commit[:10]}) — no checkout.")
    snapshot = build_repository_snapshot(git_helper, commit)
    entities = sorted(snapshot.entities.values(), key=lambda e: e.entity_id)
    print(f"Found {len(entities)} entities.")

    with_purpose = [(e, entity_purpose(e.source_code, e.name)) for e in entities]
    with_purpose = [(e, p) for e, p in with_purpose if p]
    print(f"{len(with_purpose)} entities have a docstring purpose to paraphrase.")

    paraphraser = Paraphraser(args.paraphrase_model, args.device, args.seed)
    candidates = paraphraser.generate([p for _, p in with_purpose], args.candidates)

    # Rules 1+2 per entity (keep a surplus so rule 3 can still leave enough).
    clean_by_entity = {}
    for (entity, _), cands in zip(with_purpose, candidates):
        clean_by_entity[entity.entity_id] = (
            entity,
            first_violation_free(cands, entity.entity_id, entity.file_path, entity.source_code),
        )

    # Rule 3: drop any text produced for more than one target.
    owners = defaultdict(set)
    for eid, (_, texts) in clean_by_entity.items():
        for t in texts:
            owners[normalize_query_text(t)].add(eid)
    shared = {t for t, s in owners.items() if len(s) > 1}

    queries = []
    dropped = {"no_docstring": len(entities) - len(with_purpose), "too_few_clean_queries": 0}
    for eid, (entity, texts) in clean_by_entity.items():
        texts = [t for t in texts if normalize_query_text(t) not in shared][:args.queries_per_entity]
        if len(texts) < args.queries_per_entity:
            dropped["too_few_clean_queries"] += 1
            continue
        for text in texts:
            queries.append({
                "query_id": f"black_para_{len(queries) + 1:05d}",
                "query_text": text,
                "category": "changed_entity",
                "target_entity_id": eid,
                "target_entity_name": entity.name,
                "expected_behavior": "latest_snapshot",
                "commit_after": "",
                "file_path": entity.file_path,
                "entity_type": entity.entity_type,
            })

    audit = audit_query_set(
        queries, {e.entity_id: e.source_code for e in entities}, args.queries_per_entity
    )
    if not audit["ok"]:
        sys.exit(f"Built query set failed its own audit: {json.dumps(audit, indent=2)[:2000]}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(queries, indent=2), encoding="utf-8")

    report = {
        "source_repo": str(black_repo),
        "ref": args.ref,
        "commit": commit,
        "paraphrase_model": args.paraphrase_model,
        "seed": args.seed,
        "candidates_per_entity": args.candidates,
        "queries_per_entity": args.queries_per_entity,
        "entities_total": len(entities),
        "entities_covered": audit["n_targets"],
        "queries": audit["n_queries"],
        "dropped_entities": dropped,
        "texts_dropped_as_shared": len(shared),
    }
    report_path = out_path.with_name(out_path.stem + "_build_report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"Saved {len(queries)} queries to {out_path}")


if __name__ == "__main__":
    main()

"""
GRIDSCI demo: predictive semantic cache invalidation on psf/black.

Runs entirely from committed/cached artifacts (no git checkout, no embedding):
  * the cached psf/black dataset (datasets/black_*_embedded_text_changed_*),
  * the Pipeline A model of run 20261015_150331,
  * the Pipeline B benchmark run benchmark_v1.0_seed13_a4032dce_cf4cc298.

Walkthrough:
  1. One real commit: what changed_only re-embeds vs what actually went stale,
     including an unedited caller whose embedded callee stub changed.
  2. Retrieval damage: benchmark queries whose target changed_only lost from
     the top 5, and where GRIDSCI ranked it.
  3. The numbers: re-embed coverage (psf/black, Django) and Pipeline B cost/loss.
  4. LlamaIndex: the PredictiveCacheFilter on the same commit, with and without
     the previous-commit parser.

Usage:
    python demo.py                 # interactive, pauses between steps
    python demo.py --no-pause      # run straight through
    python demo.py --html demo.html   # also write the interactive page (fills demo_template.html)
"""

import argparse
import difflib
import glob
import json
import logging
import os
import sys
import warnings
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(ROOT, "src"), ROOT]
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import joblib  # noqa: E402

from predictor.predictor import DriftPredictor, positive_class_proba  # noqa: E402
from embedder.context_builder import build_callee_stubs  # noqa: E402

BLACK_RUN = "results_all-MiniLM-L6-v2_contextual_commits60_stride5_cleanFalse_20261015_150331"
DJANGO_RUN = "results_all-MiniLM-L6-v2_contextual_commits100_stride200_cleanFalse_20261015_150710"
BENCH_RUN = "benchmark_v1.0_seed13_a4032dce_cf4cc298"
NAMES = {
    "predictive_ml": "GRIDSCI",
    "changed_only": "changed only",
    "fixed_hop_k1": "fixed hop k=1",
    "fixed_hop_k2": "fixed hop k=2",
    "fixed_hop": "fixed hop k=2",
    "weighted_bfs_decay": "weighted BFS decay",
    "pagerank_propagation": "PageRank",
    "full_reindex": "full re-index",
}

BOLD, DIM, RED, GREEN, CYAN, RESET = "\033[1m", "\033[2m", "\033[31m", "\033[32m", "\033[36m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    BOLD = DIM = RED = GREEN = CYAN = RESET = ""


def in_top(rank, k: int) -> bool:
    return rank is not None and rank <= k


def short(entity_id: str) -> str:
    return entity_id.split("/")[-1]


def header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 78}\n  {title}\n{'=' * 78}{RESET}")


class Demo:
    def __init__(self, pause: bool):
        self.pause = pause
        self.report = {}

    def wait(self) -> None:
        if self.pause:
            input(f"\n{DIM}[Enter] to continue...{RESET}")

    # ------------------------------------------------------------------ data
    def load(self) -> None:
        cache = glob.glob(os.path.join(ROOT, "datasets", "black_*_embedded_text_changed_*"))
        if not cache:
            sys.exit("No cached psf/black dataset in datasets/. Run Pipeline A on psf/black once to build it.")
        self.cache = cache[0]
        self.ds = joblib.load(os.path.join(self.cache, "dataset.joblib"))
        self.model = DriftPredictor.load_artifact(os.path.join(ROOT, "results", BLACK_RUN, "drift_predictor.pkl"))
        snaps = {os.path.basename(p)[:-7] for p in glob.glob(os.path.join(self.cache, "snapshots", "*.joblib"))}
        # Test pairs: both commits have cached parsers.
        self.pairs = [p for p in self.ds["features_history"] if p[0] in snaps and p[1] in snaps]

    def snapshot(self, commit: str):
        return joblib.load(os.path.join(self.cache, "snapshots", f"{commit}.joblib"))["parser"]

    def score(self, pair):
        feats = self.ds["features_history"][pair]
        X = feats.reindex(columns=self.model.feature_names, fill_value=0.0)
        proba = positive_class_proba(self.model.model, self.model.predict_proba(X.values))
        truth = self.ds["ground_truth_history"][pair]
        return feats, dict(zip(feats.index, proba)), truth

    # ---------------------------------------------------------- step 1
    def step_commit(self) -> None:
        header("1. One real commit: which vectors went stale?")
        best = None
        for pair in self.pairs:
            feats, proba, truth = self.score(pair)
            indirect = [e for e, y in truth.items() if y == 1 and feats.at[e, "own_source_changed"] == 0]
            if best is None or len(indirect) > len(best[3]):
                best = (pair, feats, proba, indirect, truth)
        pair, feats, proba, indirect, truth = best
        thr = self.model.decision_threshold
        needed = {e for e, y in truth.items() if y == 1}
        changed = {e for e in truth if feats.at[e, "own_source_changed"] == 1}
        gridsci = {e for e in truth if proba[e] >= thr}

        print(f"Commit pair {pair[0][:8]} -> {pair[1][:8]} ({len(truth)} entities, "
              f"{len(self.ds['modified_entities_history'][pair])} semantically edited)\n")
        print(f"  Entities whose embedded text changed (need re-embedding): {BOLD}{len(needed)}{RESET}")
        print(f"     of which edited directly : {len(needed & changed)}")
        print(f"     of which {BOLD}NOT in the diff{RESET}  : {len(indirect)}  "
              f"{DIM}(callers whose callee stub changed){RESET}\n")
        rows = []
        for name, chosen in (("changed only", changed), ("GRIDSCI", gridsci), ("full re-index", set(truth))):
            missed, extra = len(needed - chosen), len(chosen - needed)
            colour = RED if missed else GREEN
            print(f"  {name:14s} re-embeds {len(chosen):4d} ({len(chosen) / len(truth):6.1%})   "
                  f"{colour}missed {missed}{RESET}   extra {extra}")
            rows.append({"strategy": name, "reembedded": len(chosen), "share": len(chosen) / len(truth),
                         "missed": missed, "extra": extra})

        # The headline example: an unedited caller with the most changed stubs.
        example = max(indirect, key=lambda e: (feats.at[e, "context_stub_changed_count"], proba[e]))
        parser_a, parser_b = self.snapshot(pair[0]), self.snapshot(pair[1])
        stubs_a = build_callee_stubs(example, parser_a)
        stubs_b = build_callee_stubs(example, parser_b)
        changed_callees = sorted(c for c in set(stubs_a) | set(stubs_b) if stubs_a.get(c) != stubs_b.get(c))
        print(f"\n  {BOLD}Example:{RESET} {example}")
        print("    its own source did not change, so changed_only keeps its old vector.")
        print(f"    But its embedded text includes stubs of the functions it calls; {len(changed_callees)} changed:")
        diffs = []
        for callee in changed_callees[:2]:
            before, after = stubs_a.get(callee, "(absent)"), stubs_b.get(callee, "(absent)")
            diff = [l for l in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
                    if not l.startswith(("---", "+++", "@@"))]
            print(f"\n    callee {short(callee)}:")
            for line in diff:
                print(f"      {RED if line.startswith('-') else GREEN}{line}{RESET}")
            diffs.append({"callee": callee, "diff": diff})
        print(f"\n    GRIDSCI stale probability {BOLD}{proba[example]:.3f}{RESET} "
              f"(threshold {thr:.4f}) -> {GREEN}re-embedded{RESET}")

        # Call-graph slice for the HTML view: every stale entity, plus the
        # changed callees that made each unedited caller stale.
        nodes, edges = {}, []

        def node(eid, kind):
            nodes.setdefault(eid, {"id": eid, "name": short(eid).split("::")[-1], "file": eid.split("::")[0],
                                   "kind": kind, "needed": eid in needed, "changed_only": eid in changed,
                                   "gridsci": eid in gridsci, "proba": float(proba.get(eid, 0.0))})

        for eid in sorted(needed & changed):
            node(eid, "edited")
        for eid in sorted(indirect):
            node(eid, "indirect")
            sa, sb = build_callee_stubs(eid, parser_a), build_callee_stubs(eid, parser_b)
            for callee in sorted(c for c in set(sa) | set(sb) if sa.get(c) != sb.get(c)):
                node(callee, "edited" if callee in changed else "callee")
                edges.append({"from": callee, "to": eid})
        self.report["commit"] = {"pair": pair, "entities": len(truth), "needed": len(needed),
                                 "direct": len(needed & changed), "indirect": len(indirect), "rows": rows,
                                 "example": example, "probability": float(proba[example]),
                                 "threshold": float(thr), "diffs": diffs,
                                 "graph": {"nodes": list(nodes.values()), "edges": edges}}
        self.pair = pair
        self.wait()

    # ---------------------------------------------------------- step 2
    def step_queries(self) -> None:
        header("2. Retrieval damage: queries changed_only got wrong")
        rows = defaultdict(dict)
        path = os.path.join(ROOT, "benchmark_runs", BENCH_RUN, "per_query_results.jsonl")
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                rows[(r["query_id"], r["commit_after"])][r["strategy_name"]] = r
        def lost_at(strategy, k):
            return [by for by in rows.values() if strategy in by
                    and in_top(by[strategy]["baseline_rank"], k) and not in_top(by[strategy]["selective_rank"], k)]

        counts = {s: (len(lost_at(s, 1)), len(lost_at(s, 5))) for s in ("changed_only", "predictive_ml")}
        print("In the stateful replay (15 commit pairs, the cache carries over between commits):")
        for s, (l1, l5) in counts.items():
            colour = RED if l1 or l5 else GREEN
            print(f"  {NAMES[s]:13s} {colour}lost the #1 answer {l1:2d} times, a top-5 answer {l5:2d} times{RESET}")

        # Group changed_only's #1 losses by query: the same stale vector keeps
        # costing the right answer commit after commit.
        groups = defaultdict(list)
        for by in lost_at("changed_only", 1):
            groups[(by["changed_only"]["query_text"], by["changed_only"]["target_entity_name"])].append(by)
        print(f"\nThe #1 answer that changed_only lost, by query:\n")
        rank = lambda r: "not in top 10" if r is None or r > 10 else f"#{r}"
        shown = []
        for (query, target), hits in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:3]:
            co_ranks = sorted({rank(b["changed_only"]["selective_rank"]) for b in hits})
            ml_ranks = sorted({rank(b["predictive_ml"]["selective_rank"]) for b in hits if "predictive_ml" in b})
            print(f"  {BOLD}\"{query[:110]}\"{RESET}")
            print(f"    target {target}:  full re-index #1   {RED}changed only {', '.join(co_ranks)}{RESET}   "
                  f"{GREEN}GRIDSCI {', '.join(ml_ranks)}{RESET}   {DIM}(wrong in {len(hits)} consecutive "
                  f"commit{'s' if len(hits) > 1 else ''}){RESET}\n")
            shown.append({"query": query, "target": target, "full": "#1", "changed_only": ", ".join(co_ranks),
                          "gridsci": ", ".join(ml_ranks), "commits": len(hits)})

        # Rank of the headline query's target at every replayed commit.
        order = [p["commit_after"] for p in json.load(
            open(os.path.join(ROOT, "benchmark_runs", BENCH_RUN, "commit_pairs.json"), encoding="utf-8"))]
        timeline = []
        if shown:
            q0 = shown[0]["query"]
            for (qid, commit), by in rows.items():
                if "changed_only" in by and by["changed_only"]["query_text"] == q0:
                    timeline.append({"pair": order.index(commit) + 1,
                                     "full": by["changed_only"]["baseline_rank"],
                                     "changed_only": by["changed_only"]["selective_rank"],
                                     "gridsci": by.get("predictive_ml", {}).get("selective_rank")})
            timeline.sort(key=lambda t: t["pair"])
        self.report["queries"] = {"counts": {NAMES[s]: c for s, c in counts.items()}, "examples": shown,
                                  "timeline": timeline}
        self.wait()

    # ---------------------------------------------------------- step 3
    def step_numbers(self) -> None:
        header("3. The numbers")
        cov = {}
        for repo, run in (("psf/black", BLACK_RUN), ("Django", DJANGO_RUN)):
            summary = json.load(open(os.path.join(ROOT, "results", run, "reembed_coverage.json")))["summary"]
            needed = summary["predictive_ml"]["needed"]
            print(f"\n  Re-embed coverage, {repo} test pairs ({needed:,} entities needed re-embedding):")
            cov[repo] = []
            for name in ("predictive_ml", "changed_only", "fixed_hop_k1", "fixed_hop_k2",
                         "pagerank_propagation", "full_reindex"):
                s = summary[name]
                colour = RED if s["missed"] else GREEN
                print(f"    {NAMES[name]:15s} missed {colour}{s['missed']:6,}{RESET}   "
                      f"re-embedded {s['reembedded_fraction']:7.2%} of entities")
                cov[repo].append({"strategy": NAMES[name], "missed": s["missed"], "extra": s["extra"],
                                  "share": s["reembedded_fraction"]})

        # Pipeline B: Lost@5 per strategy from the per-query log (target in the
        # full re-index's top 5 but not the strategy's); update cost from the
        # benchmark's own summary table.
        lost5, checks5 = defaultdict(int), defaultdict(int)
        with open(os.path.join(ROOT, "benchmark_runs", BENCH_RUN, "per_query_results.jsonl"), encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if in_top(r["baseline_rank"], 5):
                    checks5[r["strategy_name"]] += 1
                    lost5[r["strategy_name"]] += not in_top(r["selective_rank"], 5)
        cost = {}
        with open(os.path.join(ROOT, "benchmark_runs", BENCH_RUN, "summary_report.md"), encoding="utf-8") as f:
            for line in f:
                cells = [c.strip(" `") for c in line.split("|")]
                if len(cells) > 3 and cells[1] in NAMES and cells[1] not in cost:
                    cost[cells[1]] = float(cells[2])
        print(f"\n  Stateful replay of 15 psf/black commit pairs (missed refreshes persist):")
        bench = []
        for s in ("changed_only", "predictive_ml", "fixed_hop", "full_reindex"):
            if s not in cost:
                continue
            c = cost[s]
            colour = RED if lost5[s] else GREEN
            print(f"    {NAMES[s]:15s} cost {c:7.2%}   {colour}lost top-5 results {lost5[s]:3d} / {checks5[s]:,}{RESET}")
            bench.append({"strategy": NAMES[s], "cost": c, "lost5": lost5[s], "checks5": checks5[s]})

        black_entities, django_entities = 568, 10249
        print(f"\n  Embedding calls per commit: psf/black ~{black_entities * 0.018:.0f} instead of {black_entities:,}; "
              f"Django ~{django_entities * 0.0533:.0f} instead of {django_entities:,}.")
        self.report["numbers"] = {"coverage": cov, "bench": bench}
        self.wait()

    # ---------------------------------------------------------- step 4
    def step_llama(self) -> None:
        header("4. Drop-in: LlamaIndex ingestion filter on the same commit")
        from llama_index_integration import LLAMA_INDEX_AVAILABLE, PredictiveCacheFilter, TextNode

        pair = self.pair
        parser_a, parser_b = self.snapshot(pair[0]), self.snapshot(pair[1])
        truth = self.ds["ground_truth_history"][pair]
        modified = self.ds["modified_entities_history"][pair]
        nodes = [TextNode(text=e.source_code, id_=eid, metadata={"cpg_id": eid})
                 for eid, e in parser_b.entities.items() if eid in truth]
        needed = {e for e, y in truth.items() if y == 1}
        print(f"  {len(nodes)} nodes enter the ingestion pipeline "
              f"({'llama-index' if LLAMA_INDEX_AVAILABLE else 'stand-in classes, llama-index not importable'}).\n")
        rows = []
        for label, previous in (("without previous-commit parser", None), ("with previous-commit parser", parser_a)):
            filt = PredictiveCacheFilter(self.model, repo_parser=parser_b, modified_entities=modified,
                                         previous_parser=previous)
            kept = {getattr(n, "id_", None) or n.id for n in filt(nodes)}
            caught = len(needed & kept)
            colour = GREEN if caught == len(needed) else RED
            print(f"  {label:32s} passes {len(kept):3d} nodes to the embedder   "
                  f"{colour}caught {caught}/{len(needed)} stale{RESET}")
            rows.append({"mode": label, "passed": len(kept), "caught": caught, "needed": len(needed)})
        print(f"\n  The other {len(nodes) - rows[-1]['passed']} nodes keep their cached vectors.")
        self.report["llama"] = {"nodes": len(nodes), "rows": rows}

    # ---------------------------------------------------------- html
    def write_html(self, path: str) -> None:
        """Fill demo_template.html with this run's data (one self-contained file)."""
        with open(os.path.join(ROOT, "demo_template.html"), encoding="utf-8") as f:
            page = f.read()
        # Escape "</" so no string in the data can close the <script> tag.
        data = json.dumps(self.report, default=str).replace("</", "<\\/")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page.replace("__DEMO_DATA__", data))
        print(f"\nHTML report written to {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-pause", action="store_true", help="Run without pausing between steps")
    ap.add_argument("--html", help="Also write a self-contained HTML report to this path")
    ap.add_argument("--skip-llama", action="store_true", help="Skip the LlamaIndex step")
    args = ap.parse_args()

    demo = Demo(pause=not args.no_pause)
    print(f"{BOLD}GRIDSCI demo{RESET} {DIM}(loading cached psf/black dataset and model...){RESET}")
    demo.load()
    demo.step_commit()
    demo.step_queries()
    demo.step_numbers()
    if not args.skip_llama:
        demo.step_llama()
    if args.html:
        demo.write_html(args.html)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Robustness of benchmark (Pipeline B) conclusions to the query workload.

The Wilson intervals in the benchmark report treat every query check as an
independent observation. They are not: each target entity has several queries
(five in the change-focused set) and is queried in every commit pair, so checks
on the same target are correlated. This script re-estimates the uncertainty by
resampling *targets* instead of queries, and checks how stable the strategy
comparison is.

Reported, for Lost@k (target in the full re-index top k but not in the
strategy's top k, over the queries whose target the full re-index finds):

  * per strategy: Lost@k with a Wilson interval (query-level, as in the report)
    and a target-level bootstrap interval, plus the design effect
    (bootstrap variance / binomial variance), the effective sample size, and a
    Wilson upper bound on the effective sample size. A strategy with no
    observed loss has no design effect of its own (and a degenerate bootstrap
    interval), so its bound uses the largest design effect of any strategy;
  * paired differences between strategies on the same resampled targets, with
    bootstrap intervals and the share of replicates in which the difference is
    > 0;
  * the smallest difference detectable at 80% power and alpha = 0.05 given the
    target-level standard error of each paired difference;
  * ranking stability: the share of bootstrap replicates that reproduce the
    observed ordering of strategies (by Lost@k, ties broken by update cost);
  * the effect of dropping short queries (--min-words).

Usage:
    python scripts/query_set_robustness.py benchmark_runs/<run>/per_query_results.jsonl \
        --k 5 --min-words 8 --out robustness_report.md
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

Z = 1.959964


def wilson(x: int, n: int):
    if n == 0:
        return float("nan"), float("nan")
    p = x / n
    den = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / den
    half = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def load(path: Path, k: int, min_words: int):
    """Per strategy and target: (lost, eligible) counts; plus mean update cost."""
    counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    cost = defaultdict(dict)
    total = defaultdict(int)
    for line in path.open(encoding="utf-8"):
        r = json.loads(line)
        s = r["strategy_name"]
        cost[s][r["commit_after"]] = r.get("updated_entity_fraction", float("nan"))
        if min_words and len(r.get("query_text", "").split()) < min_words:
            continue
        total[s] += 1
        base, sel = r.get("baseline_rank"), r.get("selective_rank")
        if base is None or base > k:
            continue  # not eligible: the full re-index does not find the target in the top k
        c = counts[s][r["target_entity_id"]]
        c[1] += 1
        c[0] += int(sel is None or sel > k)
    mean_cost = {s: float(np.mean(list(v.values()))) for s, v in cost.items()}
    return counts, mean_cost, total


def analyse(counts, mean_cost, n_boot: int, seed: int):
    strategies = sorted(counts, key=lambda s: mean_cost.get(s, 0.0))
    targets = sorted({t for s in strategies for t in counts[s]})
    lost = np.array([[counts[s].get(t, [0, 0])[0] for t in targets] for s in strategies], dtype=float)
    elig = np.array([[counts[s].get(t, [0, 0])[1] for t in targets] for s in strategies], dtype=float)

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(targets), size=(n_boot, len(targets)))
    boot = lost[:, idx].sum(axis=2) / np.maximum(elig[:, idx].sum(axis=2), 1)  # (strategies, n_boot)

    per = {}
    for i, s in enumerate(strategies):
        x, n = int(lost[i].sum()), int(elig[i].sum())
        p = x / n if n else float("nan")
        lo, hi = wilson(x, n)
        b_lo, b_hi = np.percentile(boot[i], [2.5, 97.5])
        binom_var = p * (1 - p) / n if n else float("nan")
        deff = float(np.var(boot[i]) / binom_var) if binom_var else float("nan")
        per[s] = dict(lost=x, eligible=n, rate=p, wilson=(lo, hi), bootstrap=(float(b_lo), float(b_hi)),
                      design_effect=deff, effective_n=(n / deff if deff and deff > 0 else float("nan")),
                      cost=mean_cost.get(s, float("nan")), targets=int((elig[i] > 0).sum()))

    known = [p["design_effect"] for p in per.values() if np.isfinite(p["design_effect"])]
    worst = max(known) if known else 1.0
    for p in per.values():
        deff = p["design_effect"] if np.isfinite(p["design_effect"]) else worst
        n_eff = p["eligible"] / deff if deff > 0 else p["eligible"]
        p["adjusted_upper"] = wilson(round(p["rate"] * n_eff), max(1, round(n_eff)))[1]
        p["adjusted_with"] = deff

    pairs = {}
    for i, a in enumerate(strategies):
        for j, b in enumerate(strategies):
            if j <= i:
                continue
            obs = per[a]["rate"] - per[b]["rate"]
            d = boot[i] - boot[j]
            se = float(np.std(d))
            pairs[(a, b)] = dict(diff=obs, ci=tuple(float(v) for v in np.percentile(d, [2.5, 97.5])),
                                 share_positive=float(np.mean(d > 0)), se=se, mde=(Z + 0.841621) * se)

    def order(rates):
        return tuple(sorted(strategies, key=lambda s: (round(rates[s], 12), per[s]["cost"])))

    observed = order({s: per[s]["rate"] for s in strategies})
    same = np.mean([order({s: boot[i][r] for i, s in enumerate(strategies)}) == observed
                    for r in range(n_boot)])
    return dict(strategies=strategies, per=per, pairs=pairs, observed_order=observed,
                ranking_stability=float(same), n_targets=len(targets))


def pct(v):
    return f"{100 * v:.2f}%"


def num(v, fmt):
    return format(v, fmt) if np.isfinite(v) else "–"


def report(path, k, n_boot, seed, full, filt, min_words, totals_full, totals_filt):
    lines = [f"# Query-set robustness: Lost@{k}", "",
             f"Source: `{path}`  ", f"Bootstrap: {n_boot} replicates over target entities, seed {seed}.", ""]
    for title, res, totals in [("All queries", full, totals_full),
                               (f"Queries with at least {min_words} words", filt, totals_filt)]:
        if res is None:
            continue
        lines += [f"## {title}", "",
                  f"{res['n_targets']} target entities with at least one eligible query; "
                  f"{next(iter(totals.values()))} query checks per strategy.", "",
                  f"| Strategy | Mean per-pair update cost | Lost@{k} | Wilson 95% (query-level) | Bootstrap 95% (target-level) | Design effect | Effective n | Adjusted upper bound |",
                  "|---|---|---|---|---|---|---|---|"]
        for s in res["strategies"]:
            p = res["per"][s]
            lines.append(f"| `{s}` | {pct(p['cost'])} | {p['lost']}/{p['eligible']:,} = {pct(p['rate'])} | "
                         f"[{pct(p['wilson'][0])}, {pct(p['wilson'][1])}] | "
                         f"[{pct(p['bootstrap'][0])}, {pct(p['bootstrap'][1])}] | "
                         f"{num(p['design_effect'], '.2f')} | {num(p['effective_n'], ',.0f')} | "
                         f"{pct(p['adjusted_upper'])} (design effect {p['adjusted_with']:.2f}) |")
        lines += ["", "Paired differences (row minus column strategy), target-level bootstrap:", "",
                  f"| Pair | Difference in Lost@{k} | 95% interval | Share of replicates > 0 | Smallest detectable difference (80% power) |",
                  "|---|---|---|---|---|"]
        for (a, b), d in res["pairs"].items():
            lines.append(f"| `{a}` − `{b}` | {pct(d['diff'])} | [{pct(d['ci'][0])}, {pct(d['ci'][1])}] | "
                         f"{d['share_positive']:.3f} | {pct(d['mde']) if d['se'] > 0 else '–'} |")
        lines += ["", f"Observed ordering (lowest Lost@{k} first, ties by update cost): "
                      + " < ".join(f"`{s}`" for s in res["observed_order"]),
                  f"Share of bootstrap replicates with the same ordering: {res['ranking_stability']:.3f}", ""]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("per_query_results", type=Path)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-words", type=int, default=0, help="also report with queries shorter than this dropped")
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", type=Path, default=Path("robustness_report.md"))
    args = ap.parse_args()

    counts, mean_cost, totals = load(args.per_query_results, args.k, 0)
    full = analyse(counts, mean_cost, args.bootstrap, args.seed)
    filt, totals_f = None, {}
    if args.min_words:
        counts_f, mean_cost_f, totals_f = load(args.per_query_results, args.k, args.min_words)
        filt = analyse(counts_f, mean_cost_f, args.bootstrap, args.seed)

    text = report(args.per_query_results, args.k, args.bootstrap, args.seed, full, filt, args.min_words,
                  totals, totals_f)
    args.out.write_text(text, encoding="utf-8")
    serial = {"k": args.k, "bootstrap": args.bootstrap, "seed": args.seed, "min_words": args.min_words}
    for name, res in [("all_queries", full), ("filtered", filt)]:
        if res is None:
            continue
        serial[name] = {
            "n_targets": res["n_targets"],
            "per_strategy": res["per"],
            "pairs": {f"{a} - {b}": d for (a, b), d in res["pairs"].items()},
            "observed_order": list(res["observed_order"]),
            "ranking_stability": res["ranking_stability"],
        }
    args.out.with_suffix(".json").write_text(json.dumps(serial, indent=2), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

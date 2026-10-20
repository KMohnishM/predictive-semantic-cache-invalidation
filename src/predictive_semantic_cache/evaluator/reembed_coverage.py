"""Re-embed coverage: of the entities that needed re-embedding, how many each
strategy actually re-embedded.

"Needed" is the positive training label of the commit pair (for
``label_source="embedded_text_changed"``: the entity's embedded text changed, so
its cached vector differs from a full re-index). Only labeled entities count,
so every strategy is scored on the same set.
"""

import json
from pathlib import Path
from typing import Dict, Iterable, List, Set

# Report / plot order: the proposed model first, then baselines by cost.
STRATEGY_ORDER = [
    "predictive_ml",
    "changed_only",
    "fixed_hop_k1",
    "fixed_hop_k2",
    "weighted_bfs_decay",
    "pagerank_propagation",
    "full_reindex",
]


def reembed_coverage_row(commit_a: str, commit_b: str, needed: Set[str], labeled: Set[str],
                         strategy_sets: Dict[str, Iterable[str]]) -> Dict:
    """Coverage of ``needed`` by each strategy's re-embed set for one commit pair."""
    strategies = {}
    for name, entities in strategy_sets.items():
        reembedded = set(entities) & labeled
        hit = len(reembedded & needed)
        strategies[name] = {
            "reembedded": len(reembedded),
            "reembedded_needed": hit,
            "missed": len(needed) - hit,
            "extra": len(reembedded) - hit,
        }
    return {
        "commit_before": commit_a,
        "commit_after": commit_b,
        "entities": len(labeled),
        "needed": len(needed),
        "strategies": strategies,
    }


def summarize_reembed_coverage(rows: List[Dict]) -> Dict[str, Dict]:
    """Totals per strategy over all commit pairs."""
    names = [s for s in STRATEGY_ORDER if any(s in r["strategies"] for r in rows)]
    names += sorted({s for r in rows for s in r["strategies"]} - set(names))
    summary = {}
    for name in names:
        per_pair = [(r, r["strategies"][name]) for r in rows if name in r["strategies"]]
        needed = sum(r["needed"] for r, _ in per_pair)
        entities = sum(r["entities"] for r, _ in per_pair)
        hit = sum(s["reembedded_needed"] for _, s in per_pair)
        reembedded = sum(s["reembedded"] for _, s in per_pair)
        summary[name] = {
            "needed": needed,
            "reembedded_needed": hit,
            "missed": needed - hit,
            "extra": reembedded - hit,
            "reembedded": reembedded,
            "entities": entities,
            "coverage": hit / needed if needed else 1.0,
            "reembedded_fraction": reembedded / entities if entities else 0.0,
            "pairs_with_misses": sum(1 for _, s in per_pair if s["missed"] > 0),
            "pairs": len(per_pair),
        }
    return summary


def save_reembed_coverage(rows: List[Dict], output_dir: Path) -> Dict[str, Dict]:
    """Write reembed_coverage.json (summary + per-pair rows) and reembed_coverage.md."""
    summary = summarize_reembed_coverage(rows)
    output_dir = Path(output_dir)
    with open(output_dir / "reembed_coverage.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "pairs": rows}, f, indent=2)

    names = list(summary)
    lines = [
        "# Re-embed coverage",
        "",
        "Of the entities that needed re-embedding on the test commit pairs, how many each strategy re-embedded.",
        "",
        "| Strategy | Needed | Re-embedded of needed | Missed | Pairs with misses | Extra re-embeds | Re-embedded % of entities |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in summary.items():
        lines.append(
            f"| `{name}` | {s['needed']:,} | {s['reembedded_needed']:,} ({s['coverage']:.2%}) | {s['missed']:,} | "
            f"{s['pairs_with_misses']}/{s['pairs']} | {s['extra']:,} | {s['reembedded_fraction']:.2%} |"
        )
    lines += [
        "",
        "## Per commit pair (re-embedded of needed)",
        "",
        "| Pair | Entities | Needed | " + " | ".join(f"`{n}`" for n in names) + " |",
        "|---|---|---|" + "---|" * len(names),
    ]
    for r in rows:
        cells = []
        for n in names:
            s = r["strategies"].get(n)
            cells.append(f"{s['reembedded_needed']}/{r['needed']}" if s else "–")
        lines.append(
            f"| {r['commit_before'][:8]} → {r['commit_after'][:8]} | {r['entities']:,} | {r['needed']:,} | "
            + " | ".join(cells) + " |"
        )
    (output_dir / "reembed_coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary

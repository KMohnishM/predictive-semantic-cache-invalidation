#!/usr/bin/env python3
"""Script to evaluate Semantic Coverage SC(e, Q) of current queries against synthetic repo."""

import sys
import io
from pathlib import Path
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))

from parser.git_helper import GitHelper
from parser.tree_sitter_repo_parser import TreeSitterRepoParser
from embedder.ground_truth import load_ground_truth_queries
from benchmarking.semantic_coverage import compute_semantic_coverage


def audit_semantic_coverage():
    print("=" * 90)
    print("[AUDIT] SEMANTIC COVERAGE SC(e, Q) AUDIT ON SYNTHETIC REPOSITORY")
    print("=" * 90)

    test_repo = repo_root / "test_repo_project1"
    git_helper = GitHelper(str(test_repo))
    git_helper.checkout_commit("main")

    parser = TreeSitterRepoParser(str(test_repo))
    parser.parse_directory(str(test_repo))
    entities = parser.get_all_entities()

    query_path = repo_root / "src" / "benchmarking" / "data" / "curated_queries_synthetic_5x.json"
    queries = load_ground_truth_queries(str(query_path))

    sc_results = compute_semantic_coverage(entities, queries)

    rows = []
    sc_values = []
    under_target_count = 0
    tau_target = 0.85

    for eid, res in sc_results.items():
        sc_values.append(res.coverage_ratio)
        if res.coverage_ratio < tau_target:
            under_target_count += 1

        rows.append({
            "Entity AST Name": eid,
            "Entity Type": res.entity_type,
            "Total Dimensions |D(e)|": res.total_dimensions,
            "Covered Dimensions": res.covered_dimensions,
            "Query Count |Q_e|": res.query_count,
            "Semantic Coverage SC(e, Q)": f"{res.coverage_ratio * 100:.1f}%",
            "SC Ratio": res.coverage_ratio,
            "Uncovered Dimensions": ", ".join(res.uncovered_dimension_names) if res.uncovered_dimension_names else "NONE (100% Covered)"
        })

    df_sc = pd.DataFrame(rows)
    mean_sc = sum(sc_values) / len(sc_values) if sc_values else 0.0

    print(f"\nTotal Parsed AST Entities: {len(entities)}")
    print(f"Total Evaluated Queries: {len(queries)}")
    print(f"Mean Semantic Coverage SC(e, Q): {mean_sc * 100:.2f}%")
    print(f"Entities Meeting Target SC >= {tau_target * 100:.0f}%: {len(entities) - under_target_count} / {len(entities)}")
    print(f"Entities Below Target SC < {tau_target * 100:.0f}%: {under_target_count} / {len(entities)}")

    print("\n[SAMPLE ENTITY SEMANTIC COVERAGE SCORES (First 15 Entities)]:")
    disp_cols = ["Entity AST Name", "Total Dimensions |D(e)|", "Query Count |Q_e|", "Semantic Coverage SC(e, Q)", "Uncovered Dimensions"]
    print(df_sc[disp_cols].head(15).to_string(index=False))

    # Output full report to CSV
    csv_out = repo_root / "results" / "semantic_coverage_audit.csv"
    csv_out.parent.mkdir(exist_ok=True)
    df_sc.to_csv(csv_out, index=False)
    print(f"\nFull Semantic Coverage audit saved to: {csv_out}")


if __name__ == "__main__":
    audit_semantic_coverage()

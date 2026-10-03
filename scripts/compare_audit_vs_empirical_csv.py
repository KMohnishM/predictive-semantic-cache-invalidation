#!/usr/bin/env python3
"""Compare documented entity evolution audit matrix (entity_evolution_audit.md)
against empirical ground truth CSV (ground_truth_perfect_sc_ast_entities.csv).
"""

import re
import sys
import io
from pathlib import Path
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

repo_root = Path(__file__).parent.parent.resolve()
csv_path = repo_root / "results" / "ground_truth_perfect_sc_ast_entities.csv"
audit_md_path = repo_root / "test_repo_project1" / "entity_evolution_audit.md"

df_emp = pd.read_csv(csv_path)

# Parse entity_evolution_audit.md
audit_text = audit_md_path.read_text(encoding="utf-8")

# Extract per-commit direct and dependency drift lists from markdown
commits_audit = {}

# Parse sections like "### Commit 1: ..."
commit_blocks = re.split(r"### Commit (\d+):", audit_text)

for k in range(1, len(commit_blocks), 2):
    c_num = int(commit_blocks[k])
    block = commit_blocks[k+1]
    
    direct_line = re.search(r"- \*\*Direct\*\*: (.*)", block)
    dep_line = re.search(r"- \*\*Dependency Drifts\*\*: (.*)", block)
    
    direct_items = []
    if direct_line:
        raw_d = direct_line.group(1)
        direct_items = [x.strip(" `") for x in raw_d.split(",") if x.strip(" `")]
        
    dep_items = []
    if dep_line:
        raw_dep = dep_line.group(1)
        dep_items = [x.strip(" `") for x in raw_dep.split(",") if x.strip(" `")]
        
    commits_audit[f"C{c_num}"] = {
        "direct": direct_items,
        "dependency": dep_items
    }

print("=" * 95)
print("[COMPARISON] DOCUMENTED EVOLUTION AUDIT MD vs EMPIRICAL 100% SC GROUND TRUTH CSV")
print("=" * 95)

# Match commit by commit
comparison_rows = []

for c_num in range(1, 10):
    c_key = f"C{c_num}"
    doc_direct = commits_audit.get(c_key, {}).get("direct", [])
    doc_dep = commits_audit.get(c_key, {}).get("dependency", [])
    doc_all_drifted = set(doc_direct + doc_dep)
    
    # Filter CSV for this commit transition
    df_c = df_emp[df_emp["Commit Pair"].str.startswith(f"C{c_num-1} ")]
    
    # Git direct edits in CSV
    emp_direct_eids = set(df_c[df_c["Is Direct Edit"] == "YES"]["Entity AST Name"])
    emp_pure_loo = set(df_c[df_c["Pure LOO Label"] == 1]["Entity AST Name"])
    emp_hybrid = set(df_c[df_c["Hybrid Label"] == 1]["Entity AST Name"])
    
    # Helper to match short names (e.g. "TokenValidator") to full AST names ("src/auth.py::TokenValidator")
    def match_short_names(short_names, full_eids):
        matched = set()
        for s in short_names:
            for f in full_eids:
                if s in f:
                    matched.add(f)
        return matched

    matched_doc_direct = match_short_names(doc_direct, df_c["Entity AST Name"])
    matched_doc_dep = match_short_names(doc_dep, df_c["Entity AST Name"])
    matched_doc_total = matched_doc_direct | matched_doc_dep

    # Calculate overlaps
    direct_match_cnt = len(matched_doc_direct.intersection(emp_direct_eids))
    hybrid_match_cnt = len(matched_doc_total.intersection(emp_hybrid))
    pure_loo_in_doc = len(emp_pure_loo.intersection(matched_doc_total))

    comparison_rows.append({
        "Commit Transition": f"C{c_num-1} -> C{c_num}",
        "Doc Direct Count": len(matched_doc_direct),
        "Emp Direct Count": len(emp_direct_eids),
        "Direct Match Count": direct_match_cnt,
        "Direct Match %": f"{(direct_match_cnt / len(matched_doc_direct) * 100):.1f}%" if matched_doc_direct else "N/A",
        "Doc Total Drifted": len(matched_doc_total),
        "Emp Hybrid Drifted": len(emp_hybrid),
        "Emp Pure LOO Drifted": len(emp_pure_loo),
        "Pure LOO in Doc Drifts": f"{pure_loo_in_doc} / {len(emp_pure_loo)}"
    })

df_comp = pd.DataFrame(comparison_rows)
print(df_comp.to_string(index=False))

print("\n" + "=" * 95)
print("OVERALL SUMMARY & CORRELATION ANALYSIS:")
print("=" * 95)

total_doc_direct = sum(r["Doc Direct Count"] for r in comparison_rows)
total_emp_direct = sum(r["Emp Direct Count"] for r in comparison_rows)
total_direct_match = sum(r["Direct Match Count"] for r in comparison_rows)

print(f"* Total Documented Direct Edits across C1..C9: {total_doc_direct}")
print(f"* Total Git Diff Direct AST Edits in CSV: {total_emp_direct}")
print(f"* Exact Direct AST Edit Match: {total_direct_match} / {total_doc_direct} ({total_direct_match/total_doc_direct*100:.1f}%)")

total_emp_pure = sum(r["Emp Pure LOO Drifted"] for r in comparison_rows)
pure_in_doc = sum(int(r["Pure LOO in Doc Drifts"].split(" / ")[0]) for r in comparison_rows)

print(f"* Empirical Pure LOO Operational Drifts: {total_emp_pure}")
print(f"* Pure LOO Drifts present in Documented Drift Set: {pure_in_doc} / {total_emp_pure} ({pure_in_doc/total_emp_pure*100:.1f}%)")

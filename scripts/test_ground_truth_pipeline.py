#!/usr/bin/env python3
"""Ground Truth Drift Audit Script under Stage 2 Strict Ground Truth (408 Perfect SC Queries, N >= 5).

Evaluates chronological commit transitions (C0 -> C9) using the 408-query dataset
and strict ground-truth labeling engine (binomtest + strict displacement check).
"""

import sys
import io
from pathlib import Path
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))

from parser.git_helper import GitHelper
from parser.tree_sitter_repo_parser import TreeSitterRepoParser
from embedder.embedding_manager import EmbeddingManager
from embedder.ground_truth import (
    load_ground_truth_queries,
    compute_leave_one_out_scores,
    compute_strict_ground_truth,
)


def run_strict_ground_truth_test():
    print("=" * 95)
    print("[STAGE 2/3 TEST] STRICT GROUND TRUTH DRIFT AUDIT (408 QUERIES, N >= 5)")
    print("=" * 95)

    test_repo_path = repo_root / "test_repo_project1"
    git_helper = GitHelper(str(test_repo_path))
    git_helper.checkout_commit("main")
    
    commits = git_helper.get_commit_history(count=10)

    query_path = repo_root / "src" / "benchmarking" / "data" / "curated_queries_sanitized_5x.json"
    if not query_path.exists():
        query_path = repo_root / "src" / "benchmarking" / "data" / "curated_queries_perfect_sc.json"
    queries = load_ground_truth_queries(str(query_path))
    print(f"\nLoaded {len(queries)} queries with N >= 5 queries per entity from {query_path.name}")
    print(f"Target Repository: {test_repo_path}")
    print(f"Total Chronological Commits: {len(commits)}")

    embedder = EmbeddingManager(model_name="sentence-transformers/all-MiniLM-L6-v2", device="cpu")

    query_embeddings = {
        q.query_id: embedder.generate_embedding(q.query_id, q.query_text)
        for q in queries
    }

    all_commit_audits = {}
    master_records = []

    for i in range(1, len(commits)):
        commit_a = commits[i-1]
        commit_b = commits[i]
        pair_label = f"C{i-1} ({commit_a[:7]}) -> C{i} ({commit_b[:7]})"

        git_helper.checkout_commit(commit_a)
        parser_a = TreeSitterRepoParser(str(test_repo_path))
        parser_a.parse_directory(str(test_repo_path))
        sources_a = {e.entity_id: e.source_code for e in parser_a.get_all_entities()}
        embeddings_a = embedder.generate_embeddings_batch(sources_a)

        git_helper.checkout_commit(commit_b)
        parser_b = TreeSitterRepoParser(str(test_repo_path))
        parser_b.parse_directory(str(test_repo_path))
        entities_b = parser_b.get_all_entities()
        sources_b = {e.entity_id: e.source_code for e in entities_b}
        embeddings_b = embedder.generate_embeddings_batch(sources_b)

        modified_files = git_helper.get_modified_files(commit_a, commit_b)
        direct_modified = {
            eid for eid, ent in parser_b.entities.items() if ent.file_path in modified_files
        }

        loo_results = compute_leave_one_out_scores(
            embeddings_before=embeddings_a,
            embeddings_after=embeddings_b,
            queries=queries,
            query_embeddings=query_embeddings,
            top_k=10,
        )

        gt_labels = compute_strict_ground_truth(loo_results, alpha=0.05, min_queries=5)

        commit_rows = []
        for eid, label_obj in gt_labels.items():
            is_direct = eid in direct_modified
            # Operational rank displacement ground truth label
            strict_drift = 1 if (label_obj.is_covered and label_obj.label == 1) else 0

            rec = {
                "Commit Pair": pair_label,
                "Entity AST Name": eid,
                "File Path": parser_b.entities[eid].file_path if eid in parser_b.entities else "",
                "Entity Type": parser_b.entities[eid].entity_type if eid in parser_b.entities else "",
                "Is Direct Edit": "YES" if is_direct else "NO",
                "Strict Ground Truth Drifted": "DRIFTED" if strict_drift else "NOT DRIFTED",
                "Strict Label": strict_drift,
                "Displaced Queries": label_obj.displaced_query_count,
                "Evaluated Queries": label_obj.evaluated_query_count,
                "Positive Deltas": label_obj.positive_delta_count,
                "Mean Delta nDCG": round(label_obj.mean_ndcg_delta, 4),
                "p-value": round(label_obj.p_value, 4),
                "Is Covered": "YES" if label_obj.is_covered else "NO",
            }
            commit_rows.append(rec)
            master_records.append(rec)

        df_c = pd.DataFrame(commit_rows)
        all_commit_audits[pair_label] = df_c

    for bname in ["main", "master"]:
        if git_helper.checkout_commit(bname):
            break

    df_master = pd.DataFrame(master_records)

    csv_path = repo_root / "results" / "ground_truth_sanitized_strict_entities.csv"
    csv_path.parent.mkdir(exist_ok=True)
    df_master.to_csv(csv_path, index=False)
    print(f"\nSaved Strict Ground Truth Dataset to: {csv_path}\n")

    summary_rows = []
    for pair, df_c in all_commit_audits.items():
        n_total = len(df_c)
        n_direct = (df_c["Is Direct Edit"] == "YES").sum()
        n_strict = (df_c["Strict Label"] == 1).sum()
        summary_rows.append({
            "Commit Transition": pair,
            "Total AST Entities": n_total,
            "Direct Edits (Git Diff Feature X)": n_direct,
            "Strict Ground Truth (Target Y=1)": f"{n_strict} ({n_strict/n_total*100:.1f}%)",
        })

    df_summary = pd.DataFrame(summary_rows)
    print(df_summary.to_string(index=False))

    print("\nTotal Evaluated Entity-Commit Pairs:", len(df_master))
    print(f"Total Strict Positive Labels Y=1: {(df_master['Strict Label'] == 1).sum()} / {len(df_master)} ({(df_master['Strict Label'] == 1).mean()*100:.2f}%)")


if __name__ == "__main__":
    run_strict_ground_truth_test()

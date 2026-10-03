#!/usr/bin/env python3
"""Script to evaluate ground truth using dynamic commit-diff queries extracted directly from snapshot code & docstring updates."""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add src to path
repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))

from parser.git_helper import GitHelper
from parser.tree_sitter_repo_parser import TreeSitterRepoParser
from embedder.embedding_manager import EmbeddingManager
from embedder.ground_truth import compute_leave_one_out_scores, binarize_ground_truth
from benchmarking.query_sources import build_synthetic_queries
from benchmarking.types import RepositorySnapshot, RepositoryEntity, CommitPair

def run_dynamic_diff_query_test():
    print("=" * 90)
    print("[TEST] DYNAMIC COMMIT-DIFF QUERY GROUND TRUTH EVALUATION")
    print("=" * 90)

    test_repo_path = repo_root / "test_repo_project1"
    git_helper = GitHelper(str(test_repo_path))
    git_helper.checkout_commit("main")
    raw_commits = git_helper.get_commit_history(count=10)
    commits = list(reversed(raw_commits))  # Chronological order C0 -> C9

    embedder = EmbeddingManager(model_name="sentence-transformers/all-MiniLM-L6-v2", device="cpu")

    summary_rows = []

    for i in range(1, len(commits)):
        commit_a = commits[i-1]
        commit_b = commits[i]
        pair_label = f"C{i-1} ({commit_a[:7]}) -> C{i} ({commit_b[:7]})"

        print(f"\nEvaluating Transition: {pair_label}")

        # Pre-commit C_a
        git_helper.checkout_commit(commit_a)
        parser_a = TreeSitterRepoParser(str(test_repo_path))
        parser_a.parse_directory(str(test_repo_path))
        sources_a = {e.entity_id: e.source_code for e in parser_a.get_all_entities()}
        embeddings_a = embedder.generate_embeddings_batch(sources_a)

        # Post-commit C_b
        git_helper.checkout_commit(commit_b)
        parser_b = TreeSitterRepoParser(str(test_repo_path))
        parser_b.parse_directory(str(test_repo_path))
        sources_b = {e.entity_id: e.source_code for e in parser_b.get_all_entities()}
        embeddings_b = embedder.generate_embeddings_batch(sources_b)

        # Build dynamic queries from post-commit C_b snapshot code & docstrings
        snapshot_entities = {}
        for eid, e in parser_b.entities.items():
            name = eid.split("::")[-1]
            snapshot_entities[eid] = RepositoryEntity(
                entity_id=eid,
                entity_type=e.entity_type,
                file_path=e.file_path,
                lineno=e.lineno,
                end_lineno=e.end_lineno,
                name=name,
                source_code=e.source_code,
            )


        snapshot_b = RepositorySnapshot(commit_hash=commit_b, entities=snapshot_entities)
        cp = CommitPair(commit_before=commit_a, commit_after=commit_b, index=i)

        modified_files = git_helper.get_modified_files(commit_a, commit_b)
        direct_modified = {eid for eid, ent in parser_b.entities.items() if ent.file_path in modified_files}

        dynamic_queries = build_synthetic_queries(
            snapshot=snapshot_b,
            commit_pair=cp,
            max_queries_per_entity=3,
            modified_entity_ids=direct_modified,
            repo_graph=parser_b.get_graph()
        )

        # Embed dynamic queries
        query_embeddings = {
            q.query_id: embedder.generate_embedding(q.query_id, q.query_text)
            for q in dynamic_queries
        }

        # LOO Rank displacement
        loo_results = compute_leave_one_out_scores(
            embeddings_before=embeddings_a,
            embeddings_after=embeddings_b,
            queries=dynamic_queries,
            query_embeddings=query_embeddings,
            top_k=10
        )

        gt_labels = binarize_ground_truth(loo_results, alpha=0.05, min_nonzero_queries=1)

        drifted_count = sum(1 for label_obj in gt_labels.values() if label_obj.label == 1 or label_obj.entity_id in direct_modified)
        total_count = len(gt_labels)

        summary_rows.append({
            "Commit Transition": pair_label,
            "Dynamic Queries Built": len(dynamic_queries),
            "Direct Edits": len(direct_modified),
            "Total Entities": total_count,
            "Drifted Entities (Y_i=1)": drifted_count,
            "Drift Rate (%)": f"{(drifted_count / total_count) * 100:.1f}%"
        })

    git_helper.checkout_commit("main")

    df_sum = pd.DataFrame(summary_rows)
    print("\n" + "=" * 90)
    print("DYNAMIC COMMIT-DIFF QUERY GROUND TRUTH SUMMARY MATRIX")
    print("=" * 90)
    print(df_sum.to_string(index=False))

if __name__ == "__main__":
    run_dynamic_diff_query_test()

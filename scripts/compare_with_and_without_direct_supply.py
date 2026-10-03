#!/usr/bin/env python3
"""Comparative script evaluating Pure LOO Ground Truth (WITHOUT supply of direct change)
versus Hybrid Ground Truth (WITH supply of direct change).
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Add src to path
repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))

from parser.git_helper import GitHelper
from parser.tree_sitter_repo_parser import TreeSitterRepoParser
from embedder.embedding_manager import EmbeddingManager
from embedder.ground_truth import compute_leave_one_out_scores, binarize_ground_truth
from extractor.feature_extractor import FeatureExtractor
from extractor.gtd import GraphTransitionDescriptor
from benchmarking.query_sources import build_synthetic_queries
from benchmarking.types import RepositorySnapshot, RepositoryEntity, CommitPair

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix


def run_comparison():
    print("=" * 90)
    print("[COMPARE] PURE LOO (WITHOUT DIRECT SUPPLY) VS HYBRID (WITH DIRECT SUPPLY)")
    print("=" * 90)

    test_repo_path = repo_root / "test_repo_project1"
    git_helper = GitHelper(str(test_repo_path))
    git_helper.checkout_commit("main")
    raw_commits = git_helper.get_commit_history(count=10)
    commits = list(reversed(raw_commits))  # Chronological order C0 -> C9

    embedder = EmbeddingManager(model_name="sentence-transformers/all-MiniLM-L6-v2", device="cpu")

    all_features = []
    pure_loo_labels = []
    hybrid_labels = []
    direct_flags = []

    modification_history = {}
    previous_drifts = {}
    parsers_history = {}
    embeddings_history = {}

    for commit in commits:
        git_helper.checkout_commit(commit)
        parser = TreeSitterRepoParser(str(test_repo_path))
        parser.parse_directory(str(test_repo_path))
        parsers_history[commit] = parser

        entities = parser.get_all_entities()
        sources = {e.entity_id: e.source_code for e in entities}
        if sources:
            embeddings_history[commit] = embedder.generate_embeddings_batch(sources)
        else:
            embeddings_history[commit] = {}

    for i in range(1, len(commits)):
        commit_a = commits[i-1]
        commit_b = commits[i]
        pair_label = f"C{i-1} ({commit_a[:7]}) -> C{i} ({commit_b[:7]})"

        emb_a = embeddings_history.get(commit_a, {})
        emb_b = embeddings_history.get(commit_b, {})
        if not emb_a or not emb_b:
            continue

        drifts = embedder.compute_all_drifts(emb_a, emb_b)
        parser_a = parsers_history[commit_a]
        parser_b = parsers_history[commit_b]

        gtd = GraphTransitionDescriptor()
        gtd.compute(parser_a=parser_a, parser_b=parser_b, drifts=drifts)

        modified_files = git_helper.get_modified_files(commit_a, commit_b)
        direct_modified = set()
        for eid, ent in parser_b.entities.items():
            if ent.file_path in modified_files:
                direct_modified.add(eid)

        fe = FeatureExtractor(parser_b)
        entity_ids = [eid for eid in drifts.keys() if eid in parser_b.get_graph()]
        if not entity_ids:
            continue

        df = fe.extract_features_batch(
            entity_ids, commit_a, commit_b, direct_modified,
            modification_history, previous_drifts, git_helper, gtd=gtd
        )

        for eid in direct_modified:
            fe.update_modification_history(eid, commit_b, modification_history)
        for eid, d in drifts.items():
            previous_drifts[eid] = d

        # Build dynamic queries from post-commit C_b snapshot
        snapshot_entities = {}
        for eid, e in parser_b.entities.items():
            name = eid.split("::")[-1]
            snapshot_entities[eid] = RepositoryEntity(
                entity_id=eid, entity_type=e.entity_type, file_path=e.file_path,
                lineno=e.lineno, end_lineno=e.end_lineno, name=name, source_code=e.source_code
            )

        snapshot_b = RepositorySnapshot(commit_hash=commit_b, entities=snapshot_entities)
        cp = CommitPair(commit_before=commit_a, commit_after=commit_b, index=i)

        dynamic_queries = build_synthetic_queries(
            snapshot=snapshot_b, commit_pair=cp, max_queries_per_entity=3,
            modified_entity_ids=direct_modified, repo_graph=parser_b.get_graph()
        )

        query_embeddings = {
            q.query_id: embedder.generate_embedding(q.query_id, q.query_text)
            for q in dynamic_queries
        }

        loo_results = compute_leave_one_out_scores(
            embeddings_before=emb_a, embeddings_after=emb_b,
            queries=dynamic_queries, query_embeddings=query_embeddings, top_k=10
        )

        gt_labels = binarize_ground_truth(loo_results, alpha=0.05, min_nonzero_queries=1)

        # 1. Pure LOO Label (Without Direct Supply): Only Y_i=1 from rank displacement
        pure_y = [1 if (gt_labels.get(eid) and gt_labels[eid].label == 1) else 0 for eid in df.index]

        # 2. Hybrid Label (With Direct Supply): Y_i=1 if Direct Edit OR LOO rank displacement
        hybrid_y = [1 if (eid in direct_modified or (gt_labels.get(eid) and gt_labels[eid].label == 1)) else 0 for eid in df.index]

        is_direct_vec = [1 if eid in direct_modified else 0 for eid in df.index]

        df.index = [f"{commit_a[:7]}_{commit_b[:7]}::{eid}" for eid in df.index]

        all_features.append(df)
        pure_loo_labels.extend(pure_y)
        hybrid_labels.extend(hybrid_y)
        direct_flags.extend(is_direct_vec)

    git_helper.checkout_commit("main")

    X_df = pd.concat(all_features)
    y_pure = np.array(pure_loo_labels)
    y_hybrid = np.array(hybrid_labels)
    y_direct = np.array(direct_flags)

    print(f"\nTotal Dataset Rows (N): {len(X_df)}")
    print(f"  • Pure LOO Positives (Without Direct Supply): {np.sum(y_pure)} / {len(y_pure)} ({np.mean(y_pure):.2%})")
    print(f"  • Hybrid Positives   (With Direct Supply):    {np.sum(y_hybrid)} / {len(y_hybrid)} ({np.mean(y_hybrid):.2%})")
    print(f"  • Direct Edits Only  (Git Diff):               {np.sum(y_direct)} / {len(y_direct)} ({np.mean(y_direct):.2%})")

    # Train / Test Split (70/30)
    split_idx = int(len(X_df) * 0.7)
    X_train_raw, X_test_raw = X_df.iloc[:split_idx], X_df.iloc[split_idx:]
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced"),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42),
        "Extra Trees": ExtraTreesClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced"),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    }

    comparison_results = []

    for paradigm_name, y_all in [("Pure LOO (Without Direct Supply)", y_pure), ("Hybrid (With Direct Supply)", y_hybrid)]:
        y_tr, y_te = y_all[:split_idx], y_all[split_idx:]

        for m_name, clf in models.items():
            clf.fit(X_train, y_tr)
            y_pred = clf.predict(X_test)
            if hasattr(clf, "predict_proba"):
                probs = clf.predict_proba(X_test)
                y_prob = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
            else:
                y_prob = y_pred.astype(float)

            acc = accuracy_score(y_te, y_pred)
            prec = precision_score(y_te, y_pred, zero_division=0)
            rec = recall_score(y_te, y_pred, zero_division=0)
            f1 = f1_score(y_te, y_pred, zero_division=0)
            try:
                roc_auc = roc_auc_score(y_te, y_prob)
            except Exception:
                roc_auc = 0.5

            cm = confusion_matrix(y_te, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
            update_pct = (np.sum(y_pred) / len(y_pred)) * 100.0

            comparison_results.append({
                "Paradigm": paradigm_name,
                "Model": m_name,
                "Accuracy": round(acc, 4),
                "Precision": round(prec, 4),
                "Recall": round(rec, 4),
                "F1-Score": round(f1, 4),
                "ROC-AUC": round(roc_auc, 4),
                "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                "Update %": f"{update_pct:.2f}%"
            })

    df_comp = pd.DataFrame(comparison_results)

    print("\n" + "=" * 90)
    print("PARADIGM COMPARISON: PURE LOO VS HYBRID GROUND TRUTH")
    print("=" * 90)
    print(df_comp.to_string(index=False))

    out_dir = Path("results/paradigm_comparison")
    out_dir.mkdir(parents=True, exist_ok=True)
    df_comp.to_csv(out_dir / "paradigm_comparison.csv", index=False)

    # Plot comparison bar chart
    plt.figure(figsize=(12, 6))
    sns.barplot(data=df_comp, x="Model", y="F1-Score", hue="Paradigm", palette="Set1")
    plt.xticks(rotation=15)
    plt.title("F1-Score Comparison: Pure LOO (No Direct Supply) vs Hybrid Ground Truth", fontsize=13, fontweight="bold")
    plt.ylim(0, 1.1)
    plt.tight_layout()
    plt.savefig(out_dir / "f1_score_paradigm_comparison.png", dpi=300)
    plt.close()

    print(f"\nSaved paradigm comparison plot & CSV report to: {out_dir}")

if __name__ == "__main__":
    run_comparison()

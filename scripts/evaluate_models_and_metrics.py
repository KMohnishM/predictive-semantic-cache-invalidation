#!/usr/bin/env python3
"""Stage 4 Supervised ML Retraining and Pareto Frontier Evaluation Script.

Trains 8 ML Classifiers on input feature matrix X (is_modified, ast_diff, degree, complexity)
to predict Stage 2 Strict Ground Truth Target Y_strict (from ground_truth_sanitized_strict_entities.csv).

Evaluates cost-quality Pareto Frontier curves: Retrieval Recall@10 vs. % Entities Re-indexed.
"""

import sys
import io
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

repo_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(repo_root / "src"))

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

from parser.git_helper import GitHelper
from parser.tree_sitter_repo_parser import TreeSitterRepoParser
from extractor.feature_extractor import FeatureExtractor
from extractor.gtd import GraphTransitionDescriptor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_stage4_ml_evaluation():
    print("=" * 95)
    print("[STAGE 4] SUPERVISED ML RETRAIN & PARETO FRONTIER EVALUATION (STRICT TARGET Y)")
    print("=" * 95)

    test_repo = repo_root / "test_repo_project1"
    git_helper = GitHelper(str(test_repo))
    original_ref = git_helper.get_checkout_ref()
    try:
        _run_stage4(git_helper, test_repo)
    finally:
        # The commit loop below checks out every commit; restore the checkout.
        git_helper.checkout_commit(original_ref)


def _run_stage4(git_helper, test_repo):
    commits = git_helper.get_commit_history(count=10, ref="main")

    # Load Strict Ground Truth Target Y
    gt_csv_path = repo_root / "results" / "ground_truth_sanitized_strict_entities.csv"
    if not gt_csv_path.exists():
        gt_csv_path = repo_root / "results" / "ground_truth_perfect_sc_ast_entities.csv"

    df_gt = pd.read_csv(gt_csv_path)
    print(f"Loaded {len(df_gt)} entity-commit pairs from {gt_csv_path.name}")
    print(f"Total Strict Positive Labels Y=1: {(df_gt['Strict Label'] == 1).sum()} / {len(df_gt)} ({(df_gt['Strict Label'] == 1).mean()*100:.2f}%)")

    parsers_history = {}
    for commit in commits:
        git_helper.checkout_commit(commit)
        parser = TreeSitterRepoParser(str(test_repo))
        parser.parse_directory(str(test_repo))
        parsers_history[commit] = parser

    X_dfs = []
    y_list = []

    modification_history = {}
    previous_drifts = {}

    for i in range(1, len(commits)):
        commit_a = commits[i-1]
        commit_b = commits[i]

        parser_a = parsers_history[commit_a]
        parser_b = parsers_history[commit_b]

        feature_extractor = FeatureExtractor(parser_b, git_helper=git_helper, commit_a=commit_a, commit_b=commit_b)

        modified_files = git_helper.get_modified_files(commit_a, commit_b)
        direct_modified = {
            eid for eid, ent in parser_b.entities.items() if ent.file_path in modified_files
        }

        # Filter GT rows for this pair
        df_c = df_gt[df_gt["Commit Pair"].str.startswith(f"C{i-1} ")]
        gt_map = dict(zip(df_c["Entity AST Name"], df_c["Strict Label"]))

        gtd = GraphTransitionDescriptor()
        dummy_drifts = {eid: (0.5 if eid in direct_modified else 0.0) for eid in parser_b.entities}
        gtd.compute(parser_a=parser_a, parser_b=parser_b, drifts=dummy_drifts)

        entity_ids = sorted(list(parser_b.entities.keys()))

        df_feats = feature_extractor.extract_features_batch(
            entity_ids=entity_ids,
            commit_a=commit_a,
            commit_b=commit_b,
            modified_entities=direct_modified,
            modification_history=modification_history,
            previous_drifts=previous_drifts,
            git_helper=git_helper,
            gtd=gtd
        )

        for eid in df_feats.index:
            if eid in gt_map:
                X_dfs.append(df_feats.loc[[eid]])
                y_list.append(gt_map[eid])

        for eid in direct_modified:
            feature_extractor.update_modification_history(eid, commit_b, modification_history)

    df_X = pd.concat(X_dfs)
    y = np.array(y_list)

    print(f"\nConstructed Feature Matrix X shape: {df_X.shape}, Target y shape: {y.shape}")

    # Time-Series Train/Test split (first 70% train, last 30% test). The scaler is
    # fit on the training rows only so no test statistics leak into training.
    split_idx = int(len(df_X) * 0.70)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(df_X.iloc[:split_idx])
    X_test = scaler.transform(df_X.iloc[split_idx:])
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"Train Set: {len(y_train)} samples (y=1: {y_train.sum()}) | Test Set: {len(y_test)} samples (y=1: {y_test.sum()})")

    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "Extra Trees": ExtraTreesClassifier(n_estimators=100, random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "SVC": SVC(probability=True, random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=5),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "MLP Classifier": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
    }

    eval_results = []

    for name, clf in models.items():
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1] if hasattr(clf, "predict_proba") else y_pred

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        try:
            roc = roc_auc_score(y_test, y_prob)
        except Exception:
            roc = 0.5

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        reindex_cost_pct = (y_pred.sum() / len(y_test)) * 100

        eval_results.append({
            "Model / Strategy": name,
            "Accuracy": round(acc, 4),
            "Precision": round(prec, 4),
            "Recall": round(rec, 4),
            "F1-Score": round(f1, 4),
            "ROC-AUC": round(roc, 4),
            "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "Re-index Cost %": f"{reindex_cost_pct:.2f}%"
        })

    # Baseline 1: Full Re-index (Upper bound: predicts all 1)
    y_full = np.ones_like(y_test)
    eval_results.append({
        "Model / Strategy": "Baseline: Full Re-index",
        "Accuracy": round(accuracy_score(y_test, y_full), 4),
        "Precision": round(precision_score(y_test, y_full, zero_division=0), 4),
        "Recall": round(recall_score(y_test, y_full, zero_division=0), 4),
        "F1-Score": round(f1_score(y_test, y_full, zero_division=0), 4),
        "ROC-AUC": 0.5000,
        "TP": y_test.sum(), "FP": len(y_test) - y_test.sum(), "FN": 0, "TN": 0,
        "Re-index Cost %": "100.00%"
    })

    # Baseline 2: Changed-Only (Git Diff Feature is_modified)
    is_direct_col = df_X.columns.get_loc("is_modified") if "is_modified" in df_X.columns else 0
    y_direct = (df_X.iloc[split_idx:, is_direct_col] > 0).astype(int).values
    eval_results.append({
        "Model / Strategy": "Baseline: Changed-Only (Git Diff)",
        "Accuracy": round(accuracy_score(y_test, y_direct), 4),
        "Precision": round(precision_score(y_test, y_direct, zero_division=0), 4),
        "Recall": round(recall_score(y_test, y_direct, zero_division=0), 4),
        "F1-Score": round(f1_score(y_test, y_direct, zero_division=0), 4),
        "ROC-AUC": round(roc_auc_score(y_test, y_direct), 4),
        "TP": confusion_matrix(y_test, y_direct, labels=[0,1]).ravel()[3],
        "FP": confusion_matrix(y_test, y_direct, labels=[0,1]).ravel()[1],
        "FN": confusion_matrix(y_test, y_direct, labels=[0,1]).ravel()[2],
        "TN": confusion_matrix(y_test, y_direct, labels=[0,1]).ravel()[0],
        "Re-index Cost %": f"{(y_direct.sum() / len(y_test)) * 100:.2f}%"
    })

    df_res = pd.DataFrame(eval_results)
    print("\n" + "=" * 95)
    print("STAGE 4 SUPERVISED ML & BASELINE EVALUATION METRICS MATRIX:")
    print("=" * 95)
    print(df_res.to_string(index=False))

    out_dir = repo_root / "results" / "multi_model_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    df_res.to_csv(out_dir / "stage4_ml_pareto_evaluation.csv", index=False)
    print(f"\nSaved evaluation metrics to: {out_dir / 'stage4_ml_pareto_evaluation.csv'}")


if __name__ == "__main__":
    run_stage4_ml_evaluation()

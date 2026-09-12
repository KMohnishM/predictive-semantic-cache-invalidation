#!/usr/bin/env python3
"""
Phase 6 validation: train Pipeline A's predictor on each label source
(cosine_threshold vs leave_one_out), export each model's predictions, and
run both through the *unmodified* standalone benchmarking pipeline
(src/benchmarking/) so the two label sources can be compared on the same
ground everyone already trusts — a real Pareto frontier (update cost vs.
retrieval freshness), not a claim.

This deliberately does NOT touch src/benchmarking/ or predictor.py — it
only orchestrates two runs of each and diffs the results. See
docs/ground_truth_method_comparison.md and
Plans/ground_truth_fix_implementation_plan.md (Phase 6) for the rationale.

Usage:
    python scripts/compare_ground_truth_labels.py [--num-commits N] [--commit-stride N] [--quick]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_experiment import Experiment  # noqa: E402
from benchmarking.types import BenchmarkConfig  # noqa: E402
from benchmarking.runner import run_benchmark  # noqa: E402


LABEL_SOURCES = ["cosine_threshold", "leave_one_out"]


def train_and_export_predictions(label_source: str, num_commits: int, commit_stride: int,
                                  predictions_out_dir: Path) -> Path:
    """Run Pipeline A's full train_model()+evaluate_strategies() for one
    label source, and return the path to its exported predictions.json."""
    print(f"\n{'='*80}\nTraining Pipeline A predictor  (label_source={label_source})\n{'='*80}")

    experiment = Experiment(
        num_commits=num_commits,
        commit_stride=commit_stride,
        label_source=label_source,
    )

    if not experiment.setup():
        raise RuntimeError(f"[{label_source}] Experiment.setup() failed")
    if not experiment.harvest_commits():
        raise RuntimeError(f"[{label_source}] Experiment.harvest_commits() failed")
    if not experiment.build_dataset():
        raise RuntimeError(f"[{label_source}] Experiment.build_dataset() failed")
    if not experiment.train_model():
        raise RuntimeError(f"[{label_source}] Experiment.train_model() failed")

    # evaluate_strategies() is what populates and exports predictions.json
    experiment.evaluate_strategies()

    src_predictions = experiment.results_dir / "predictions.json"
    if not src_predictions.exists():
        raise RuntimeError(f"[{label_source}] predictions.json was not produced at {src_predictions}")

    predictions_out_dir.mkdir(parents=True, exist_ok=True)
    dest = predictions_out_dir / f"predictions_{label_source}.json"
    shutil.copyfile(src_predictions, dest)
    print(f"[{label_source}] predictions exported -> {dest}")
    return dest


def run_benchmark_for_predictions(label_source: str, predictions_path: Path,
                                   num_commits: int, commit_stride: int,
                                   output_dir: Path) -> Path:
    """Run the unmodified standalone benchmarking pipeline against one
    label source's predictions, with predictive_ml included so its Pareto
    position is directly comparable to the other baselines."""
    print(f"\n{'='*80}\nRunning benchmarking pipeline against {label_source} predictions\n{'='*80}")

    config = BenchmarkConfig(
        repo_url="https://github.com/psf/black.git",
        repo_path=str(PROJECT_ROOT / "workspace" / "black"),
        output_dir=str(output_dir / label_source),
        num_commits=num_commits,
        commit_stride=commit_stride,
        query_mode="hybrid",
        curated_queries_path=str(PROJECT_ROOT / "src" / "benchmarking" / "data" / "curated_queries.json"),
        strategies=["changed_only", "fixed_hop", "predictive_ml", "full_reindex"],
        predictions_path=str(predictions_path),
        ml_threshold=0.5,
    )
    run_dir = run_benchmark(config)
    print(f"[{label_source}] benchmark report -> {run_dir / 'summary_report.md'}")
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-commits", type=int, default=5)
    parser.add_argument("--commit-stride", type=int, default=20)
    parser.add_argument(
        "--quick", action="store_true",
        help="Use a small, fast configuration (3 commits, stride 5) for a smoke test "
             "rather than a statistically meaningful comparison."
    )
    args = parser.parse_args()

    num_commits = 3 if args.quick else args.num_commits
    commit_stride = 5 if args.quick else args.commit_stride

    predictions_dir = PROJECT_ROOT / "results" / "label_source_comparison" / "predictions"
    benchmark_output_dir = PROJECT_ROOT / "results" / "label_source_comparison" / "benchmark_runs"

    report_paths = {}
    for label_source in LABEL_SOURCES:
        predictions_path = train_and_export_predictions(
            label_source, num_commits, commit_stride, predictions_dir
        )
        run_dir = run_benchmark_for_predictions(
            label_source, predictions_path, num_commits, commit_stride, benchmark_output_dir
        )
        report_paths[label_source] = run_dir / "summary_report.md"

    print(f"\n{'='*80}\nDONE — compare these two reports directly:\n{'='*80}")
    for label_source, path in report_paths.items():
        print(f"  {label_source:18s} -> {path}")


if __name__ == "__main__":
    main()

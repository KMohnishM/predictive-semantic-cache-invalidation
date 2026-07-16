# Codebase Index

## Overview
This repository is a Python research prototype for predictive semantic cache invalidation under repository evolution. It replays Git history, builds repository dependency graphs, computes semantic drift between commits, trains a prediction model, and evaluates cache invalidation strategies.

## Entry Points
- [run_experiment.py](run_experiment.py) is the main orchestration script and CLI entry point.
- [requirements.txt](requirements.txt) lists the runtime dependencies.
- [task.md](task.md) tracks the current phase/task status.

## Core Pipeline Modules
- [src/git_helper.py](src/git_helper.py) handles Git checkout, history traversal, and diff/file lookup.
- [src/repo_parser.py](src/repo_parser.py) parses repository source into entities and builds the dependency/call graph.
- [src/embedding_manager.py](src/embedding_manager.py) generates embeddings and computes semantic drift.
- [src/feature_extractor.py](src/feature_extractor.py) assembles structural, propagation, and commit-level features.
- [src/predictor.py](src/predictor.py) trains and evaluates drift prediction models.
- [src/evaluator.py](src/evaluator.py) compares cache invalidation strategies and retrieval metrics.
- [src/visualize.py](src/visualize.py) produces plots and summary reports.

## Supporting Models
- [src/rsd.py](src/rsd.py) implements Repository State Descriptor logic for stratified splitting.
- [src/gtd.py](src/gtd.py) implements Graph Transition Descriptor logic for graph evolution features.
- [src/__init__.py](src/__init__.py) marks the package root.

## Runtime Flow
1. Clone the target repository into `workspace/black`.
2. Parse each commit into entities and a dependency graph.
3. Generate embeddings for entity source, optionally with call-graph context.
4. Compute semantic drift between adjacent commits.
5. Extract predictive features and train the model.
6. Evaluate baseline and predictive invalidation strategies.
7. Write plots, metrics, and reports into `results/`.

## Command-Line Options
The CLI in [run_experiment.py](run_experiment.py) supports these main flags:
- `--repo-url`: repository to analyze.
- `--workspace-dir`: clone destination.
- `--num-commits`: number of commits to replay.
- `--train-ratio`: training split ratio.
- `--threshold`: drift threshold for classification.
- `--clean-mode`: strip comments/docstrings before embedding.
- `--context-chunking`: enable call-graph aware contextual chunking.
- `--subset`: override commit count for quick runs.

## Output Locations
- `results/`: generated reports and plots.
- `results/results.json`: serialized experiment output.
- `results/summary_report.txt`: summary metrics report.
- `results_<mode>_commits<N>_clean<flag>/`: run-specific result folders.
- `experiment.log`: run log written at the repository root.

## Reference Docs
- [README.md](README.md) explains the research problem and the main experiment flow.
- [Plans/Problem_Statement_and_FLOW.md](Plans/Problem_Statement_and_FLOW.md) captures the broader workflow framing.
- [Plans/ProblemStatements/Commit_Tuple_Problem/Implementation_Notes.md](Plans/ProblemStatements/Commit_Tuple_Problem/Implementation_Notes.md) and the other `Plans/` documents contain phase-specific notes.

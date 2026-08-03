# Tasks - Commit-Pair Diagnostic Logging

- [x] Initialize logging directory
  - [x] Create `results/commit_logs/` inside `run_experiment.py` setup
- [x] Implement training diagnostic capture
  - [x] Intercept training commit pairs in `build_dataset()`
  - [x] Log 25-feature matrix, actual drifts, and call-graph structure
- [x] Implement evaluation diagnostic capture
  - [x] Intercept test commit pairs in `evaluate_strategies()`
  - [x] Log ML predictions, strategy re-embeddings, and search metrics
- [x] Write diagnostic logs to disk
  - [x] Implement JSON serialization helper
  - [x] Verify generated JSON files exist and are well-formed

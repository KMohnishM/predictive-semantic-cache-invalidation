# Tasks - AST Cosmetic Filter & BFS Decay Integration

- [x] Implement AST Cosmetic Filter
  - [x] Add `normalize_source` helper to `run_experiment.py`
  - [x] Apply AST filter to `modified_entities` in `compute_drifts_and_features`
- [x] Implement Weighted BFS Decay Invalidation Strategy
  - [x] Define `WeightedBFSDecayStrategy` class in `src/evaluator.py`
  - [x] Add BFS decay evaluation to `evaluate_all_strategies`
  - [x] Wire `weighted_bfs_decay` trace into diagnostic log files in `run_experiment.py`
- [ ] Verify implementation (to be run by user)
  - [ ] Check `summary_report.txt` contains `weighted_bfs_decay` strategy results
  - [ ] Verify AST filter filters out cosmetic commits successfully

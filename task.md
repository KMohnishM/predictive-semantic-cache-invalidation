# Tasks - Phase 2: Call-Graph Aware Contextual Chunking

- [x] Implement contextual source builder helper in `run_experiment.py`
  - [x] Extract signature (first line of `def` or `class`) of direct dependencies
  - [x] Format as a valid Python stub function block to survive docstring/comment stripping
  - [x] Append to original entity source code
- [x] Integrate contextual chunking into the main `build_dataset` pipeline
  - [x] Retrieve contextual text before batch embedding generation
- [x] Add command-line argument `--context-chunking` to enable/disable this feature
- [/ ] Run experiment and verify (to be executed by user):
  - [ ] Propagation of drift to caller nodes (distance 1 and 2) is non-zero
  - [ ] Baseline A recall degrades over time as call-graph context changes
  - [ ] Proposed Predictive Strategy maintains high recall by updating stale callers
- [x] Update walkthrough artifact with Phase 2 results

# Semantic Cache Invalidation for Repository-Scale Embedding Maintenance

## Research Problem Statement

## Overview

Modern Large Language Model (LLM) coding assistants use **vector
databases** to store embeddings of software repositories. These
embeddings represent functions, classes, files, and other code
components so they can be searched semantically instead of by exact
keywords.

When a developer asks a question such as:

> "Where is user authentication implemented?"

the system searches the vector database to retrieve the most relevant
code before generating an answer.

This works well while the repository remains unchanged. However,
software repositories continuously evolve as developers add features,
fix bugs, refactor code, and modify dependencies.

This creates an important problem that current repository retrieval
systems do not explicitly solve.

------------------------------------------------------------------------

## The Core Problem

Most repository retrieval systems update their vector database using one
of two approaches.

### Strategy 1 -- Update Only Changed Code

Only the files or functions that were directly modified receive new
embeddings.

This approach is fast and inexpensive.

However, repositories are highly interconnected.

For example:

``` text
authenticate()
      ↑
login()
      ↑
api.py
```

If `authenticate()` changes significantly, the meaning of `login()` may
also change even though its source code remains exactly the same.

Since `login()` was not re-embedded, its stored embedding becomes
outdated.

Over time, these outdated embeddings reduce retrieval quality.

------------------------------------------------------------------------

### Strategy 2 -- Re-Embed the Entire Repository

Another solution is to regenerate embeddings for every repository entity
after each update.

This keeps all embeddings consistent.

However, for large repositories this process is expensive, slow, and
impractical for real-time software development.

------------------------------------------------------------------------

## Research Gap

Current research mainly focuses on:

-   Building better retrieval systems
-   Improving GraphRAG and repository knowledge graphs
-   Improving code search
-   Performing software change impact analysis

These approaches identify changed or affected code, but they do not
answer the following question:

> Which stored embeddings have become semantically outdated and should
> be regenerated?

This research focuses on stale embeddings rather than simply changed
code.

------------------------------------------------------------------------

## Research Problem

This research introduces **Semantic Cache Invalidation** for repository
embedding systems.

Instead of asking:

-   Which files changed?
-   Which functions were modified?
-   Which code depends on the changed code?

we ask:

> Which stored embeddings have become outdated enough to reduce
> retrieval quality?

The objective is to regenerate only those embeddings that are actually
needed.

------------------------------------------------------------------------

## Main Research Question

> What is the smallest set of repository entities that must be
> re-embedded after a code change to maintain retrieval quality close to
> that of a complete repository re-index?

This converts repository maintenance into an optimization problem.

------------------------------------------------------------------------

## Motivation

Modern repositories contain thousands of files and hundreds of thousands
of code entities.

Future LLM-based software engineering assistants will continuously rely
on repository embeddings.

If these embeddings become outdated:

-   Retrieval quality decreases.
-   Generated code may become incorrect.
-   Context supplied to LLMs becomes inaccurate.
-   Autonomous software engineering agents make poorer decisions.

Efficient embedding maintenance is therefore essential.

------------------------------------------------------------------------

## Proposed Solution

Rather than rebuilding the entire vector database after every repository
update, the proposed system estimates which repository entities have
become semantically stale.

Only those predicted entities are re-embedded.

Workflow:

``` text
Repository Update
      │
      ▼
Repository Graph
      │
      ▼
Semantic Impact Analysis
      │
      ▼
Predict Stale Embeddings
      │
      ▼
Selective Re-Embedding
      │
      ▼
Updated Vector Database
```

------------------------------------------------------------------------

## Research Objectives

1.  Study how repository changes affect stored embeddings.
2.  Define semantic embedding staleness.
3.  Predict which repository entities require re-embedding.
4.  Minimize update cost while preserving retrieval quality.
5.  Compare against existing update strategies.

------------------------------------------------------------------------

## Research Hypothesis

The dependency structure of a software repository contains enough
information to estimate which embeddings become semantically stale after
repository evolution.

------------------------------------------------------------------------

## Implementation Plan

### Stage 1 -- Repository Analysis

Extract:

-   Functions
-   Classes
-   Files
-   Imports
-   Function calls
-   Inheritance relationships

Construct a repository graph.

### Stage 2 -- Initial Embeddings

Generate embeddings for repository entities and store them in a vector
database.

### Stage 3 -- Repository Evolution

Replay repository commits to simulate software evolution.

### Stage 4 -- Semantic Impact Estimation

Estimate which entities have become semantically stale after each
update.

### Stage 5 -- Selective Re-Embedding

Regenerate embeddings only for predicted stale entities.

### Stage 6 -- Evaluation

Compare with:

-   Baseline 1: Re-embed changed entities only
-   Baseline 2: Full repository re-index

------------------------------------------------------------------------

## Evaluation Metrics

### Retrieval Performance

-   Recall@K
-   Mean Reciprocal Rank (MRR)
-   nDCG

### Computational Cost

-   Number of regenerated embeddings
-   Update latency
-   Embedding time
-   Total update cost

------------------------------------------------------------------------

## Expected Contributions

-   A formal definition of Semantic Cache Invalidation.
-   A framework for selective repository re-embedding.
-   A cost-versus-retrieval optimization formulation.
-   A benchmark for repository embedding maintenance.
-   Experimental evaluation against existing approaches.

------------------------------------------------------------------------

## Summary

This research investigates how to intelligently maintain repository
embeddings as software evolves.

Instead of rebuilding the entire repository index or updating only
directly modified files, the proposed approach predicts which embeddings
have become semantically outdated and selectively regenerates only those
embeddings.

The goal is to maintain high retrieval quality while significantly
reducing the computational cost of repository maintenance.






=======================================================================================================




# Project Flow

This document explains how the experiment moves through the codebase, from the command-line entrypoint to the final outputs.

## 1. Entry Point

The workflow starts in `run_experiment.py`.

1. Parse command-line arguments such as repository URL, number of commits, training split, drift threshold, clean mode, and context chunking.
2. Create an `Experiment` object.
3. Call `Experiment.run()` to execute the full pipeline.

## 2. Setup Phase

`Experiment.setup()` prepares the environment and core services:

1. Clone the target repository into `workspace/black` using `GitHelper`.
2. Initialize the repository parser, embedding manager, feature extractor, predictor, evaluator, and visualizer.
3. Create a results directory for the current run configuration.

## 3. Commit Harvesting

`Experiment.harvest_commits()` collects the history to replay:

1. Read the last N commits from the repository.
2. Reverse them into chronological order.
3. Split the commits into training and test subsets.

This keeps the experiment temporal instead of random, which matches how repository evolution actually happens.

## 4. Dataset Building

`Experiment.build_dataset()` replays each commit one by one and builds the learning dataset.

### 4.1 Checkout and Parse

For each commit:

1. Checkout the commit with Git.
2. Parse the repository with `RepoParser`.
3. Extract Python entities such as classes, functions, and methods.
4. Build a directed call graph from AST call relationships.

### 4.2 Embed Entities

Each extracted entity is embedded using `EmbeddingManager`:

1. Optionally remove comments and docstrings when `--clean-mode` is enabled.
2. Optionally append call-graph-aware context when `--context-chunking` is enabled.
3. Generate normalized sentence-transformer embeddings.

### 4.3 Measure Drift and Extract Features

When two adjacent commits are available, `compute_drifts_and_features()` compares them:

1. Compute semantic drift with cosine distance between old and new embeddings.
2. Detect modified files from Git diff output.
3. Map modified files back to affected entities.
4. Extract structural, propagation, commit, and historical features.

## 5. Feature Meaning

The feature extractor combines four groups of signals:

1. Structural features: graph degrees and centralities such as PageRank, closeness, and betweenness.
2. Evolution features: distance to modified nodes and counts of modified dependencies/dependents.
3. Commit features: lines added/deleted, entity size, and entity modification size.
4. Historical features: how often an entity changed before and its previous drift value.

These features are meant to explain why some entities become semantically stale after a commit.

## 6. Model Training

`Experiment.train_model()` builds the predictor:

1. Combine feature rows and drift targets from the training commit window.
2. Align features with drift labels by entity ID.
3. Split the data temporally.
4. Train the default drift model, which is a random forest regressor unless configured otherwise.
5. Evaluate the model on the held-out set.
6. Save the trained model to the results directory.

The predictor is used to estimate which entities are likely to exceed the drift threshold in future commits.

## 7. Strategy Evaluation

`Experiment.evaluate_strategies()` simulates cache maintenance policies on the test commits:

1. Predict drift scores for all entities in a commit pair.
2. Threshold those predictions into stale vs. not stale.
3. Run multiple invalidation strategies:
   - Changed-only baseline: update only directly modified entities.
   - Full reindex baseline: update every entity.
   - Fixed-hop baseline: update modified entities and nearby dependents within K hops.
   - Predictive strategy: update entities whose predicted drift is above threshold.
4. Compare the retrieval quality of each strategy against the ground truth embeddings.

The evaluator measures Recall@K, rank correlation, update percentage, and runtime.

## 8. Visualization And Reporting

`Experiment.generate_visualizations()` turns results into outputs:

1. Drift decay plot: shows how drift changes with graph distance from modified nodes.
2. Feature importance plot: shows which features matter most to the predictor.
3. Strategy comparison plot: compares recall and rank correlation across baselines.
4. Pareto frontier plot: shows the trade-off between retrieval quality and maintenance cost.
5. Drift distribution plot: summarizes the distribution of observed drift values.
6. Confusion matrix: compares predicted stale entities against the thresholded ground truth.
7. Summary report: writes a text summary of model and strategy performance.

## 9. Final Outputs

The run writes artifacts into the results folder:

1. `results.json` for serialized metrics.
2. `summary_report.txt` for a human-readable report.
3. Plots such as `drift_decay.png`, `feature_importance.png`, `pareto_frontier.png`, and `strategy_comparison.png`.
4. `drift_predictor.pkl` for the trained model.

## 10. Block Diagram

```mermaid
flowchart TD
    A[CLI: run_experiment.py] --> B[Experiment.setup()]
    B --> C[Clone repo with GitHelper]
    B --> D[Init RepoParser]
    B --> E[Init EmbeddingManager]
    B --> F[Init FeatureExtractor]
    B --> G[Init DriftPredictor]
    B --> H[Init Evaluator]
    B --> I[Init Visualizer]

    A --> J[Experiment.harvest_commits()]
    J --> K[Get commit history]
    K --> L[Split into train and test commits]

    L --> M[Experiment.build_dataset()]
    M --> N[Checkout commit]
    N --> O[Parse repo AST]
    O --> P[Build dependency graph]
    P --> Q[Generate entity embeddings]
    Q --> R[Compute drift between adjacent commits]
    R --> S[Extract graph, diff, and history features]
    S --> T[Store datasets by commit pair]

    T --> U[Experiment.train_model()]
    U --> V[Align features with drift labels]
    V --> W[Train ML model]
    W --> X[Evaluate holdout set]
    X --> Y[Save model]

    Y --> Z[Experiment.evaluate_strategies()]
    Z --> AA[Predict drift on test pairs]
    AA --> AB[Run cache invalidation baselines]
    AB --> AC[Measure Recall@K and rank correlation]
    AC --> AD[Compare cost vs quality]

    AD --> AE[Experiment.generate_visualizations()]
    AE --> AF[Create plots and summary report]
    AF --> AG[Save results.json and artifacts]
```

## 11. Mental Model

The easiest way to think about the project is:

1. Replay Git history.
2. Turn each snapshot into a graph of code entities.
3. Embed each entity to capture semantics.
4. Measure how those semantics change over time.
5. Learn which graph and change signals predict drift.
6. Simulate different invalidation policies and compare their trade-offs.

That is the full loop the experiment is testing: can the system update only the entities that are likely to become stale, while staying close to full reindexing quality?
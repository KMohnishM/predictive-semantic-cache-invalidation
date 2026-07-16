# Research Sub-Problem 1: Repository State Characterization for Representative Commit Sampling

## Background

The primary research problem of this project is to develop a predictive
semantic cache invalidation framework that selectively regenerates stale
repository embeddings while maintaining retrieval quality and minimizing
computational cost.

The proposed drift prediction model is trained on repository evolution
data obtained by replaying Git commits. As with any supervised machine
learning system, the quality and representativeness of the training and
testing datasets have a direct impact on the reliability and
generalizability of the learned model.

Current implementations typically split commits either chronologically
or randomly. While chronological ordering preserves temporal evolution,
it does not ensure that both the training and testing datasets
adequately represent the diversity of repository states encountered
during software evolution. Likewise, random sampling provides no
guarantee that important repository characteristics are proportionally
represented.

A more statistically robust approach would be stratified sampling.
However, stratified sampling requires each sample to possess measurable
attributes that define the strata. A Git commit, by itself, is simply a
repository snapshot identified by a commit hash and does not have a
standardized numerical representation describing the state of the
repository.

Consequently, conventional stratified sampling cannot be directly
applied to repository evolution datasets.

------------------------------------------------------------------------

## Research Sub-Problem

**How can a repository snapshot (represented by a Git commit) be
transformed into a standardized numerical descriptor that enables
statistically representative train-test partitioning for machine
learning models used in semantic cache invalidation?**

This sub-problem does **not** alter the primary research objective.
Instead, it provides a methodology for constructing higher-quality
datasets that improve the training and evaluation of the semantic drift
prediction model.

------------------------------------------------------------------------

## Motivation

The drift prediction model learns from historical repository evolution.
If the training commits are not representative of the repository's
structural and semantic diversity, the model may become biased toward
certain repository states and fail to generalize.

A standardized repository descriptor enables:

-   Representative train-test partitioning
-   Stratified sampling of repository states
-   Better benchmark construction
-   More reliable model evaluation
-   Improved reproducibility across repositories

------------------------------------------------------------------------

## Proposed Solution Overview

Rather than describing a commit using only Git metadata (such as commit
hash, author, or timestamp), each commit is represented by a
**Repository State Descriptor (RSD)**.

The Repository State Descriptor is a multidimensional numerical tuple
that summarizes the repository state captured by a particular commit.

Instead of:

``` text
Commit
↓
SHA
```

we construct:

``` text
Commit
↓
Repository State Descriptor
↓
Numerical Feature Tuple
```

This descriptor becomes the basis for statistical analysis and dataset
partitioning. The primary research problem focuses on predicting which
repository entities should be selectively re-embedded after software
evolution. The prediction model relies on machine learning, making the
quality of the training and testing datasets critical to the validity
of the results.

A challenge arises because repository snapshots (Git commits) do not
possess a standardized numerical representation. Consequently, commits
cannot be directly grouped into representative strata for train-test
partitioning, and conventional stratified sampling cannot be applied.

The objective of this sub-problem is therefore to construct a
**Repository State Descriptor (RSD)** that converts every repository
snapshot into a fixed-length numerical tuple describing the state of the
repository at that commit.

------------------------------------------------------------------------

# Repository State Descriptor

For every commit (C_i), define a repository descriptor

\[ R(C_i) = (S,;T,;M,;C,;E) \]

where:

-   **S** = Repository Scale Score
-   **T** = Dependency Topology Score
-   **M** = Semantic Organization Score
-   **C** = Code Complexity Score
-   **E** = Repository Evolution Score

Each score is normalized to the interval:

\[ 0 `\leq `{=tex}score `\leq 1`{=tex} \]

allowing commits from repositories of different sizes to be compared
quantitatively.

------------------------------------------------------------------------

# Step 1 --- Compute Raw Metrics

Each category is computed from multiple repository metrics.

## Repository Scale

-   Number of files
-   Number of classes
-   Number of functions
-   Total lines of code
-   Average function length
-   Average class size

------------------------------------------------------------------------

## Dependency Graph Characteristics

-   Number of graph nodes
-   Number of graph edges
-   Average node degree
-   Graph density
-   Number of connected components
-   Average clustering coefficient
-   Average shortest path length
-   Average PageRank score

------------------------------------------------------------------------

## Semantic Characteristics

-   Average embedding similarity
-   Embedding variance
-   Embedding entropy
-   Number of semantic clusters
-   Average intra-cluster similarity
-   Average inter-cluster distance

------------------------------------------------------------------------

## Code Complexity Characteristics

-   Average cyclomatic complexity
-   Average fan-in
-   Average fan-out
-   Maximum inheritance depth
-   Import diversity

------------------------------------------------------------------------

## Evolution Characteristics

-   Historical code churn
-   Historical modification frequency
-   Average historical semantic drift
-   Repository age
-   Commit frequency

------------------------------------------------------------------------

# Step 2 --- Normalize Metrics

Because repositories vary significantly in size and complexity, raw
values should not be used directly.

Each metric is normalized using a robust normalization strategy.

Possible approaches include:

-   Min-Max Normalization
-   Z-Score Standardization
-   **Robust Scaling (Recommended)**

Robust Scaling:

\[ x' = `\frac{x - \text{Median}}{IQR}`{=tex} \]

where IQR denotes the Interquartile Range.

Robust scaling is preferred because software repository metrics often
contain significant outliers.

------------------------------------------------------------------------

# Step 3 --- Compute Category Scores

Each category score is computed as a weighted combination of its
normalized metrics.

For Repository Scale:

\[ S = `\sum`{=tex}\_{i=1}\^{n} w_i x_i' \]

subject to

\[ `\sum`{=tex}\_i w_i = 1 \]

where

-   (x_i') is the normalized metric
-   (w_i) is its corresponding weight.

------------------------------------------------------------------------

# Determining Feature Weights

Several weighting approaches are possible.

## Option 1 --- Equal Weights

Assign equal importance to every metric.

Simple and highly interpretable.

------------------------------------------------------------------------

## Option 2 --- Principal Component Analysis (PCA)

Apply PCA independently within each feature category.

The first principal component becomes the category score.

Advantages:

-   Automatically captures the dominant variation.
-   Eliminates manual weighting.

------------------------------------------------------------------------

## Option 3 --- Entropy Weight Method (Recommended)

Assign higher weights to metrics containing greater information.

Entropy weight:

\[ w_i = `\frac{1-H_i}`{=tex} {`\sum`{=tex}\_j(1-H_j)} \]

where

-   (H_i) is the entropy of metric (i).

The category score becomes

\[ Score = `\sum`{=tex}\_i w_i x_i' \]

Advantages:

-   Objective weighting
-   No manual parameter tuning
-   Emphasizes informative metrics
-   Suitable for heterogeneous repository statistics

------------------------------------------------------------------------

# Final Repository State Descriptor

After computing all category scores, each commit is represented by

\[ R(C_i) = (S,;T,;M,;C,;E) \]

Example:

``` text
Commit 153

↓

(0.76, 0.69, 0.81, 0.58, 0.43)
```

This fixed-length descriptor acts as a numerical fingerprint of the
repository state.

------------------------------------------------------------------------

# Dataset Construction Pipeline

``` text
Git Repository
        ↓
Replay Commit History
        ↓
Extract Repository Metrics
        ↓
Normalize Metrics
        ↓
Compute Category Scores
        ↓
Repository State Descriptor
        ↓
Cluster Similar Repository States
        ↓
Assign Strata
        ↓
Perform Stratified Train-Test Split
        ↓
Train Semantic Drift Prediction Model
```

Since the descriptor is multidimensional, clustering algorithms such as
K-Means or Gaussian Mixture Models can be used to group similar
repository states before applying stratified sampling.

------------------------------------------------------------------------

# Expected Benefits

The proposed Repository State Descriptor is intended to:

-   Enable statistically representative train-test partitions.
-   Reduce sampling bias during model training.
-   Improve the robustness and generalization of the semantic drift
    prediction model.
-   Produce fairer comparisons between cache invalidation strategies.
-   Provide a reusable methodology for repository-based machine learning
    experiments.

------------------------------------------------------------------------

# Relationship to the Main Research Problem

This work is a supporting methodological contribution that improves the
quality of the experimental pipeline without changing the primary
research objective.

``` text
Repository Evolution
        ↓
Repository State Descriptor
        ↓
Representative Dataset Construction
        ↓
Semantic Drift Prediction
        ↓
Selective Re-Embedding
        ↓
High Retrieval Quality with Low Update Cost
```

By ensuring that the training and testing datasets are representative of
the repository's structural, semantic, and evolutionary diversity, the
resulting drift prediction model is expected to generalize more reliably
across different repository states.

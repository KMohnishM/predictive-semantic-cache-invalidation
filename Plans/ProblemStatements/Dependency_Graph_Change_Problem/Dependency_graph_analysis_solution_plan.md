# Dependency Graph Analysis Solution Plan

# Problem Statement 2

## Background

The primary objective of the overall research is to selectively
regenerate repository embeddings after software evolution by predicting
which entities become semantically stale.

A central assumption behind this objective is that semantic changes do
not occur only within directly modified source files. A seemingly local
code change may alter dependency relationships, control flow, data flow,
API usage, or architectural interactions, causing semantic changes to
propagate through the repository.

Current approaches generally identify changed files using Git diffs or
simple dependency traversals. However, they rarely quantify **how the
dependency graph itself evolves** or how those structural changes relate
to semantic change.

Consequently, a major supporting problem arises:

> How can we accurately characterize the change in the repository
> dependency graph between two consecutive commits so that structural
> evolution reflects the underlying semantic evolution of the codebase?

------------------------------------------------------------------------

# Research Sub-Problem

For two consecutive repository snapshots,

G_t and G\_(t+1),

determine the structural and semantic changes of the dependency graph
and produce a quantitative graph transition representation that
accurately captures repository evolution.

The output of this stage should become the primary source of features
for downstream semantic drift prediction.

------------------------------------------------------------------------

# Motivation

Software repositories evolve continuously.

Between two commits, changes may include

-   function additions
-   deletions
-   refactoring
-   dependency rewiring
-   API migration
-   architectural restructuring
-   inheritance changes
-   import modifications

Although many of these changes affect only a few files syntactically,
their impact may propagate across large portions of the dependency
graph.

Simply identifying modified files cannot capture this propagation.

Instead, repository evolution should be modeled as a graph
transformation problem.

------------------------------------------------------------------------

# Proposed Solution

Represent every repository snapshot as a directed attributed dependency
graph.

For commit C_t

G_t = (V_t, E_t)

For commit C\_(t+1)

G\_(t+1) = (V\_(t+1), E\_(t+1))

where

-   V represents repository entities
-   E represents dependency relationships
-   every node stores semantic and structural attributes

Rather than comparing source files directly, compare successive graphs.

The objective is to construct a **Graph Transition Descriptor (GTD)**
that summarizes how the repository graph changes between two commits.

------------------------------------------------------------------------

# Step 1 --- Build Repository Dependency Graphs

For every commit:

Extract

-   Files
-   Classes
-   Functions
-   Methods

Construct dependency edges including

-   Function calls
-   Imports
-   Class inheritance
-   Interface implementation
-   Module dependencies
-   Composition relationships

Each node additionally stores

-   embedding
-   LOC
-   complexity
-   historical statistics

------------------------------------------------------------------------

# Step 2 --- Node-Level Structural Changes

For every entity determine

-   Node Added
-   Node Deleted
-   Node Modified
-   Node Renamed
-   Node Unchanged

Compute structural deltas including

-   Degree change
-   Fan-in change
-   Fan-out change
-   PageRank change
-   Betweenness change
-   Closeness change

These describe how the importance of an entity changes.

------------------------------------------------------------------------

# Step 3 --- Edge-Level Dependency Changes

Compare

E_t

and

E\_(t+1)

Determine

-   Added dependencies
-   Removed dependencies
-   Redirected dependencies
-   Changed import relationships
-   Changed inheritance relationships
-   Changed call relationships

Compute metrics such as

-   Edge edit distance
-   Dependency churn
-   Density variation
-   Connectivity variation

------------------------------------------------------------------------

# Step 4 --- Graph-Level Evolution Metrics

Measure global structural evolution.

Suggested metrics include

-   Node growth ratio
-   Edge growth ratio
-   Graph density change
-   Diameter change
-   Average shortest path change
-   Clustering coefficient change
-   Community structure variation
-   Centrality distribution shift

These summarize how the repository architecture evolves.

------------------------------------------------------------------------

# Step 5 --- Semantic Graph Analysis

Structure alone is insufficient.

Each node also possesses an embedding.

For every matched node

compute

Cosine Drift

between

Embedding_t

and

Embedding\_(t+1)

Aggregate these into graph-level semantic measures.

Example metrics

-   Mean semantic drift
-   Drift variance
-   Drift entropy
-   High-drift node ratio
-   Drift by graph distance
-   Community semantic shift

This links graph evolution with semantic evolution.

------------------------------------------------------------------------

# Step 6 --- Graph Transition Descriptor (GTD)

Combine all graph evolution statistics into a fixed-length numerical
descriptor.

For transition

G_t → G\_(t+1)

define

GTD = ( Node Evolution, Edge Evolution, Structural Evolution, Centrality
Evolution, Semantic Evolution )

Each component is computed from normalized graph metrics using the same
methodology adopted for the Repository State Descriptor:

1.  Extract raw metrics.
2.  Normalize using Robust Scaling.
3.  Compute composite scores using the Entropy Weight Method.
4.  Produce normalized scores between 0 and 1.

The resulting descriptor acts as a compact numerical fingerprint of
graph evolution between consecutive commits.

------------------------------------------------------------------------

# Step 7 --- Dependency Impact Propagation

Rather than assuming all neighbors are equally affected,

estimate propagation through the graph.

Possible propagation signals include

-   shortest-path distance
-   weighted edge traversal
-   personalized PageRank diffusion
-   graph attention propagation
-   random walk influence

The output is an impact score for every node indicating how strongly it
is affected by upstream changes.

------------------------------------------------------------------------

# Step 8 --- Integration with Drift Prediction

The Graph Transition Descriptor and propagation scores become feature
inputs for the semantic drift prediction model.

Pipeline

Repository Snapshot_t ↓ Dependency Graph_t

Repository Snapshot\_(t+1) ↓ Dependency Graph\_(t+1)

        ↓

Graph Difference Analysis ↓ Graph Transition Descriptor ↓ Impact
Propagation ↓ Semantic Drift Predictor ↓ Selective Cache Invalidation

------------------------------------------------------------------------

# Expected Benefits

The proposed methodology is expected to

-   Capture repository evolution more accurately than Git diffs alone.
-   Represent both structural and semantic graph evolution.
-   Quantify dependency propagation instead of relying on heuristic hop
    distances.
-   Produce richer features for semantic drift prediction.
-   Improve selective re-embedding decisions.

------------------------------------------------------------------------

# Relationship to the Main Research Problem

This is a supporting methodological contribution.

Main Research Problem

Repository Evolution ↓ Graph Evolution Analysis ↓ Semantic Drift
Prediction ↓ Predict Stale Embeddings ↓ Selective Re-Embedding

Problem Statement 3 addresses the second stage of this pipeline by
transforming raw repository changes into a structured graph evolution
representation that can be learned by the semantic drift prediction
model.

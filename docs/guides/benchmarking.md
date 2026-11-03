# Benchmarking & Evaluation

The library includes a full benchmarking suite to compare invalidation strategies on any Git repository.

---

## 1. Supported Invalidation Strategies

- **`changed_only`**: Directly modified entities (0 hops).
- **`fixed_hop`**: Propagates invalidation up to $k$ hops in the call graph (e.g. $k=1$ or $k=2$).
- **`predictive_ml`**: Machine learning classifier predicting semantic drift based on AST, graph metrics, and diff descriptors.
- **`full_reindex`**: Theoretical upper bound (re-indexes 100% of the codebase).

---

## 2. Running Benchmarks via CLI

The package exposes the `predictive-cache-benchmark` console entrypoint:

```bash
predictive-cache-benchmark \
  --repo-path ./django \
  --num-commits 10 \
  --commit-stride 1 \
  --strategies changed_only,fixed_hop,predictive_ml \
  --output-dir ./benchmark_output
```

### Key CLI Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--repo-path` | `.` | Target Git repository root |
| `--num-commits` | `5` | Number of commits to evaluate |
| `--commit-stride` | `1` | Stride between consecutive sampled commits |
| `--strategies` | `changed_only,fixed_hop,predictive_ml` | Comma-separated list of strategies |
| `--hop-k` | `1` | Maximum hops for fixed_hop strategy |
| `--output-dir` | `benchmark_runs` | Directory where metrics and charts are written |

---

## 3. Benchmark Reports & Visualizations

The benchmark generates:
- `summary_report.md`: Markdown report detailing recall, re-embed ratio, and staleness costs.
- `strategy_comparison.png`: Bar chart comparing re-embed costs across strategies.
- `pareto_frontier.png`: Tradeoff frontier between Recall (cache freshness) and Re-embed Percentage (compute cost).

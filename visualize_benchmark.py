"""
Standalone CLI Benchmark Results Visualizer.

Loads benchmark results (summary_metrics.json, embedding_comparisons.json, etc.)
from any benchmark run folder (or automatically detects the most recent run)
and generates high-resolution graphical visualizations.

Usage:
    python visualize_benchmark.py
    python visualize_benchmark.py --run-dir benchmark_runs/benchmark_v1.0_seed13_21dca43c_5bfefcb1
    python visualize_benchmark.py --show    # Pops up interactive GUI plot windows
    python visualize_benchmark.py --output-dir my_charts/
"""

import argparse
import json
import logging
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("visualize_benchmark")


def find_latest_benchmark_run(benchmark_dir: Path = Path("benchmark_runs")) -> Path:
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"Directory {benchmark_dir} does not exist.")
    runs = [
        d for d in benchmark_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "summary_metrics.json").exists()
    ]
    if not runs:
        raise FileNotFoundError(f"No benchmark run containing summary_metrics.json found in {benchmark_dir}.")
    runs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return runs[0]


def main():
    parser = argparse.ArgumentParser(description="Visualize Predictive Cache Invalidation Benchmark Results")
    parser.add_argument(
        "--run-dir",
        type=str,
        default=None,
        help="Path to benchmark run directory (e.g. benchmark_runs/benchmark_v1.0_seed13_...). Defaults to latest.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save generated PNG charts. Defaults to inside the run directory.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display interactive matplotlib figure windows on screen.",
    )
    args = parser.parse_args()

    if args.run_dir:
        run_path = Path(args.run_dir).resolve()
    else:
        run_path = find_latest_benchmark_run()

    logger.info(f"Loading benchmark metrics from: {run_path}")
    metrics_file = run_path / "summary_metrics.json"
    if not metrics_file.exists():
        raise FileNotFoundError(f"Missing {metrics_file}")

    data = json.loads(metrics_file.read_text(encoding="utf-8"))
    strategy_summaries = data.get("strategy_summaries", {})
    if not strategy_summaries:
        logger.error("No strategy_summaries found in summary_metrics.json.")
        return

    # Check for saturation warning
    if data.get("saturation_warning"):
        logger.warning("NOTE: Benchmark saturation was detected for this run.")

    # Reconstruct embedding comparisons if available
    raw_emb = data.get("embedding_comparison_summaries") or []
    from src.benchmarking.types import StrategyEmbeddingComparisonResult
    emb_comps = [
        StrategyEmbeddingComparisonResult(
            strategy_name=e.get("strategy_name", ""),
            total_entities=e.get("total_entities", 0),
            mean_cosine_similarity=e.get("mean_cosine_similarity", 1.0),
            min_cosine_similarity=e.get("min_cosine_similarity", 1.0),
            p95_cosine_similarity=e.get("p95_cosine_similarity", 1.0),
            updated_fraction=e.get("updated_fraction", 0.0),
            decision_latency_seconds=e.get("decision_latency_seconds", 0.0),
            total_e2e_time_seconds=e.get("total_e2e_time_seconds", 0.0),
            per_entity_comparisons=[],
        )
        for e in raw_emb
    ]

    from src.benchmarking.reporting import compute_pareto_frontier
    real_ss = {k: v for k, v in strategy_summaries.items() if not k.startswith("__")}
    pareto_strategies = compute_pareto_frontier(real_ss)

    out_dir = Path(args.output_dir).resolve() if args.output_dir else run_path

    # Generate image charts
    from src.benchmarking.visualizer import generate_benchmark_charts
    chart_paths = generate_benchmark_charts(
        output_dir=str(out_dir),
        strategy_summaries=strategy_summaries,
        embedding_comparisons=emb_comps if emb_comps else None,
        pareto_strategies=pareto_strategies,
    )

    print("\n" + "=" * 65)
    print(f"BENCHMARK GRAPHICAL VISUALIZATION COMPLETED")
    print("=" * 65)
    print(f"Run ID:         {data.get('run_id')}")
    print(f"Total queries:  {data.get('total_queries'):,}")
    print(f"Output folder:  {out_dir}")
    print(f"Charts saved:")
    for p in chart_paths:
        print(f"  • {p.name} ({p.stat().st_size:,} bytes)")
    print("=" * 65 + "\n")

    if args.show:
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg

        fig, axes = plt.subplots(2, 2, figsize=(15, 11))
        fig.suptitle(f"Benchmark Results: {data.get('run_id')}", fontsize=14, fontweight="bold")

        display_charts = [
            (axes[0, 0], out_dir / "strategy_comparison.png", "Strategy Comparison"),
            (axes[0, 1], out_dir / "pareto_frontier.png", "Pareto Frontier"),
            (axes[1, 0], out_dir / "metrics_heatmap.png", "Metrics Heatmap"),
            (axes[1, 1], out_dir / "radar_chart.png", "Strategy Radar"),
        ]

        for ax, img_path, title in display_charts:
            if img_path.exists():
                img = mpimg.imread(str(img_path))
                ax.imshow(img)
                ax.axis("off")
                ax.set_title(title, fontsize=11, fontweight="bold")
            else:
                ax.axis("off")

        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()

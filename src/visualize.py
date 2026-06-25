"""Visualization module for generating plots."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Visualizer:
    """Generates visualization plots for experiment results."""

    def __init__(self, output_dir: str = "results"):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10

    def plot_drift_decay(self, drift_by_distance: Dict[int, List[float]],
                         output_file: str = "drift_decay.png") -> str:
        """
        Plot average drift against distance from modified node.

        Args:
            drift_by_distance: Dictionary mapping distance to list of drift values
            output_file: Output filename

        Returns:
            Path to saved plot
        """
        logger.info("Generating drift decay plot...")

        # Compute statistics
        distances = sorted(drift_by_distance.keys())
        mean_drifts = [np.mean(drift_by_distance[d]) for d in distances]
        std_drifts = [np.std(drift_by_distance[d]) for d in distances]

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(distances, mean_drifts, marker='o', linewidth=2, markersize=8,
                color='#2E86AB', label='Mean Drift')
        ax.fill_between(distances,
                        [m - s for m, s in zip(mean_drifts, std_drifts)],
                        [m + s for m, s in zip(mean_drifts, std_drifts)],
                        alpha=0.3, color='#2E86AB', label='±1 Std Dev')

        ax.set_xlabel('Distance from Modified Node (hops)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Semantic Drift', fontsize=12, fontweight='bold')
        ax.set_title('Semantic Drift Propagation with Distance', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        # Add threshold line
        ax.axhline(y=0.02, color='red', linestyle='--', linewidth=1.5, label='Threshold (0.02)', alpha=0.7)

        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Drift decay plot saved to {output_path}")
        return str(output_path)

    def plot_feature_importance(self, feature_importance: Dict[str, float],
                                top_n: int = 20,
                                output_file: str = "feature_importance.png") -> str:
        """
        Plot feature importance bar chart.

        Args:
            feature_importance: Dictionary mapping feature names to importance scores
            top_n: Number of top features to display
            output_file: Output filename

        Returns:
            Path to saved plot
        """
        logger.info("Generating feature importance plot...")

        # Sort and get top N
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        top_features = sorted_features[:top_n]

        feature_names = [f[0] for f in top_features]
        importance_scores = [f[1] for f in top_features]

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))

        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(feature_names)))
        bars = ax.barh(range(len(feature_names)), importance_scores, color=colors)

        ax.set_yticks(range(len(feature_names)))
        ax.set_yticklabels(feature_names)
        ax.invert_yaxis()
        ax.set_xlabel('Feature Importance', fontsize=12, fontweight='bold')
        ax.set_title(f'Top {top_n} Feature Importances for Drift Prediction',
                     fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, (bar, score) in enumerate(zip(bars, importance_scores)):
            ax.text(score, i, f' {score:.4f}', va='center', fontsize=9)

        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Feature importance plot saved to {output_path}")
        return str(output_path)

    def plot_pareto_frontier(self, pareto_df: pd.DataFrame,
                             all_strategies_df: Optional[pd.DataFrame] = None,
                             output_file: str = "pareto_frontier.png") -> str:
        """
        Plot Pareto frontier showing trade-off between recall and maintenance cost.

        Args:
            pareto_df: DataFrame with Pareto-optimal strategies
            all_strategies_df: DataFrame with all strategies (optional)
            output_file: Output filename

        Returns:
            Path to saved plot
        """
        logger.info("Generating Pareto frontier plot...")

        fig, ax = plt.subplots(figsize=(10, 7))

        # Plot all strategies if provided
        if all_strategies_df is not None:
            # Color by strategy type
            strategy_colors = {
                'baseline_a_changed_only': '#E63946',
                'baseline_b_full_reindex': '#F4A261',
                'baseline_c_fixed_hop_k1': '#2A9D8F',
                'baseline_c_fixed_hop_k2': '#264653',
                'proposed_predictive': '#06D6A0'
            }

            for strategy_name in all_strategies_df['strategy'].unique():
                strategy_data = all_strategies_df[
                    all_strategies_df['strategy'] == strategy_name
                ]
                color = strategy_colors.get(strategy_name, '#888888')
                ax.scatter(strategy_data['update_percentage'],
                          strategy_data['recall'],
                          s=200, alpha=0.6, color=color,
                          label=strategy_name.replace('_', ' ').title())

        # Highlight Pareto-optimal points
        if not pareto_df.empty:
            ax.scatter(pareto_df['update_percentage'], pareto_df['recall'],
                      s=400, facecolors='none', edgecolors='red', linewidths=3,
                      label='Pareto Optimal', zorder=5)

            # Connect Pareto points
            pareto_sorted = pareto_df.sort_values('update_percentage')
            ax.plot(pareto_sorted['update_percentage'], pareto_sorted['recall'],
                   'r--', linewidth=2, alpha=0.7, label='Pareto Frontier')

        ax.set_xlabel('Percentage of Index Updated (%)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Recall@10', fontsize=12, fontweight='bold')
        ax.set_title('Pareto Frontier: Retrieval Quality vs. Maintenance Cost',
                     fontsize=14, fontweight='bold')
        ax.legend(loc='lower right', fontsize=9)
        ax.grid(True, alpha=0.3)

        # Set axis limits with padding
        if all_strategies_df is not None:
            x_max = all_strategies_df['update_percentage'].max() * 1.1
            y_min = all_strategies_df['recall'].min() * 0.9
            ax.set_xlim(0, x_max)
            ax.set_ylim(y_min, 1.05)

        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Pareto frontier plot saved to {output_path}")
        return str(output_path)

    def plot_strategy_comparison(self, strategies_results: Dict[str, Dict[str, float]],
                                 metrics: List[str] = ['recall_at_5', 'recall_at_10', 'rank_correlation'],
                                 output_file: str = "strategy_comparison.png") -> str:
        """
        Plot comparison of strategies across multiple metrics.

        Args:
            strategies_results: Results from evaluate_all_strategies
            metrics: List of metric names to plot
            output_file: Output filename

        Returns:
            Path to saved plot
        """
        logger.info("Generating strategy comparison plot...")

        # Prepare data
        strategy_names = []
        metric_values = {metric: [] for metric in metrics}

        for strategy_name, results in strategies_results.items():
            strategy_names.append(strategy_name.replace('_', ' ').title())
            for metric in metrics:
                metric_values[metric].append(results.get(metric, 0.0))

        # Create grouped bar chart
        x = np.arange(len(strategy_names))
        width = 0.25

        fig, ax = plt.subplots(figsize=(12, 6))

        colors = ['#2E86AB', '#A23B72', '#F18F01']
        for i, metric in enumerate(metrics):
            offset = (i - 1) * width
            bars = ax.bar(x + offset, metric_values[metric], width,
                         label=metric.replace('_', ' ').title(), color=colors[i], alpha=0.8)

        ax.set_xlabel('Strategy', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_title('Strategy Comparison Across Metrics', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(strategy_names, rotation=15, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Strategy comparison plot saved to {output_path}")
        return str(output_path)

    def plot_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray,
                              output_file: str = "confusion_matrix.png") -> str:
        """
        Plot confusion matrix for classification results.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            output_file: Output filename

        Returns:
            Path to saved plot
        """
        from sklearn.metrics import confusion_matrix

        logger.info("Generating confusion matrix plot...")

        cm = confusion_matrix(y_true, y_pred)

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                   cbar_kws={'label': 'Count'})

        ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
        ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
        ax.set_title('Confusion Matrix', fontsize=14, fontweight='bold')
        ax.set_xticklabels(['No Drift', 'Drift'])
        ax.set_yticklabels(['No Drift', 'Drift'])

        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Confusion matrix plot saved to {output_path}")
        return str(output_path)

    def plot_drift_distribution(self, drifts: Dict[str, float],
                                threshold: float = 0.02,
                                output_file: str = "drift_distribution.png") -> str:
        """
        Plot distribution of drift values.

        Args:
            drifts: Dictionary mapping entity_id to drift value
            threshold: Drift threshold
            output_file: Output filename

        Returns:
            Path to saved plot
        """
        logger.info("Generating drift distribution plot...")

        drift_values = list(drifts.values())

        fig, ax = plt.subplots(figsize=(10, 6))

        # Histogram
        n, bins, patches = ax.hist(drift_values, bins=50, color='#2E86AB',
                                   alpha=0.7, edgecolor='black', linewidth=0.5)

        # Add threshold line
        ax.axvline(x=threshold, color='red', linestyle='--', linewidth=2,
                  label=f'Threshold ({threshold})', alpha=0.8)

        # Add statistics
        mean_drift = np.mean(drift_values)
        median_drift = np.median(drift_values)
        ax.axvline(x=mean_drift, color='green', linestyle='-', linewidth=2,
                  label=f'Mean ({mean_drift:.4f})', alpha=0.8)
        ax.axvline(x=median_drift, color='orange', linestyle='-', linewidth=2,
                  label=f'Median ({median_drift:.4f})', alpha=0.8)

        ax.set_xlabel('Semantic Drift', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title('Distribution of Semantic Drift Values', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # Add text box with statistics
        stats_text = f'Total Entities: {len(drift_values)}\n'
        stats_text += f'Mean: {mean_drift:.4f}\n'
        stats_text += f'Median: {median_drift:.4f}\n'
        stats_text += f'Std: {np.std(drift_values):.4f}\n'
        stats_text += f'Above Threshold: {sum(1 for d in drift_values if d >= threshold)} ({sum(1 for d in drift_values if d >= threshold)/len(drift_values)*100:.1f}%)'

        ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.tight_layout()
        output_path = self.output_dir / output_file
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Drift distribution plot saved to {output_path}")
        return str(output_path)

    def generate_summary_report(self, results: Dict,
                                output_file: str = "summary_report.txt") -> str:
        """
        Generate text summary report of results.

        Args:
            results: Dictionary with experiment results
            output_file: Output filename

        Returns:
            Path to saved report
        """
        logger.info("Generating summary report...")

        output_path = self.output_dir / output_file

        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("PREDICTIVE SEMANTIC CACHE INVALIDATION - EXPERIMENT SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            # Model performance
            if 'model_metrics' in results:
                f.write("MODEL PERFORMANCE\n")
                f.write("-" * 80 + "\n")
                metrics = results['model_metrics']
                for key, value in metrics.items():
                    f.write(f"{key}: {value:.4f}\n")
                f.write("\n")

            # Feature importance
            if 'feature_importance' in results:
                f.write("TOP 10 FEATURE IMPORTANCES\n")
                f.write("-" * 80 + "\n")
                importance = results['feature_importance']
                for i, (feature, score) in enumerate(list(importance.items())[:10], 1):
                    f.write(f"{i}. {feature}: {score:.4f}\n")
                f.write("\n")

            # Strategy comparison
            if 'strategy_results' in results:
                f.write("STRATEGY COMPARISON\n")
                f.write("-" * 80 + "\n")
                strategy_results = results['strategy_results']

                for strategy_name, metrics in strategy_results.items():
                    f.write(f"\n{strategy_name.upper()}\n")
                    f.write(f"  Entities Updated: {metrics['entities_updated']} / {metrics['total_entities']} "
                           f"({metrics['update_percentage']:.2f}%)\n")
                    f.write(f"  Recall@5: {metrics.get('recall_at_5', 0):.4f}\n")
                    f.write(f"  Recall@10: {metrics.get('recall_at_10', 0):.4f}\n")
                    f.write(f"  Rank Correlation: {metrics.get('rank_correlation', 0):.4f}\n")
                    f.write(f"  Evaluation Time: {metrics.get('evaluation_time', 0):.4f}s\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")

        logger.info(f"Summary report saved to {output_path}")
        return str(output_path)
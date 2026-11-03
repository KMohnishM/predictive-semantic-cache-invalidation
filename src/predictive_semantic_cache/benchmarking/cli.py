"""Command-line entry point for the benchmark pipeline."""

from __future__ import annotations

import sys

try:
    from .runner import main
except ImportError:
    from predictive_semantic_cache.benchmarking.runner import main


if __name__ == "__main__":
    output_path = main(sys.argv[1:])
    print(output_path)

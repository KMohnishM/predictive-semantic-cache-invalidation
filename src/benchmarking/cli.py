"""Command-line entry point for the benchmark pipeline."""

from __future__ import annotations

import sys

from benchmarking.runner import main


if __name__ == "__main__":
    output_path = main(sys.argv[1:])
    print(output_path)

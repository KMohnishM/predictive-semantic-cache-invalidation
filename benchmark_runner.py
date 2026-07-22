#!/usr/bin/env python3
"""Top-level benchmark runner for repo-root execution."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarking.runner import main


if __name__ == "__main__":
    output_path = main(sys.argv[1:])
    print(output_path)

#!/usr/bin/env python3
"""Top-level benchmark runner for repo-root execution."""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve absolute path to 'src' directory and prepend it
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from benchmarking.runner import main

if __name__ == "__main__":
    output_path = main(sys.argv[1:])
    print(output_path)

#!/usr/bin/env python3
"""Quick test to verify all modules can be imported."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing module imports...")

try:
    from git_helper import GitHelper
    print("[OK] git_helper imported successfully")
except Exception as e:
    print(f"[FAIL] git_helper failed: {e}")

try:
    from repo_parser import RepoParser, Entity
    print("[OK] repo_parser imported successfully")
except Exception as e:
    print(f"[FAIL] repo_parser failed: {e}")

try:
    from embedding_manager import EmbeddingManager
    print("[OK] embedding_manager imported successfully")
except Exception as e:
    print(f"[FAIL] embedding_manager failed: {e}")

try:
    from feature_extractor import FeatureExtractor
    print("[OK] feature_extractor imported successfully")
except Exception as e:
    print(f"[FAIL] feature_extractor failed: {e}")

try:
    from predictor import DriftPredictor
    print("[OK] predictor imported successfully")
except Exception as e:
    print(f"[FAIL] predictor failed: {e}")

try:
    from evaluator import Evaluator, BaselineAChangedOnly, BaselineBFullReindex, BaselineCFixedHop, PredictiveStrategy
    print("[OK] evaluator imported successfully")
except Exception as e:
    print(f"[FAIL] evaluator failed: {e}")

try:
    from visualize import Visualizer
    print("[OK] visualize imported successfully")
except Exception as e:
    print(f"[FAIL] visualize failed: {e}")

print("\nAll module imports tested!")
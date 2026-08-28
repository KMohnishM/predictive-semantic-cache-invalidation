#!/usr/bin/env python3
"""Quick test to verify all reorganized modules can be imported."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing reorganized module imports...")

try:
    from core.git_helper import GitHelper
    print("[OK] core.git_helper imported successfully")
except Exception as e:
    print(f"[FAIL] core.git_helper failed: {e}")

try:
    from core.repo_parser import RepoParser, Entity
    print("[OK] core.repo_parser imported successfully")
except Exception as e:
    print(f"[FAIL] core.repo_parser failed: {e}")

try:
    from core.embedding_manager import EmbeddingManager
    print("[OK] core.embedding_manager imported successfully")
except Exception as e:
    print(f"[FAIL] core.embedding_manager failed: {e}")

try:
    from phase1_training.feature_extractor import FeatureExtractor
    print("[OK] phase1_training.feature_extractor imported successfully")
except Exception as e:
    print(f"[FAIL] phase1_training.feature_extractor failed: {e}")

try:
    from phase1_training.predictor import DriftPredictor
    print("[OK] phase1_training.predictor imported successfully")
except Exception as e:
    print(f"[FAIL] phase1_training.predictor failed: {e}")

try:
    from phase2_invalidation.evaluator import Evaluator, BaselineAChangedOnly, BaselineBFullReindex, BaselineCFixedHop, PredictiveStrategy
    print("[OK] phase2_invalidation.evaluator imported successfully")
except Exception as e:
    print(f"[FAIL] phase2_invalidation.evaluator failed: {e}")

try:
    from core.visualize import Visualizer
    print("[OK] core.visualize imported successfully")
except Exception as e:
    print(f"[FAIL] core.visualize failed: {e}")

print("\nAll reorganized module imports tested!")
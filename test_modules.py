#!/usr/bin/env python3
"""Quick test to verify all reorganized modules can be imported."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing reorganized module imports...")

try:
    from parser.git_helper import GitHelper
    print("[OK] parser.git_helper imported successfully")
except Exception as e:
    print(f"[FAIL] parser.git_helper failed: {e}")

try:
    from parser.repo_parser import RepoParser, Entity
    print("[OK] parser.repo_parser imported successfully")
except Exception as e:
    print(f"[FAIL] parser.repo_parser failed: {e}")

try:
    from embedder.embedding_manager import EmbeddingManager
    print("[OK] embedder.embedding_manager imported successfully")
except Exception as e:
    print(f"[FAIL] embedder.embedding_manager failed: {e}")

try:
    from extractor.feature_extractor import FeatureExtractor
    print("[OK] extractor.feature_extractor imported successfully")
except Exception as e:
    print(f"[FAIL] extractor.feature_extractor failed: {e}")

try:
    from predictor.predictor import DriftPredictor
    print("[OK] predictor.predictor imported successfully")
except Exception as e:
    print(f"[FAIL] predictor.predictor failed: {e}")

try:
    from evaluator.evaluator import Evaluator, BaselineAChangedOnly, BaselineBFullReindex, BaselineCFixedHop, PredictiveStrategy
    print("[OK] evaluator.evaluator imported successfully")
except Exception as e:
    print(f"[FAIL] evaluator.evaluator failed: {e}")

try:
    from visualizer.visualize import Visualizer
    print("[OK] visualizer.visualize imported successfully")
except Exception as e:
    print(f"[FAIL] visualizer.visualize failed: {e}")

print("\nAll reorganized module imports tested!")
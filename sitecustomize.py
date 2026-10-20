from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PKG = SRC / "predictive_semantic_cache"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

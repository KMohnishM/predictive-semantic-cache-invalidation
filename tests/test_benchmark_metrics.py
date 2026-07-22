import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.metrics import mean_reciprocal_rank, ndcg_at_k, rank_delta, recall_at_k, score_delta


class BenchmarkMetricTests(unittest.TestCase):
    def test_basic_metrics(self):
        ranked = ["a", "b", "c"]
        self.assertEqual(recall_at_k(ranked, "b", 2), 1.0)
        self.assertAlmostEqual(mean_reciprocal_rank(ranked, "b"), 0.5)
        self.assertGreater(ndcg_at_k(ranked, "b", 3), 0.0)
        self.assertEqual(rank_delta(1, 3), 2)
        self.assertEqual(score_delta(0.1, 0.25), 0.15)


if __name__ == "__main__":
    unittest.main()

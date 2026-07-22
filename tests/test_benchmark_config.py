import sys
import unittest
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.config import build_config, parse_top_k_values


class BenchmarkConfigTests(unittest.TestCase):
    def test_parse_top_k_values(self):
        self.assertEqual(parse_top_k_values("10, 5, 1, 5"), [1, 5, 10])

    def test_build_config(self):
        args = Namespace(
            repo_url="https://example.com/repo.git",
            repo_path=".",
            output_dir="results",
            benchmark_version="2.0",
            seed=99,
            num_commits=4,
            commit_stride=2,
            sampling_mode="stride",
            query_mode="synthetic",
            curated_queries_path=None,
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            clean_mode=True,
            top_k_values="1,3,5",
            max_queries_per_entity=2,
        )

        config = build_config(args)
        self.assertEqual(config.benchmark_version, "2.0")
        self.assertEqual(config.seed, 99)
        self.assertEqual(config.top_k_values, [1, 3, 5])
        self.assertTrue(config.clean_mode)


if __name__ == "__main__":
    unittest.main()

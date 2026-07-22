import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.serialization import persist_run
from benchmarking.types import BenchmarkConfig, BenchmarkSummary, CommitPair, PerQueryResult, QueryCase


class BenchmarkSerializationTests(unittest.TestCase):
    def test_persist_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = BenchmarkConfig(repo_url="url", repo_path=".", output_dir=tmpdir)
            commit_pairs = [CommitPair("a", "b", 0)]
            queries = [QueryCase("q1", "text", "synthetic", "changed_entity", "id", "name", "latest_snapshot", "b", "file.py", "function")]
            results = [PerQueryResult("run", "a", "b", "q1", "text", "synthetic", "changed_entity", "id", "name", "latest_snapshot", 1, 1, 0.9, 0.9, True, True, True, True, 0, 0.0, 1.0, "changed_only")]
            summary = BenchmarkSummary("run", 1, 1, 0, {"mrr": 1.0}, {"mrr": 1.0}, {"mrr": 0.0}, 1.0, 1.0, 1.0, True)

            run_dir = persist_run(tmpdir, config, commit_pairs, queries, results, summary)

            self.assertTrue((run_dir / "benchmark_config.json").exists())
            self.assertTrue((run_dir / "commit_pairs.json").exists())
            self.assertTrue((run_dir / "queries.json").exists())
            self.assertTrue((run_dir / "per_query_results.jsonl").exists())
            self.assertTrue((run_dir / "summary_metrics.json").exists())


if __name__ == "__main__":
    unittest.main()

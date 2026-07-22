import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.query_sources import build_queries, build_synthetic_queries, load_curated_queries
from benchmarking.repository_snapshot import RepositoryEntity, RepositorySnapshot
from benchmarking.types import CommitPair


class BenchmarkQuerySourceTests(unittest.TestCase):
    def test_synthetic_queries(self):
        snapshot = RepositorySnapshot(
            commit_hash="after",
            entities={
                "a.py::foo": RepositoryEntity("a.py::foo", "function", "a.py", 1, 3, "foo", "def foo():\n    return 1\n"),
                "a.py::Bar": RepositoryEntity("a.py::Bar", "class", "a.py", 5, 8, "Bar", "class Bar:\n    pass\n"),
            },
        )
        queries = build_synthetic_queries(snapshot, CommitPair("before", "after", 0), max_queries_per_entity=1)
        self.assertEqual(len(queries), 2)
        self.assertTrue(all(query.query_source == "synthetic" for query in queries))

    def test_build_queries_hybrid(self):
        snapshot = RepositorySnapshot(commit_hash="after", entities={})
        queries = build_queries(snapshot, CommitPair("before", "after", 0), "synthetic", None, 1)
        self.assertEqual(queries, [])


if __name__ == "__main__":
    unittest.main()

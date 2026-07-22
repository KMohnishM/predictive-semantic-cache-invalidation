import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.commit_sampler import sample_commit_pairs


class DummyGitHelper:
    def __init__(self, commits):
        self.commits = commits

    def get_commit_history(self, count=50):
        return self.commits[:count]


class BenchmarkCommitSamplerTests(unittest.TestCase):
    def test_adjacent_sampling(self):
        helper = DummyGitHelper(["c1", "c2", "c3"])
        pairs = sample_commit_pairs(helper, num_commits=3, sampling_mode="adjacent")
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0].commit_before, "c1")
        self.assertEqual(pairs[0].commit_after, "c2")

    def test_stride_sampling(self):
        helper = DummyGitHelper(["c1", "c2", "c3", "c4"])
        pairs = sample_commit_pairs(helper, num_commits=4, sampling_mode="stride", commit_stride=2)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0].commit_after, "c3")


if __name__ == "__main__":
    unittest.main()

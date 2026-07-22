import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from git_helper import GitHelper
from benchmarking.repository_snapshot import build_repository_snapshot


class BenchmarkRepositorySnapshotTests(unittest.TestCase):
    def test_snapshot_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True, text=True)
            (repo / "sample.py").write_text("def alpha():\n    return 1\n\nclass Beta:\n    def beta(self):\n        return 2\n", encoding="utf-8")
            subprocess.run(["git", "add", "sample.py"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)

            helper = GitHelper(str(repo))
            commit = helper.get_current_commit()
            snapshot = build_repository_snapshot(helper, commit)

            self.assertIn("sample.py::alpha", snapshot.entities)
            self.assertIn("sample.py::Beta", snapshot.entities)
            self.assertIn("sample.py::Beta::beta", snapshot.entities)


if __name__ == "__main__":
    unittest.main()

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.repository_snapshot import RepositoryEntity, RepositorySnapshot
from benchmarking.types import BenchmarkConfig, CommitPair
from benchmarking.runner import run_benchmark


class FakeEmbeddingManager:
    def __init__(self, model_name="fake", clean_mode=False):
        self.embeddings = {}

    def generate_embedding(self, entity_id, source_code):
        value = float(len(source_code) % 10 + 1)
        embedding = __import__("numpy").array([value, value / 10.0, 1.0], dtype=float)
        self.embeddings[entity_id] = embedding
        return embedding

    def find_similar_entities(self, query_embedding, entity_embeddings, top_k=10):
        scored = []
        for entity_id, embedding in entity_embeddings.items():
            score = float(query_embedding.dot(embedding))
            scored.append((entity_id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _create_temp_repo() -> Path:
    repo_dir = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True, capture_output=True, text=True)
    (repo_dir / "sample.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.py"], cwd=repo_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "first"], cwd=repo_dir, check=True, capture_output=True, text=True)
    (repo_dir / "sample.py").write_text("def alpha():\n    return 2\n\nclass Beta:\n    def beta(self):\n        return 3\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.py"], cwd=repo_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "second"], cwd=repo_dir, check=True, capture_output=True, text=True)
    return repo_dir


class BenchmarkRunnerSmokeTests(unittest.TestCase):
    def test_runner_executes_end_to_end(self):
        repo_dir = _create_temp_repo()
        with tempfile.TemporaryDirectory() as output_dir:
            config = BenchmarkConfig(
                repo_url=str(repo_dir),
                repo_path=str(repo_dir),
                output_dir=output_dir,
                num_commits=2,
                query_mode="synthetic",
                max_queries_per_entity=1,
            )

            with patch("benchmarking.runner.EmbeddingManager", FakeEmbeddingManager):
                run_dir = run_benchmark(config)

            self.assertTrue((run_dir / "benchmark_config.json").exists())
            self.assertTrue((run_dir / "summary_report.md").exists())


if __name__ == "__main__":
    unittest.main()

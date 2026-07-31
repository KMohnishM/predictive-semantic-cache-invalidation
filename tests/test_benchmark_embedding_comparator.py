import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarking.embedding_comparator import compare_index_snapshots
from benchmarking.types import IndexSnapshot


class BenchmarkEmbeddingComparatorTests(unittest.TestCase):
    def setUp(self):
        self.baseline_snapshot = IndexSnapshot(
            commit_hash="commit_after_hash",
            entity_embeddings={
                "mod.py::func_a": [1.0, 0.0, 0.0],
                "mod.py::func_b": [0.0, 1.0, 0.0],
                "new.py::func_c": [0.0, 0.0, 1.0],
            },
            entity_metadata={
                "mod.py::func_a": {"file_path": "mod.py", "entity_type": "function"},
                "mod.py::func_b": {"file_path": "mod.py", "entity_type": "function"},
                "new.py::func_c": {"file_path": "new.py", "entity_type": "function"},
            },
        )

        self.candidate_snapshot = IndexSnapshot(
            commit_hash="commit_after_hash",
            entity_embeddings={
                "mod.py::func_a": [1.0, 0.0, 0.0],  # Identical
                "mod.py::func_b": [0.0, 0.7071, 0.7071],  # Shifted
                "new.py::func_c": [0.0, 0.0, 1.0],  # Freshly re-embedded
            },
            entity_metadata=self.baseline_snapshot.entity_metadata,
        )

    def test_compare_index_snapshots_basic(self):
        modified_files = {"mod.py"}
        before_ids = {"mod.py::func_a", "mod.py::func_b"}

        result = compare_index_snapshots(
            baseline_snapshot=self.baseline_snapshot,
            candidate_snapshot=self.candidate_snapshot,
            modified_files=modified_files,
            strategy_name="changed_only",
            store_raw_vectors=True,
            before_entity_ids=before_ids,
            updated_entity_ids=["mod.py::func_a", "mod.py::func_b"],
        )

        self.assertEqual(result.strategy_name, "changed_only")
        self.assertEqual(result.total_entities, 3)
        self.assertAlmostEqual(result.updated_fraction, 2.0 / 3.0, places=4)

        comp_dict = {item.entity_id: item for item in result.per_entity_comparisons}
        self.assertIn("mod.py::func_a", comp_dict)
        self.assertIn("mod.py::func_b", comp_dict)
        self.assertIn("new.py::func_c", comp_dict)

        self.assertEqual(comp_dict["mod.py::func_a"].status, "modified")
        self.assertEqual(comp_dict["new.py::func_c"].status, "added")
        self.assertAlmostEqual(comp_dict["mod.py::func_a"].cosine_similarity, 1.0, places=4)
        self.assertAlmostEqual(comp_dict["mod.py::func_b"].cosine_similarity, 0.7071, places=3)
        self.assertIsNotNone(comp_dict["mod.py::func_a"].baseline_raw_vector)

    def test_compare_index_snapshots_no_raw_vectors(self):
        result = compare_index_snapshots(
            baseline_snapshot=self.baseline_snapshot,
            candidate_snapshot=self.candidate_snapshot,
            modified_files={"mod.py"},
            strategy_name="changed_only",
            store_raw_vectors=False,
        )

        for comp in result.per_entity_comparisons:
            self.assertIsNone(comp.baseline_raw_vector)
            self.assertIsNone(comp.candidate_raw_vector)


if __name__ == "__main__":
    unittest.main()

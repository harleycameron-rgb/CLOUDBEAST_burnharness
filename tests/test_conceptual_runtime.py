import unittest
from unittest.mock import patch

from conceptual_runtime import ARTIFACTS, initialize_conceptual_runtime


class ConceptualRuntimeTests(unittest.TestCase):
    def test_initialization_reports_symbolic_references_without_loading_files(self):
        with patch("builtins.open", side_effect=AssertionError("file access")):
            report = initialize_conceptual_runtime()

        self.assertTrue(report["runtime_initialized"])
        self.assertTrue(report["safe_symbolic_start"])
        self.assertEqual(report["coherence_check"], "conceptual_only")
        self.assertFalse(report["validator_executed"])
        self.assertFalse(report["agent_triggered"])
        self.assertFalse(report["glyph_generated"])
        self.assertFalse(report["activation_performed"])
        self.assertEqual(set(report["missing_artifacts"]), set(ARTIFACTS))
        self.assertTrue(all(not item["loaded"] for item in report["artifacts"].values()))
        self.assertEqual(report["sequence"][-1]["code"], "BH-08")
        self.assertEqual(report["data_source"], "in_memory_only")

    def test_root_argument_does_not_enable_file_access(self):
        report = initialize_conceptual_runtime("/path/that/is/not/read")
        self.assertEqual(set(report["missing_artifacts"]), set(ARTIFACTS))
        self.assertTrue(all(
            item["path"] == ARTIFACTS[name]
            for name, item in report["artifacts"].items()
        ))


if __name__ == "__main__":
    unittest.main()

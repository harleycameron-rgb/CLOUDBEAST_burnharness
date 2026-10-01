import tempfile
import unittest
from pathlib import Path

from conceptual_runtime import ARTIFACTS, initialize_conceptual_runtime


class ConceptualRuntimeTests(unittest.TestCase):
    def test_initialization_is_read_only_and_reports_missing_artifacts(self):
        report = initialize_conceptual_runtime()

        self.assertTrue(report["runtime_initialized"])
        self.assertTrue(report["safe_symbolic_start"])
        self.assertEqual(report["coherence_check"], "conceptual_only")
        self.assertFalse(report["validator_executed"])
        self.assertFalse(report["agent_triggered"])
        self.assertFalse(report["glyph_generated"])
        self.assertFalse(report["activation_performed"])
        self.assertIn("qob_algebra", report["missing_artifacts"])
        self.assertIn("glyph_prompt", report["missing_artifacts"])
        self.assertEqual(report["sequence"][-1]["code"], "BH-08")

    def test_artifact_loading_does_not_require_engine_execution(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for relative_path in ARTIFACTS.values():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("symbolic reference", encoding="utf-8")

            report = initialize_conceptual_runtime(root)

        self.assertEqual(report["missing_artifacts"], ())
        self.assertTrue(all(item["loaded"] for item in report["artifacts"].values()))
        self.assertFalse(report["validator_executed"])
        self.assertFalse(report["activation_performed"])


if __name__ == "__main__":
    unittest.main()

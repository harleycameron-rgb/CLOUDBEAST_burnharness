import unittest

from burnharness.ignition_layer.generate_leg_ignition_layer import (
    LEGS,
    main as generate_legs,
)
from generate_leg_couplers import COUPLER_MAP, main as generate_couplers
from stabiliser import STEP_SEQUENCE, Stabiliser
from src.run_supervised_build import run_supervised_build
from zero_data import FileIOViolation, forbid_file_io


class StabiliserTests(unittest.TestCase):
    def test_records_only_expected_ordered_steps(self):
        stabiliser = Stabiliser()
        for name in STEP_SEQUENCE:
            record = stabiliser.record(name, {"passed": True})
            self.assertTrue(record["passed"])
            self.assertEqual(len(record["sha512"]), 128)
        self.assertEqual(len(stabiliser.finish()), len(STEP_SEQUENCE))

    def test_rejects_invalid_or_out_of_order_steps(self):
        stabiliser = Stabiliser()
        with self.assertRaises(ValueError):
            stabiliser.record("unknown", {})
        with self.assertRaises(ValueError):
            stabiliser.record("superblock", {})
        with self.assertRaises(ValueError):
            stabiliser.record("benchmark", {"not_json": object()})

    def test_repeat_verification_rejects_drift(self):
        with self.assertRaises(RuntimeError):
            Stabiliser.verify_repeat(
                [{"step": "benchmark", "sha512": "a"}],
                [{"step": "benchmark", "sha512": "b"}],
            )
        self.assertTrue(Stabiliser.verify_repeat([{"step": "x"}], [{"step": "x"}]))


class ZeroDataTests(unittest.TestCase):
    def test_guard_rejects_python_filesystem_access(self):
        with self.assertRaises(FileIOViolation):
            with forbid_file_io():
                open("not-created.txt", "w")
        with self.assertRaises(FileIOViolation):
            with forbid_file_io():
                import os
                os.listdir(".")
        with self.assertRaises(FileIOViolation):
            with forbid_file_io():
                from pathlib import Path
                Path("not-read.txt").read_text()

    def test_coupler_generator_returns_in_memory_content(self):
        with forbid_file_io():
            generated = generate_couplers()
        self.assertEqual(set(generated), set(COUPLER_MAP))
        self.assertTrue(all(
            set(files) == {"coupler.py", "coupler_manifest.json"}
            for files in generated.values()
        ))

    def test_leg_generator_returns_in_memory_content(self):
        with forbid_file_io():
            generated = generate_legs()
        self.assertEqual(set(generated), set(LEGS))
        self.assertTrue(all(
            set(files) == {"ignition_stub.py", "leg_manifest.json"}
            for files in generated.values()
        ))

    def test_supervised_pipeline_is_in_memory_and_reproducible(self):
        result = run_supervised_build()
        repeated = run_supervised_build()
        self.assertTrue(result["passed"])
        self.assertTrue(result["deterministic"])
        self.assertFalse(result["persistent_artifacts"])
        self.assertEqual(len(result["steps"]), len(STEP_SEQUENCE))
        self.assertEqual(result["sentinel_hash"], repeated["sentinel_hash"])
        self.assertEqual(result["outputs"]["burn_report"]["passed"], True)


if __name__ == "__main__":
    unittest.main()

import unittest
import math
from unittest.mock import patch

import system_validation as validation


FIELD = {"stability": 0.5, "curvature": 0.2, "provenance": 0.1}


class ValidationHarness(unittest.TestCase):

    # ------------------------------------------------------------
    # HEARTBEAT / READINESS
    # ------------------------------------------------------------
    def test_heartbeat_requires_all_checks(self):
        passing = {
            check: True for check in (
                "environment_ready", "boundary_valid", "stable",
                "consistent", "integrity_verified"
            )
        }
        with patch.object(validation, "validate_system", return_value=passing):
            self.assertTrue(validation.system_heartbeat())

        for failed in passing:
            with self.subTest(failed=failed):
                failing = {**passing, failed: False}
                with patch.object(validation, "validate_system",
                                  return_value=failing):
                    self.assertFalse(validation.system_heartbeat())

    # ------------------------------------------------------------
    # BASELINE SYSTEM READINESS
    # ------------------------------------------------------------
    def test_local_system_is_ready(self):
        report = validation.validate_system()
        self.assertTrue(report["system_ready"])
        self.assertEqual(report["drift"], 0)
        self.assertEqual(len(report["sha512"]), 128)

    # ------------------------------------------------------------
    # BOUNDARY VALIDATION
    # ------------------------------------------------------------
    def test_boundary_rejects_bad_inputs(self):
        invalid = [
            {}, {"stability": 0.3, "curvature": 0.2},
            {**FIELD, "other": 0}, {**FIELD, "stability": True},
            {**FIELD, "stability": float("nan")},
            {**FIELD, "stability": float("inf")},
            {**FIELD, "stability": -0.1}, {**FIELD, "stability": 1.1},
            {**FIELD, "stability": []},
        ]
        for data in invalid:
            with self.subTest(data=data):
                self.assertFalse(validation.check_boundary(data))
                self.assertFalse(validation.validate_system(data)["system_ready"])

        # Oversized input
        with patch.object(validation, "MAX_INPUT_BYTES", 1):
            self.assertFalse(validation.check_boundary(FIELD))

    # ------------------------------------------------------------
    # DRIFT THRESHOLD
    # ------------------------------------------------------------
    def test_drift_threshold(self):
        for difference, expected in ((0.049, True), (0.05, False)):
            with self.subTest(difference=difference):
                changed = {**FIELD, "stability": FIELD["stability"] + difference}
                with patch.object(validation, "run_cycle",
                                  side_effect=[FIELD, FIELD, changed]):
                    report = validation.validate_system()
                self.assertEqual(report["stable"], expected)
                self.assertEqual(report["system_ready"], expected)
                self.assertTrue(math.isclose(report["drift"], difference))

    # ------------------------------------------------------------
    # FAIL-CLOSED BEHAVIOUR
    # ------------------------------------------------------------
    def test_cycle_failure_and_malformed_output(self):
        with patch.object(validation, "run_cycle", side_effect=RuntimeError("failed")):
            self.assertFalse(validation.validate_system()["system_ready"])

        with patch.object(validation, "run_cycle", return_value={"stability": 0.1}):
            self.assertFalse(validation.validate_system()["system_ready"])

    # ------------------------------------------------------------
    # ENVIRONMENT VALIDATION
    # ------------------------------------------------------------
    def test_environment_rejects_missing_modules_and_bad_config(self):
        with patch.object(validation.importlib, "import_module",
                          side_effect=ModuleNotFoundError):
            self.assertFalse(validation.check_environment())
            self.assertFalse(validation.validate_system()["system_ready"])

        with patch.object(validation.json, "load", return_value={"leg": "scandoc"}):
            self.assertFalse(validation.check_environment())

    # ------------------------------------------------------------
    # CONFIGURATION DRIFT
    # ------------------------------------------------------------
    def test_configuration_drift(self):
        with patch.object(validation, "_configuration_snapshot",
                          side_effect=[("before",), ("after",)]):
            report = validation.validate_system()
        self.assertFalse(report["environment_ready"])
        self.assertFalse(report["system_ready"])

    # ------------------------------------------------------------
    # INTEGRITY / CANONICAL CORE
    # ------------------------------------------------------------
    def test_integrity_hash(self):
        self.assertTrue(validation.check_consistency(FIELD))
        verified, digest = validation.check_integrity(FIELD)
        self.assertTrue(verified)
        self.assertEqual(digest, validation.check_integrity(dict(reversed(
            list(FIELD.items())
        )))[1])
        self.assertNotEqual(digest, validation.check_integrity(
            {**FIELD, "stability": 0.4}
        )[1])

    # ------------------------------------------------------------
    # CHAOS MODE: LOGISTIC MAP INPUTS
    # ------------------------------------------------------------
    def test_chaotic_input_rejected(self):
        def logistic(seed, r=3.99, steps=32):
            x = seed
            out = []
            for _ in range(steps):
                x = r * x * (1 - x)
                out.append(x)
            return out

        chaotic_inputs = [
            {"stability": x, "curvature": 0.2, "provenance": 0.1}
            for x in logistic(0.123)
        ]

        for data in chaotic_inputs:
            with self.subTest(data=data):
                if not (0 <= data["stability"] <= 1):
                    self.assertFalse(validation.check_boundary(data))
                else:
                    report = validation.validate_system(data)
                    self.assertFalse(report["system_ready"])

    # ------------------------------------------------------------
    # CHAOTIC DRIFT INJECTION
    # ------------------------------------------------------------
    def test_chaotic_drift(self):
        chaotic_values = [0.5, 0.5001, 0.47, 0.61, 0.499, 0.8]

        for value in chaotic_values:
            with self.subTest(value=value):
                changed = {**FIELD, "stability": value}
                with patch.object(validation, "run_cycle",
                                  side_effect=[FIELD, FIELD, changed]):
                    report = validation.validate_system()

                drift = abs(value - FIELD["stability"])
                if drift < 0.05:
                    self.assertTrue(report["stable"])
                    self.assertTrue(report["system_ready"])
                else:
                    self.assertFalse(report["stable"])
                    self.assertFalse(report["system_ready"])

    # ------------------------------------------------------------
    # CHAOTIC CONFIGURATION MUTATION
    # ------------------------------------------------------------
    def test_chaotic_configuration_mutation(self):
        chaotic_configs = [
            ("before",),
            ("before", "extra"),
            ("after",),
            ("before", "before"),
            ("random",),
        ]

        for snapshot in chaotic_configs:
            with self.subTest(snapshot=snapshot):
                with patch.object(validation, "_configuration_snapshot",
                                  side_effect=[("baseline",), snapshot]):
                    report = validation.validate_system()
                    if snapshot != ("baseline",):
                        self.assertFalse(report["environment_ready"])
                        self.assertFalse(report["system_ready"])

    # ------------------------------------------------------------
    # CHAOTIC INTEGRITY STRESS
    # ------------------------------------------------------------
    def test_chaotic_integrity_stress(self):
        chaotic_fields = [
            {"stability": 0.5 + math.sin(i), "curvature": 0.2, "provenance": 0.1}
            for i in range(10)
        ]

        for data in chaotic_fields:
            with self.subTest(data=data):
                verified, digest = validation.check_integrity(data)
                self.assertEqual(len(digest), 128)
                if not (0 <= data["stability"] <= 1):
                    self.assertFalse(verified)


if __name__ == "__main__":
    unittest.main()

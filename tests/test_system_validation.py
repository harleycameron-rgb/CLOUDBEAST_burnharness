import math
import unittest
from unittest.mock import patch

import system_validation as validation
from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import (
    SentinelDotIgnitionStub,
)
from coordinator import SentinelDotCoordinator, bootstrap_genesis


FIELD = {"stability": 0.5, "curvature": 0.2, "provenance": 0.1}


class SystemValidationTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = SentinelDotCoordinator()
        for instance_id in self.coordinator.instance_ids:
            SentinelDotIgnitionStub().bind(self.coordinator, instance_id)
        bootstrap_genesis(self.coordinator)

    def test_system_heartbeat_requires_every_readiness_check(self):
        passing_report = {
            check: True for check in (
                "environment_ready", "boundary_valid", "stable", "consistent",
                "integrity_verified"
            )
        }
        with patch.object(validation, "validate_system", return_value=passing_report):
            self.assertTrue(
                validation.system_heartbeat(self.coordinator)["readiness"]
            )

        for failed_check in passing_report:
            with self.subTest(failed_check=failed_check):
                failing_report = {**passing_report, failed_check: False}
                with patch.object(validation, "validate_system",
                                  return_value=failing_report):
                    self.assertFalse(
                        validation.system_heartbeat(self.coordinator)["readiness"]
                    )

    def test_local_system_is_ready(self):
        report = validation.validate_system()
        self.assertTrue(report["system_ready"])
        self.assertEqual(report["drift"], 0)
        self.assertEqual(len(report["sha512"]), 128)

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
        with patch.object(validation, "MAX_INPUT_BYTES", 1):
            self.assertFalse(validation.check_boundary(FIELD))

    def test_chaotic_input_is_rejected_as_inconsistent(self):
        def chaotic_sequence(seed, r=3.99, steps=64):
            x = seed
            out = []
            for _ in range(steps):
                x = r * x * (1 - x)
                out.append(x)
            return out

        chaotic_inputs = [
            {"stability": x, "curvature": 0.2, "provenance": 0.1}
            for x in chaotic_sequence(0.123)
        ]

        for data in chaotic_inputs:
            with self.subTest(data=data):
                self.assertTrue(validation.check_boundary(data))
                report = validation.validate_system(data)
                self.assertFalse(report["consistent"])
                self.assertFalse(report["system_ready"])

    def test_drift_is_strictly_below_limit(self):
        for difference, expected in ((0.049, True), (0.05, False)):
            with self.subTest(difference=difference):
                changed = {**FIELD, "stability": FIELD["stability"] + difference}
                with patch.object(validation, "run_cycle",
                                  side_effect=[FIELD, FIELD, changed]):
                    report = validation.validate_system()
                self.assertEqual(report["stable"], expected)
                self.assertEqual(report["system_ready"], expected)
                self.assertTrue(math.isclose(report["drift"], difference))

    def test_chaotic_drift_detection(self):
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

    def test_cycle_failure_and_malformed_output_fail_closed(self):
        with patch.object(validation, "run_cycle", side_effect=RuntimeError("failed")):
            self.assertFalse(validation.validate_system()["system_ready"])
        with patch.object(validation, "run_cycle", return_value={"stability": 0.1}):
            self.assertFalse(validation.validate_system()["system_ready"])

    def test_adversarial_cycle_fields_fail_closed(self):
        malformed_samples = (
            {**FIELD, "stability": float("nan")},
            {**FIELD, "curvature": True},
            {**FIELD, "unexpected": 0},
        )
        for malformed in malformed_samples:
            with self.subTest(malformed=malformed):
                with patch.object(validation, "run_cycle", return_value=malformed):
                    report = validation.validate_system()

                self.assertFalse(report["boundary_valid"])
                self.assertFalse(report["system_ready"])
                self.assertIsNone(report["canonical_model"])
                self.assertIsNone(report["sha512"])

    def test_configuration_change_during_cycle_fails_closed(self):
        with patch.object(
            validation, "_configuration_snapshot",
            side_effect=[("before",), ("after",)],
        ), patch.object(validation, "run_cycle", return_value=FIELD):
            report = validation.validate_system()

        self.assertFalse(report["environment_ready"])
        self.assertFalse(report["system_ready"])
        self.assertIsNone(report["canonical_model"])
        self.assertIsNone(report["sha512"])

    def test_environment_rejects_missing_modules_and_bad_config(self):
        with patch.object(validation.importlib, "import_module",
                          side_effect=ModuleNotFoundError):
            self.assertFalse(validation.check_environment())
            self.assertFalse(validation.validate_system()["system_ready"])
        with patch.object(validation.json, "load", return_value={"leg": "scandoc"}):
            self.assertFalse(validation.check_environment())

    def test_changed_configuration_fails_readiness(self):
        with patch.object(validation, "_configuration_snapshot",
                          side_effect=[("before",), ("after",)]):
            report = validation.validate_system()
        self.assertFalse(report["environment_ready"])
        self.assertFalse(report["system_ready"])

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

    def test_chaotic_integrity_stress(self):
        chaotic_fields = [
            {"stability": 0.5 + math.sin(i), "curvature": 0.2, "provenance": 0.1}
            for i in range(10)
        ]

        for data in chaotic_fields:
            with self.subTest(data=data):
                verified, digest = validation.check_integrity(data)
                # Hash must always be 128 chars
                self.assertEqual(len(digest), 128)
                # Integrity must fail if stability leaves valid range
                if not (0 <= data["stability"] <= 1):
                    self.assertFalse(verified)

    def test_canonical_hash_is_repeatable_and_input_sensitive(self):
        self.assertTrue(validation.check_consistency(FIELD))
        verified, digest = validation.check_integrity(FIELD)
        self.assertTrue(verified)
        self.assertEqual(digest, validation.check_integrity(dict(reversed(
            list(FIELD.items())
        )))[1])
        self.assertNotEqual(digest, validation.check_integrity(
            {**FIELD, "stability": 0.4}
        )[1])


if __name__ == "__main__":
    unittest.main()

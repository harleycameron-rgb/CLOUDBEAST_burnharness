import math
import unittest

from UNIFIED_FIELD_ZIPGATE.geometry.ignition.ignition_algebra import (
    destiny_alignment,
    harmonic_field,
    ignition_condition,
    ignition_time,
    system_recurrence,
)
from burnharness_protocol import PROTOCOL


class IgnitionAlgebraTests(unittest.TestCase):
    def test_harmonic_field_sums_complex_phasors(self):
        result = harmonic_field(0, [1, 2], [0, 0])
        self.assertAlmostEqual(result.real, 2)
        self.assertAlmostEqual(result.imag, 0)

    def test_harmonic_field_rejects_invalid_parameters(self):
        with self.assertRaises(ValueError):
            harmonic_field(0, [1], [])
        with self.assertRaises(ValueError):
            harmonic_field(float("nan"), [1], [0])

    def test_ignition_time_and_equal_frequency(self):
        self.assertAlmostEqual(ignition_time(0, math.pi, 2, 1), math.pi)
        self.assertIsNone(ignition_time(0, 1, 2, 2))

    def test_flow_alignment_uses_strict_tolerance(self):
        self.assertTrue(ignition_condition(1.0, 0.9, 0.11))
        self.assertFalse(ignition_condition(1.0, 0.0, 1.0))
        self.assertFalse(ignition_condition(1, 1, 0))

    def test_recurrence_requires_lock_core_and_harmonic_alignment(self):
        domains = {"S1": (-1, 1), "S2": (-1, 1)}
        self.assertTrue(destiny_alignment(0.5, domains))
        self.assertEqual(
            system_recurrence(0.9, 0.5, {"S1": 0, "S2": 1}, domains, 0.5),
            1,
        )
        self.assertEqual(
            system_recurrence(0.5, 0.5, {"S1": 0, "S2": 1}, domains, 0.5),
            0,
        )
        self.assertEqual(
            system_recurrence(0.9, 0.5, {"S1": 0, "S2": 2}, domains, 0.5),
            0,
        )
        self.assertEqual(
            system_recurrence(0.9, 0.5, {"S1": 0}, domains, 0.5),
            0,
        )

    def test_protocol_registers_ignition_algebra(self):
        self.assertEqual(
            PROTOCOL["geometry_system"]["ignition_algebra"]["alliance_lock"],
            "ρ(t) > ρ_min",
        )


if __name__ == "__main__":
    unittest.main()

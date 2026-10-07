import math
import unittest
from unittest.mock import patch

import chaos_harness


class ChaosInjectorTests(unittest.TestCase):
    def test_deterministic_generators_match_their_definitions(self):
        self.assertEqual(chaos_harness.ChaosInjector.logistic(0.25, r=2, steps=3), [
            0.375, 0.46875, 0.498046875,
        ])
        self.assertEqual(
            chaos_harness.ChaosInjector.sinusoidal(0, steps=3),
            [0.5 + math.sin(index) for index in range(3)],
        )
        self.assertEqual(chaos_harness.ChaosInjector.logistic(0.25, steps=0), [])
        self.assertEqual(chaos_harness.ChaosInjector.sinusoidal(0, steps=0), [])

    def test_brownian_generator_accumulates_each_step(self):
        with patch.object(
            chaos_harness.random, "uniform", side_effect=[0.1, -0.2, 0.05]
        ) as uniform:
            result = chaos_harness.ChaosInjector.brownian(0.5, steps=3)

        for actual, expected in zip(result, (0.6, 0.4, 0.45)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(uniform.call_count, 3)

    def test_permutation_shuffles_a_copy(self):
        values = [1, 2, 3]
        with patch.object(chaos_harness.random, "shuffle", side_effect=lambda items: items.reverse()):
            result = chaos_harness.ChaosInjector.permutation(values)

        self.assertEqual(result, [3, 2, 1])
        self.assertEqual(values, [1, 2, 3])
        self.assertIsNot(result, values)


class MutationFuzzerTests(unittest.TestCase):
    def test_each_field_mutation_handles_numeric_and_invalid_values(self):
        expected = (0.6, float("nan"), float("inf"), -0.5, 0.75, None, [])
        for index, mutation in enumerate(expected):
            with self.subTest(mutation=index):
                with patch.object(
                    chaos_harness.random, "choice",
                    side_effect=lambda options, index=index: options[index],
                ), patch.object(
                    chaos_harness.random, "uniform",
                    return_value=1.5 if index == 4 else 0.1,
                ):
                    result = chaos_harness.MutationFuzzer.mutate_field(0.5)

                if isinstance(mutation, float) and math.isnan(mutation):
                    self.assertTrue(math.isnan(result))
                elif isinstance(mutation, float) and math.isinf(mutation):
                    self.assertTrue(math.isinf(result))
                else:
                    self.assertEqual(result, mutation)

    def test_mutate_dict_changes_only_a_copy(self):
        original = {"stability": 0.5, "curvature": 0.2}
        with patch.object(
            chaos_harness.random, "choice", side_effect=lambda options: options[0]
        ), patch.object(chaos_harness.random, "uniform", return_value=0.1):
            mutated = chaos_harness.MutationFuzzer.mutate_dict(original)

        self.assertEqual(original, {"stability": 0.5, "curvature": 0.2})
        self.assertEqual(mutated, {"stability": 0.6, "curvature": 0.2})
        self.assertIsNot(mutated, original)


class ChaosUtilityTests(unittest.TestCase):
    def test_stress_runner_records_failures_and_marks_malformed_drift(self):
        field = {"stability": 0.5}
        with patch.object(
            chaos_harness.validation, "run_cycle",
            side_effect=[{"stability": 0.6}, RuntimeError("cycle failed"), {}],
        ):
            outputs = chaos_harness.StressRunner.run_stress(field, cycles=3)

        self.assertEqual(outputs, [{"stability": 0.6}, None, {}])
        drift = chaos_harness.StressRunner.compute_drift_series(outputs, field)
        self.assertAlmostEqual(drift[0], 0.1)
        self.assertEqual(drift[1:], [float("inf"), float("inf")])

    def test_replay_returns_a_separate_event_list(self):
        replay = chaos_harness.ReplayHarness()
        event = ({"input": 1}, {"output": 2})
        replay.record(*event)

        first_read = replay.replay()
        first_read.clear()

        self.assertEqual(replay.replay(), [event])
        self.assertIsNot(replay.replay(), replay.events)

    def test_chaos_profile_counts_rejections_and_readiness_failures(self):
        valid = {
            "stability": 0.5, "curvature": 0.2, "provenance": 0.1,
        }
        invalid = {**valid, "stability": -0.1}

        profile = chaos_harness.ChaosProfile.generate(
            [0.0, 0.06, float("inf")], [valid, None, invalid]
        )

        self.assertEqual(profile["max_drift"], float("inf"))
        self.assertEqual(profile["min_drift"], 0.0)
        self.assertEqual(profile["chaos_rejections"], 1)
        self.assertEqual(profile["boundary_failures"], 1)
        self.assertEqual(profile["integrity_failures"], 1)
        self.assertEqual(profile["stable_cycles"], 1)
        self.assertEqual(profile["unstable_cycles"], 2)


if __name__ == "__main__":
    unittest.main()

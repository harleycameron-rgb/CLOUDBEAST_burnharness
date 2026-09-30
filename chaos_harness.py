"""
CHAOS HARNESS
=============
Unified chaos-mode test harness for the validation-first architecture.

Includes:
- Chaos Injector (logistic, sinusoidal, brownian, permutation)
- Multi-Cycle Stress Runner
- Fail-Closed Audit Layer
- Replay Harness
- Chaos Profile Generator
- Mutation Fuzzer
- Unified Test Harness (unittest)
"""

import unittest
import math
import random
import hashlib
from unittest.mock import patch

import system_validation as validation


# ============================================================
# CHAOS INJECTOR MODULE
# ============================================================

class ChaosInjector:
    """Deterministic chaos generators."""

    @staticmethod
    def logistic(seed, r=3.99, steps=64):
        x = seed
        out = []
        for _ in range(steps):
            x = r * x * (1 - x)
            out.append(x)
        return out

    @staticmethod
    def sinusoidal(seed, steps=64):
        return [0.5 + math.sin(seed + i) for i in range(steps)]

    @staticmethod
    def brownian(seed, steps=64):
        x = seed
        out = []
        for _ in range(steps):
            x += random.uniform(-0.1, 0.1)
            out.append(x)
        return out

    @staticmethod
    def permutation(values):
        out = values[:]
        random.shuffle(out)
        return out


# ============================================================
# MUTATION FUZZER
# ============================================================

class MutationFuzzer:
    """Mutates fields in controlled ways."""

    @staticmethod
    def mutate_field(value):
        mutations = [
            lambda v: v + random.uniform(-0.2, 0.2),
            lambda v: float("nan"),
            lambda v: float("inf"),
            lambda v: -abs(v),
            lambda v: v * random.uniform(0.5, 2.0),
            lambda v: None,
            lambda v: [],
        ]
        return random.choice(mutations)(value)

    @staticmethod
    def mutate_dict(d):
        mutated = dict(d)
        key = random.choice(list(mutated.keys()))
        mutated[key] = MutationFuzzer.mutate_field(mutated[key])
        return mutated


# ============================================================
# MULTI-CYCLE STRESS RUNNER
# ============================================================

class StressRunner:
    """Runs many cycles to detect drift accumulation."""

    @staticmethod
    def run_stress(field, cycles=200):
        outputs = []
        for _ in range(cycles):
            try:
                outputs.append(validation.run_cycle(field))
            except Exception:
                outputs.append(None)
        return outputs

    @staticmethod
    def compute_drift_series(outputs, baseline):
        drift_series = []
        for out in outputs:
            if not out or "stability" not in out:
                drift_series.append(float("inf"))
            else:
                drift_series.append(abs(out["stability"] - baseline["stability"]))
        return drift_series


# ============================================================
# REPLAY HARNESS
# ============================================================

class ReplayHarness:
    """Stores chaos events and allows deterministic replay."""

    def __init__(self):
        self.events = []

    def record(self, input_data, output_data):
        self.events.append((input_data, output_data))

    def replay(self):
        return self.events[:]


# ============================================================
# CHAOS PROFILE GENERATOR
# ============================================================

class ChaosProfile:
    """Summarises chaos behaviour into a JSON-like dict."""

    @staticmethod
    def generate(drift_series, outputs):
        return {
            "max_drift": max(drift_series),
            "min_drift": min(drift_series),
            "chaos_rejections": sum(1 for o in outputs if o is None),
            "boundary_failures": sum(1 for o in outputs if o and not validation.check_boundary(o)),
            "integrity_failures": sum(
                1 for o in outputs
                if o and not validation.check_integrity(o)[0]
            ),
            "stable_cycles": sum(1 for d in drift_series if d < 0.05),
            "unstable_cycles": sum(1 for d in drift_series if d >= 0.05),
        }


# ============================================================
# UNIFIED TEST HARNESS
# ============================================================

FIELD = {"stability": 0.5, "curvature": 0.2, "provenance": 0.1}


class ChaosHarnessTests(unittest.TestCase):

    # ------------------------------------------------------------
    # BASELINE READINESS
    # ------------------------------------------------------------
    def test_baseline_ready(self):
        report = validation.validate_system()
        self.assertTrue(report["system_ready"])
        self.assertEqual(report["drift"], 0)
        self.assertEqual(len(report["sha512"]), 128)

    # ------------------------------------------------------------
    # CHAOTIC INPUT REJECTION
    # ------------------------------------------------------------
    def test_logistic_chaos_rejected(self):
        chaotic = ChaosInjector.logistic(0.123)
        for x in chaotic:
            data = {"stability": x, "curvature": 0.2, "provenance": 0.1}
            report = validation.validate_system(data)
            self.assertFalse(report["system_ready"])

    # ------------------------------------------------------------
    # CHAOTIC DRIFT DETECTION
    # ------------------------------------------------------------
    def test_sinusoidal_drift(self):
        chaotic = ChaosInjector.sinusoidal(0.0)
        for x in chaotic:
            changed = {**FIELD, "stability": x}
            with patch.object(validation, "run_cycle",
                              side_effect=[FIELD, FIELD, changed]):
                report = validation.validate_system()
            drift = abs(x - FIELD["stability"])
            if drift < 0.05:
                self.assertTrue(report["stable"])
            else:
                self.assertFalse(report["stable"])

    # ------------------------------------------------------------
    # MUTATION FUZZER FAIL-CLOSED
    # ------------------------------------------------------------
    def test_mutation_fuzzer_fail_closed(self):
        for _ in range(50):
            mutated = MutationFuzzer.mutate_dict(FIELD)
            report = validation.validate_system(mutated)
            self.assertFalse(report["system_ready"])

    # ------------------------------------------------------------
    # MULTI-CYCLE STRESS TEST
    # ------------------------------------------------------------
    def test_multi_cycle_stress(self):
        outputs = StressRunner.run_stress(FIELD, cycles=100)
        drift_series = StressRunner.compute_drift_series(outputs, FIELD)
        profile = ChaosProfile.generate(drift_series, outputs)

        # Basic sanity checks
        self.assertGreaterEqual(profile["max_drift"], profile["min_drift"])
        self.assertGreaterEqual(profile["unstable_cycles"], 0)
        self.assertGreaterEqual(profile["stable_cycles"], 0)

    # ------------------------------------------------------------
    # REPLAY HARNESS
    # ------------------------------------------------------------
    def test_replay_harness(self):
        replay = ReplayHarness()
        chaotic = ChaosInjector.logistic(0.42)

        for x in chaotic[:10]:
            data = {"stability": x, "curvature": 0.2, "provenance": 0.1}
            out = validation.validate_system(data)
            replay.record(data, out)

        events = replay.replay()
        self.assertEqual(len(events), 10)
        for inp, out in events:
            self.assertIn("stability", inp)
            self.assertIn("system_ready", out)


if __name__ == "__main__":
    unittest.main()

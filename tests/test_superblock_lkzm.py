import copy
import math
import unittest

import numpy as np

from benchmarks.fire import build_registry, fire_couplers, probe_adapters
from causal_lkzm.harness import (
    append_event, burn, causal_curve, core_curve, event_log_from_field,
    gauss_linking_number, lk_integer, segment_gap, verify_log,
)
from superblock.superblock import GENESIS_PARENT, build_superblock, verify_chain

FIELD = {"stability": 0.16658333333333333, "curvature": 0.0025,
         "provenance": 8.333333333333334e-06}


def circle(n, centre=(0, 0, 0), plane="xy"):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    c, s, z = np.cos(t), np.sin(t), np.zeros_like(t)
    pts = {"xy": (c, s, z), "xz": (c, z, s)}[plane]
    return np.stack(pts, 1) + np.asarray(centre, float)


class LinkingNumberTests(unittest.TestCase):
    def test_hopf_link_is_unit(self):
        self.assertEqual(abs(lk_integer(circle(64), circle(64, (1, 0, 0), "xz"))), 1)

    def test_separated_circles_unlinked(self):
        self.assertEqual(lk_integer(circle(64), circle(64, (0, 0, 5))), 0)

    def test_matches_direct_gauss_integral(self):
        A, B = circle(1500), circle(1500, (1, 0, 0), "xz")
        dA, dB = np.roll(A, -1, 0) - A, np.roll(B, -1, 0) - B
        r = A[:, None] - B[None]
        direct = np.sum(np.einsum("ijk,ijk->ij", r, np.cross(dA[:, None], dB[None]))
                        / np.linalg.norm(r, axis=-1) ** 3) / (4 * math.pi)
        self.assertAlmostEqual(direct, gauss_linking_number(A, B), places=4)

    def test_causal_curve_realises_declared_winding(self):
        log = event_log_from_field(FIELD, 160)
        for k in (-3, -1, 1, 2, 5, 9):
            self.assertEqual(lk_integer(core_curve(160), causal_curve(log, k)), k)

    def test_lk_antisymmetric_under_single_reversal(self):
        A, B = core_curve(), causal_curve(event_log_from_field(FIELD), 4)
        self.assertEqual(lk_integer(A, B[::-1]), -lk_integer(A, B))

    def test_segment_gap_positive_for_tube(self):
        A, B = core_curve(), causal_curve(event_log_from_field(FIELD), 3)
        self.assertGreater(segment_gap(A, B), 0.3)

    def test_spliced_closed_polygon_stays_integral(self):
        # Any pair of disjoint closed polygons has an integer Lk.
        A = circle(64)
        B = circle(64, (1, 0, 0), "xz")
        B[:32] = circle(64, (0, 0, 5))[:32]   # spliced -> long chord pierces A
        x = gauss_linking_number(A, B)
        self.assertAlmostEqual(x, round(x), places=6)  # closed curves stay integral


class CausalLogTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tamper(self):
        log = event_log_from_field(FIELD, 20)
        self.assertEqual(verify_log(log), (True, None))
        swapped = list(log)
        swapped[2], swapped[3] = swapped[3], swapped[2]
        self.assertFalse(verify_log(swapped)[0])
        edited = copy.deepcopy(log)
        edited[5]["payload"]["value"] = 1.0
        self.assertEqual(verify_log(edited), (False, 5))
        self.assertFalse(verify_log(log[:7] + log[8:])[0])

    def test_broken_chain_blocks_geometry(self):
        log = event_log_from_field(FIELD, 20)
        log[4], log[5] = log[5], log[4]
        with self.assertRaises(ValueError):
            causal_curve(log, 2)

    def test_append_links_previous_hash(self):
        log = append_event(append_event([], {"v": 1}), {"v": 2})
        self.assertEqual(log[1]["prev"], log[0]["hash"])


class BurnTests(unittest.TestCase):
    def test_burn_passes_and_is_deterministic(self):
        a = burn("ab" * 64, FIELD, m=7, trials=12, seed=3)
        b = burn("ab" * 64, FIELD, m=7, trials=12, seed=3)
        self.assertTrue(a["passed"])
        self.assertEqual(a["admissible"]["preserved"], 12)
        self.assertEqual(a["report_sha512"], b["report_sha512"])

    def test_reversal_flagged_undetectable_when_2k_zero_mod_m(self):
        r = burn("0" * 128, FIELD, m=4, trials=4)   # residue 0 -> k = m = 4
        self.assertFalse(r["adversarial"]["single_reversal"]["expected_detectable"])
        self.assertTrue(r["passed"])

    def test_rejects_trivial_modulus(self):
        with self.assertRaises(ValueError):
            burn("ab" * 64, FIELD, m=1, trials=1)


class ConnectorAndSuperblockTests(unittest.TestCase):
    def test_all_six_couplers_fire(self):
        fired = fire_couplers()
        self.assertEqual(len(fired), 6)
        self.assertTrue(all(c["status"] == "fired" for c in fired))

    def test_stub_adapters_reported_not_fired(self):
        for adapter in probe_adapters():
            self.assertIn(adapter["status"], {"fired", "unimplemented"})

    def test_superblock_chain(self):
        registry = build_registry(iterations=2)
        genesis = build_superblock(registry=registry)
        child = build_superblock(genesis, registry=registry)
        self.assertEqual(genesis["body"]["parent_hash"], GENESIS_PARENT)
        self.assertEqual(verify_chain([genesis, child]), (True, None))
        tampered = copy.deepcopy(genesis)
        tampered["body"]["resonance_field"]["stability"] = 0.5
        self.assertEqual(verify_chain([tampered, child]), (False, 0))
        resealed = build_superblock(registry=registry)
        resealed["body"]["height"] = 0
        self.assertEqual(verify_chain([resealed, child])[0], True)  # deterministic body


if __name__ == "__main__":
    unittest.main()

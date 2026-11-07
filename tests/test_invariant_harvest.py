import copy
import json
import unittest
from unittest.mock import patch

import invariant_harvest as harvest
from burnharness_protocol import create_stabiliser_packet
from coupler_cycle import run_cycle
from src.run_supervised_build import _preload_runtime, run_supervised_build
from zero_data import FileIOViolation, forbid_file_io


class InvariantHarvestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _preload_runtime()

    def setUp(self):
        self.reference = run_cycle()
        self.event = {"event_id": "test-tap-001", "revision": harvest.LOCAL_REVISION,
                      "source": "synthetic_local_fixture"}

    def capture(self, field=None, **options):
        return harvest.capture_tap(self.event, self.reference if field is None else field, **options)

    def test_valid_fixture_executes_complete_local_slice(self):
        result = harvest.run_integration(self.capture(), self.reference)
        self.assertTrue(harvest.verify_evidence(result))
        self.assertEqual(result["body"]["retest"]["status"], "reproduced")
        self.assertTrue(result["body"]["retest"]["packet_preserved"])
        self.assertEqual(result["body"]["retest"]["residue"]["maximum_absolute_error"], 0)
        json.dumps(result, allow_nan=False)

    def test_capture_rejects_malformed_or_raw_boundaries(self):
        for field in ({}, {**self.reference, "stability": True},
                      {**self.reference, "curvature": float("nan")},
                      {**self.reference, "provenance": float("inf")},
                      {**self.reference, "raw_media": b"private"}):
            with self.subTest(field_type=type(field).__name__), self.assertRaises(ValueError):
                self.capture(field)
        for key, value in (("raw_audio", [1]), ("credentials", "not-permitted")):
            with self.assertRaises(ValueError):
                harvest.capture_tap({**self.event, key: value}, self.reference)
        with self.assertRaises(ValueError):
            harvest.capture_tap({**self.event, "event_id": "person@example.com"}, self.reference)

    def test_capture_detaches_mutable_event_and_field(self):
        event = dict(self.event)
        field = dict(self.reference)
        captured = harvest.capture_tap(event, field)
        event["event_id"] = "changed"
        field["stability"] = 0
        self.assertEqual(captured.envelope["event_id"], self.event["event_id"])
        self.assertEqual(captured.field, tuple(self.reference[k] for k in harvest.FIELD_NAMES))
        projected = captured.envelope
        projected["transform"]["scale"] = 0
        self.assertEqual(captured.envelope["transform"]["scale"], 1)

    def test_replay_is_deterministic(self):
        c = self.capture()
        self.assertEqual(harvest.run_integration(c, self.reference),
                         harvest.run_integration(c, self.reference))

    def test_canonicalization_is_key_order_independent(self):
        e = self.capture().envelope
        reordered = dict(reversed(list(e.items())))
        reordered["test_profile"] = dict(reversed(list(e["test_profile"].items())))
        self.assertEqual(harvest.commitment(harvest.ENVELOPE_SCHEMA, e),
                         harvest.commitment(harvest.ENVELOPE_SCHEMA, reordered))
        self.assertEqual(harvest.extract_topology(e), harvest.extract_topology(reordered))

    def test_topology_keeps_declarations_separate_from_observations(self):
        topology = harvest.extract_topology(self.capture().envelope)["body"]
        self.assertEqual(len(topology["edges"]), 7)
        self.assertFalse(topology["observed_upstream"])
        self.assertFalse(topology["hash_is_distance_metric"])
        self.assertEqual({e["basis"] for e in topology["edges"]},
                         {"declared_adapter_contract", "declared_local_stub"})
        result = harvest.run_integration(self.capture(), self.reference)
        self.assertEqual(result["body"]["retest"]["observed_interfaces"],
                         [{"from": "invarianttap", "to": "burnharness",
                           "basis": "local_adapter_invocation"}])

    def test_mutation_invalidates_evidence(self):
        evidence = harvest.run_integration(self.capture(), self.reference)
        for key in ("envelope", "topology", "retest"):
            changed = copy.deepcopy(evidence)
            changed["body"][key]["mutated"] = True
            self.assertFalse(harvest.verify_evidence(changed))

    def test_hash_sensitivity_does_not_claim_collision_resistance_test(self):
        e = self.capture().envelope
        altered = {**e, "event_id": "test-tap-002"}
        self.assertNotEqual(harvest.commitment(harvest.ENVELOPE_SCHEMA, e),
                            harvest.commitment(harvest.ENVELOPE_SCHEMA, altered))
        self.assertNotEqual(harvest.extract_topology(e)["sha512"],
                            harvest.extract_topology(altered)["sha512"])

    def test_near_numeric_neighbor_uses_residue_not_digest_distance(self):
        nearby = {**self.reference, "stability": self.reference["stability"] + 1e-10}
        first = harvest.run_integration(self.capture(), self.reference)
        second = harvest.run_integration(self.capture(nearby), self.reference)
        self.assertNotEqual(first["sha512"], second["sha512"])
        self.assertLess(second["body"]["retest"]["residue"]["maximum_absolute_error"], 1e-9)
        self.assertFalse(second["body"]["topology"]["body"]["hash_is_distance_metric"])
        # A close numerical neighbor is not a cryptographic collision.

    def test_drift_limit_is_strict(self):
        base = {"stability": 0.0, "curvature": 0.0, "provenance": 0.0}
        field = {**base, "stability": .05}
        validation = {"system_ready": False, "environment_ready": True, "stable": True}
        with patch.object(harvest, "run_cycle", return_value=base), patch.object(
            harvest, "validate_system", return_value=validation
        ):
            result = harvest.run_integration(self.capture(field), base)["body"]["retest"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "drift_limit_reached")

    def test_partial_does_not_relax_existing_system_readiness(self):
        changed = {**self.reference, "stability": self.reference["stability"] + .01}
        result = harvest.run_integration(self.capture(changed), self.reference)["body"]["retest"]
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["system_ready"])

    def test_scale_change_control_is_not_mislabeled_invariant(self):
        result = harvest.run_integration(self.capture(scale=.9), self.reference)["body"]["retest"]
        self.assertNotEqual(result["status"], "reproduced")
        self.assertGreater(result["residue"]["maximum_absolute_error"], 0)
        with self.assertRaises(ValueError):
            self.capture(scale=float("inf"))
        with self.assertRaises(ValueError):
            self.capture(drift_limit=.051)

    def test_missing_reference_remains_indeterminate(self):
        for reference, options in ((None, {}), (self.reference, {"reference_id": "unknown/1"})):
            result = harvest.run_integration(self.capture(**options), reference)["body"]["retest"]
            self.assertEqual(result["status"], "indeterminate")
            self.assertIsNone(result["residue"])

    def test_missing_upstream_never_executes_a_substitute(self):
        with patch.object(harvest, "run_cycle", side_effect=AssertionError("must not execute")):
            result = harvest.run_integration(self.capture(scope="upstream"), self.reference)
        self.assertEqual(result["body"]["retest"]["reason"], "upstream_unbound")
        self.assertEqual(result["body"]["retest"]["status"], "indeterminate")
        self.assertEqual(result["body"]["retest"]["observed_interfaces"], [])

    def test_synthetic_success_never_claims_upstream_or_production_pass(self):
        evidence = harvest.local_fixture()
        self.assertEqual(evidence["body"]["retest"]["status"], "reproduced")
        for key in ("upstream_verified", "production_launch_authorized", "issuer_authenticated",
                    "execution_proven_by_hash", "persistent_artifacts"):
            self.assertFalse(evidence["body"][key])
        evidence["body"]["upstream_verified"] = True
        evidence["sha512"] = harvest.commitment(harvest.EVIDENCE_SCHEMA, evidence["body"])
        self.assertFalse(harvest.verify_evidence(evidence))

    def test_zero_data_execution_and_swallowed_file_attempt_fail_closed(self):
        with forbid_file_io():
            self.assertTrue(harvest.verify_evidence(harvest.local_fixture()))
        def swallow(**_kwargs):
            try:
                open("forbidden-raw-data", "wb")
            except FileIOViolation:
                pass
            return self.reference
        with patch.object(harvest, "run_cycle", side_effect=swallow), self.assertRaises(FileIOViolation):
            harvest.run_integration(self.capture(), self.reference)

    def test_failures_are_redacted_and_packet_is_not_replaced(self):
        packet = create_stabiliser_packet()
        with patch.object(harvest, "run_cycle", side_effect=RuntimeError("secret-bearing-message")):
            result = harvest.run_integration(self.capture(), self.reference, packet)
        self.assertEqual(result["body"]["retest"]["status"], "failed")
        self.assertNotIn("secret-bearing-message", json.dumps(result))
        with self.assertRaises(TypeError):
            harvest.run_integration(self.capture(), self.reference, dict(packet))

    def test_invalid_observed_field_fails_closed(self):
        with patch.object(harvest, "run_cycle", return_value={"stability": True}):
            result = harvest.run_integration(self.capture(), self.reference)
        self.assertEqual(result["body"]["retest"]["status"], "failed")
        self.assertIsNone(result["body"]["retest"]["residue"])

    def test_profile_schema_and_privacy_mutation_rejected(self):
        e = self.capture().envelope
        for patch_value in ({"schema": "unknown/2"}, {"revision": "pretend-upstream-pin"},
                            {"privacy": {"raw_payloads": "retain"}}):
            with self.assertRaises(ValueError):
                harvest.validate_envelope({**e, **patch_value})

    def test_resealed_inconsistent_reproduction_is_not_accepted(self):
        evidence = harvest.local_fixture()
        evidence["body"]["retest"]["system_ready"] = False
        evidence["body"]["retest_commitment"] = harvest.commitment(
            harvest.RETEST_SCHEMA, evidence["body"]["retest"])
        evidence["sha512"] = harvest.commitment(harvest.EVIDENCE_SCHEMA, evidence["body"])
        self.assertFalse(harvest.verify_evidence(evidence))
        with patch("src.run_supervised_build.local_fixture", return_value=evidence):
            with self.assertRaises(RuntimeError):
                run_supervised_build()

    def test_incomplete_validation_does_not_produce_partial_or_reproduced(self):
        changed = {**self.reference, "stability": self.reference["stability"] + .01}
        bad_report = {"system_ready": True, "environment_ready": True, "stable": True,
                      "consistent": True, "boundary_valid": False, "integrity_verified": False}
        with patch.object(harvest, "validate_system", return_value=bad_report):
            result = harvest.run_integration(self.capture(changed), self.reference)
        self.assertEqual(result["body"]["retest"]["status"], "failed")
        self.assertFalse(result["body"]["retest"]["system_ready"])

    def test_resealed_raw_receipt_fields_are_rejected(self):
        evidence = harvest.local_fixture()
        evidence["body"]["raw_media"] = "not permitted"
        evidence["sha512"] = harvest.commitment(harvest.EVIDENCE_SCHEMA, evidence["body"])
        self.assertFalse(harvest.verify_evidence(evidence))

    def test_supervised_output_contains_and_checks_the_evidence(self):
        result = run_supervised_build()
        self.assertTrue(result["outputs"]["verification"]["invariant_tap_local_retest"])
        self.assertTrue(harvest.verify_evidence(result["outputs"]["invariant_tap"]))
        self.assertFalse(result["persistent_artifacts"])
        self.assertEqual([r["step"] for r in result["steps"]],
                         ["benchmark", "superblock", "causal_burn", "verification"])


if __name__ == "__main__":
    unittest.main()

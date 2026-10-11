import unittest
from dataclasses import replace
from unittest.mock import Mock

from burnharness_protocol import create_stabiliser_packet
from origin_integration import (
    Binding, CloneEvidence, DEFAULT_FACES, GATES, Gate, LEGS, Origin,
    attempt_leg, completion_report, cube_geometry, project_sphere,
    resolve_origin,
)
from repo_manifest import get_manifest
from zero_data import FileIOViolation, forbid_file_io


class FixtureAdapter:
    """Synthetic contract fixture, not an upstream implementation."""

    def invoke(self, packet, projection):
        return {"stabiliser_packet": packet, "projection": projection}


class OriginIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.origin = Origin("declared:test-fixture", "fixture.invoke", "test fixture")
        self.declarations = {"scandoc": (self.origin,)}
        self.binding = Binding(
            self.origin,
            Mock(return_value=CloneEvidence(self.origin.repository, "a" * 40, True)),
            Mock(return_value=True), FixtureAdapter(),
            Mock(return_value=True), Mock(return_value=True),
        )

    def attempt(self, **kwargs):
        return attempt_leg(
            "scandoc", self.declarations,
            kwargs.pop("binding", self.binding),
            allow_clone_retention=True, **kwargs,
        )

    def test_repository_origins_are_blocked_not_stubs(self):
        declarations = get_manifest()["origin_declarations"]
        evidence = {leg: attempt_leg(leg, declarations) for leg in LEGS}
        self.assertEqual(set(declarations), set(LEGS))
        for gates in evidence.values():
            self.assertEqual(gates["origin_resolved"].status, "blocked")
            self.assertTrue(all(gate.status == "blocked" for gate in gates.values()))
        self.assertFalse(completion_report(evidence)["development_gates_complete"])

    def test_missing_ambiguous_invalid_and_unknown_origins(self):
        for leg, declarations in (
            ("scandoc", {}),
            ("scandoc", {"scandoc": (self.origin, self.origin)}),
            ("scandoc", {"scandoc": (Origin("", "", ""),)}),
            ("scandoc", {"scandoc": (replace(self.origin, commit="main"),)}),
            ("not-a-leg", self.declarations),
        ):
            with self.subTest(leg=leg, declarations=declarations):
                origin, gate = resolve_origin(leg, declarations)
                self.assertIsNone(origin)
                self.assertEqual(gate.status, "blocked")

    def test_retention_conflict_prevents_clone(self):
        gates = attempt_leg("scandoc", self.declarations, self.binding)
        self.binding.clone.assert_not_called()
        self.assertIn("zero-data conflict", gates["pinned_clone_verified"].reason)

    def test_missing_or_mismatched_binding(self):
        for binding in (None, replace(self.binding, origin=replace(self.origin, interface="other"))):
            self.assertEqual(
                self.attempt(binding=binding)["pinned_clone_verified"].status, "blocked"
            )
        self.binding.clone.assert_not_called()

    def test_clone_exception_and_wrong_pin_fail(self):
        self.binding.clone.side_effect = RuntimeError("private trace must not escape")
        gates = self.attempt()
        self.assertEqual(gates["pinned_clone_verified"], Gate("failed", "RuntimeError"))
        self.binding.clone.side_effect = None
        for clone in (
            CloneEvidence("other", "a" * 40, True),
            CloneEvidence(self.origin.repository, "main", True),
            CloneEvidence(self.origin.repository, "a" * 40, False),
        ):
            self.binding.clone.return_value = clone
            self.assertEqual(self.attempt()["pinned_clone_verified"].status, "failed")
        self.binding.dependencies.assert_not_called()

    def test_declared_pin_must_match_resolved_clone(self):
        self.origin = replace(self.origin, commit="b" * 40)
        self.declarations = {"scandoc": (self.origin,)}
        self.binding = replace(self.binding, origin=self.origin)
        self.assertEqual(self.attempt()["pinned_clone_verified"].status, "failed")

    def test_unavailable_dependencies_prevent_invocation(self):
        adapter = Mock()
        self.binding = replace(self.binding, adapter=adapter)
        self.binding.dependencies.return_value = False
        self.assertEqual(self.attempt()["dependencies_available"].status, "blocked")
        adapter.invoke.assert_not_called()
        self.binding.dependencies.side_effect = ImportError("private dependency")
        self.assertEqual(self.attempt()["dependencies_available"].status, "failed")
        adapter.invoke.assert_not_called()

    def test_unbound_and_failed_adapter(self):
        self.assertEqual(
            self.attempt(binding=replace(self.binding, adapter=None))["adapter_invoked"].status,
            "blocked",
        )
        adapter = Mock()
        adapter.invoke.side_effect = RuntimeError("private invocation trace")
        gates = self.attempt(binding=replace(self.binding, adapter=adapter))
        self.assertEqual(gates["adapter_invoked"], Gate("failed", "RuntimeError"))
        self.assertNotEqual(gates["declared_tests_passed"].status, "passed")

    def test_packet_identity_and_content_required(self):
        for output in ({}, {"stabiliser_packet": create_stabiliser_packet()}):
            adapter = Mock()
            adapter.invoke.return_value = output
            gates = self.attempt(binding=replace(self.binding, adapter=adapter))
            self.assertEqual(gates["packet_invariants_preserved"].status, "failed")
        adapter = Mock()

        def mutate(packet, projection):
            dict.__setitem__(packet, "extra", True)
            return {"stabiliser_packet": packet}

        adapter.invoke.side_effect = mutate
        gates = self.attempt(binding=replace(self.binding, adapter=adapter))
        self.assertEqual(gates["packet_invariants_preserved"].status, "failed")

    def test_guard_rejects_io_even_if_adapter_swallows_it(self):
        adapter = Mock()

        def forbidden(packet, projection):
            try:
                open("/tmp/origin-integration-must-not-exist", "w")
            except FileIOViolation:
                pass
            return {"stabiliser_packet": packet}

        adapter.invoke.side_effect = forbidden
        gates = self.attempt(binding=replace(self.binding, adapter=adapter))
        self.assertEqual(gates["adapter_invoked"].status, "failed")
        self.assertEqual(gates["containment_requirements_tested"].status, "failed")

    def test_test_callback_cannot_falsely_attest_packet_preservation(self):
        def mutate(output):
            dict.__setitem__(output["stabiliser_packet"], "extra", True)
            return True

        gates = self.attempt(binding=replace(self.binding, declared_tests=mutate))
        self.assertEqual(gates["packet_invariants_preserved"].status, "failed")

    def test_synthetic_binding_executes_contract_not_upstream_evidence(self):
        self.assertTrue(all(gate.status == "passed" for gate in self.attempt().values()))
        self.binding.declared_tests.assert_called_once()
        self.binding.containment_tests.assert_called_once()
        self.binding.declared_tests.return_value = False
        self.binding.containment_tests.return_value = False
        gates = self.attempt()
        self.assertEqual(gates["declared_tests_passed"].status, "blocked")
        self.assertEqual(gates["containment_requirements_tested"].status, "blocked")

    def test_closed_cube_has_shared_edges_vertices_and_symmetric_adjacency(self):
        geometry = cube_geometry()
        self.assertTrue(geometry["closed"])
        self.assertEqual((geometry["vertices"], geometry["edges"], geometry["faces"]), (8, 12, 6))
        for leg, neighbors in geometry["adjacency"].items():
            self.assertEqual(len(neighbors), 4)
            for other in neighbors:
                self.assertIn(leg, geometry["adjacency"][other])
        for a, b in zip(LEGS, LEGS[1:] + LEGS[:1]):
            self.assertIn(b, geometry["adjacency"][a])

    def test_incomplete_duplicate_and_unknown_face_mappings(self):
        for mapping in (
            {}, {leg: "+x" for leg in LEGS},
            {**DEFAULT_FACES, "extra": "+x"},
            {**DEFAULT_FACES, "scandoc": "unknown"},
        ):
            self.assertFalse(cube_geometry(mapping)["closed"])
        remapped = dict(zip(LEGS, reversed(tuple(DEFAULT_FACES.values()))))
        self.assertTrue(cube_geometry(remapped)["closed"])

    def test_projection_is_model_coordinates_only(self):
        self.assertEqual(project_sphere((2, 1, -2)), (1, 0.5, -1))
        self.assertEqual(project_sphere((4, 2, -4)), (1, 0.5, -1))
        for direction in ((0, 0, 0), (1, 2), (True, 0, 0), (float("nan"), 1, 1)):
            with self.assertRaises(ValueError):
                project_sphere(direction)

    def test_false_completion_rejected_for_every_gate_and_missing_leg(self):
        evidence = {leg: {name: Gate("passed", "synthetic fixture") for name in GATES}
                    for leg in LEGS}
        self.assertTrue(completion_report(evidence)["development_gates_complete"])
        self.assertFalse(completion_report(evidence)["production_launch_authorized"])
        for gate in GATES:
            altered = {**evidence, "scandoc": {**evidence["scandoc"], gate: Gate()}}
            self.assertFalse(completion_report(altered)["development_gates_complete"])
        self.assertFalse(completion_report({})["development_gates_complete"])
        self.assertFalse(completion_report(evidence, {})["development_gates_complete"])
        altered = {**evidence, "scandoc": {"complete": True}}
        self.assertFalse(completion_report(altered)["development_gates_complete"])

    def test_geometry_resolution_and_reporting_are_in_memory(self):
        with forbid_file_io():
            declarations = get_manifest()["origin_declarations"]
            evidence = {leg: attempt_leg(leg, declarations) for leg in LEGS}
            report = completion_report(evidence)
        self.assertFalse(report["development_gates_complete"])


if __name__ == "__main__":
    unittest.main()

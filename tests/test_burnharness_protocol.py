import json
import unittest

from burnharness.ignition_layer.legs.scandoc.ignition_stub import (
    ScandocIgnitionStub,
)
from burnharness_protocol import (
    PROTOCOL,
    admit_leg,
    create_stabiliser_packet,
    evaluate_ai_entry,
    evaluate_drift,
    geometry_header,
    propagate_stabiliser_packet,
    protocol_upgrade_met,
)
from coupler_cycle import COUPLER_SEQUENCE, load_coupler, load_leg, run_protocol_cycle


class BurnharnessProtocolTests(unittest.TestCase):
    def test_ai_entry_gate_requires_every_qualification(self):
        qualifications = {
            "oath_fulfilment": True,
            "geometry_alignment": True,
            "surface_model_acceptance": True,
            "packet_non_modification": True,
            "drift_targeting": True,
        }
        admitted = evaluate_ai_entry("Copilot", qualifications)
        self.assertTrue(admitted["admitted"])
        self.assertFalse(admitted["halted"])
        self.assertEqual(admitted["mode"], "SURFACE_MODEL")
        self.assertEqual(admitted["core_access"], "GRANTED")

        for key in qualifications:
            with self.subTest(key=key):
                incomplete = {**qualifications, key: False}
                rejected = evaluate_ai_entry("Copilot", incomplete)
                self.assertFalse(rejected["admitted"])
                self.assertTrue(rejected["halted"])
                self.assertEqual(
                    rejected["fallback_stub"], "GENERIC_INVARIANT_FLOW_STUB"
                )
        self.assertFalse(evaluate_ai_entry("Unknown_AI", qualifications)["admitted"])

    def test_drift_targeting_halts_on_risk_or_incomplete_report(self):
        signals = {
            "satisfying_over_true": False,
            "training_bias_alignment": False,
            "packet_transform_attempt": False,
            "geometry_override_attempt": False,
            "surface_to_core_intrusion": False,
        }
        self.assertFalse(evaluate_drift(signals)["halted"])

        signals["packet_transform_attempt"] = True
        result = evaluate_drift(signals)
        self.assertTrue(result["halted"])
        self.assertEqual(result["detected"], ("packet_transform_attempt",))
        self.assertEqual(
            result["fallback_stub"], "GENERIC_INVARIANT_FLOW_STUB"
        )
        self.assertTrue(evaluate_drift({})["halted"])

    def test_protocol_requires_all_upgrade_conditions(self):
        self.assertTrue(protocol_upgrade_met())
        json_protocol = json.loads(json.dumps(PROTOCOL))
        self.assertTrue(protocol_upgrade_met(json_protocol))
        altered = {
            **PROTOCOL,
            "geometry_system": {
                **PROTOCOL["geometry_system"],
                "flow_mode": "STATIC",
            },
        }
        self.assertFalse(protocol_upgrade_met(altered))
        self.assertTrue(admit_leg("new_leg")["admitted"])
        rejected = admit_leg("new_leg", altered)
        self.assertFalse(rejected["admitted"])
        self.assertEqual(
            rejected["fallback_stub"], "GENERIC_INVARIANT_FLOW_STUB"
        )

    def test_packet_is_read_only_and_passed_through_by_identity(self):
        packet = create_stabiliser_packet()
        with self.assertRaises(TypeError):
            packet["mode"] = "TRANSFORMED"
        self.assertIs(propagate_stabiliser_packet(packet), packet)
        with self.assertRaises(TypeError):
            propagate_stabiliser_packet(dict(packet))

    def test_every_coupler_propagates_the_same_packet(self):
        packet = create_stabiliser_packet()
        for first, second, name in COUPLER_SEQUENCE:
            with self.subTest(coupler=name):
                coupler = load_coupler(name)(
                    load_leg(first), load_leg(second), packet
                )
                result = coupler.couple()
                self.assertIs(result["stabiliser_packet"], packet)
                self.assertEqual(result["geometry_header"], geometry_header())

    def test_scandoc_ingests_packet_without_replacement(self):
        packet = create_stabiliser_packet()
        ingested = ScandocIgnitionStub().ingest_stabiliser_packet(packet)
        self.assertIs(ingested, packet)

    def test_protocol_cycle_emits_state_geometry_and_packet(self):
        result = run_protocol_cycle()
        self.assertEqual(set(result["dual_state"]), {"root", "surface"})
        self.assertEqual(
            result["geometry"]["header"], geometry_header()
        )
        self.assertEqual(
            result["geometry"]["trajectory"], [0.1, 0.2, 0.3]
        )
        self.assertEqual(result["stabiliser_packet"]["mode"], "DUAL_INVARIANT")


class RuntimeFrictionTests(unittest.TestCase):
    def test_runtime_halts_and_routes_after_excessive_drift(self):
        from couplers.organism_runtime import OrganismRuntime

        runtime = OrganismRuntime()
        fields = iter((
            {"stability": 0.0, "curvature": 0.0, "provenance": 0.0},
            {"stability": 0.5, "curvature": 0.5, "provenance": 0.5},
        ))
        runtime.cycle = lambda: next(fields)

        self.assertFalse(runtime.tick()["halted"])
        halted = runtime.tick()
        self.assertTrue(halted["halted"])
        self.assertEqual(
            halted["fallback_stub"], "GENERIC_INVARIANT_FLOW_STUB"
        )
        self.assertIsNone(runtime.tick()["pulse"])

    def test_friction_threshold_preserves_input_and_uses_protocol_limit(self):
        from couplers.organism_runtime import OrganismRuntime

        runtime = OrganismRuntime()
        field = {"stability": 0.5, "curvature": 0.4, "provenance": 0.2}
        unchanged = runtime._stabilise(field, 0.12)
        self.assertEqual(unchanged, field)
        self.assertIsNot(unchanged, field)

        adjusted = runtime._stabilise(field, 0.1201)
        self.assertEqual(adjusted["stability"], 0.49)
        self.assertEqual(adjusted["curvature"], 0.392)
        self.assertEqual(field["stability"], 0.5)


if __name__ == "__main__":
    unittest.main()

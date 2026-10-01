import unittest

from burnharness.ignition_layer.legs.scandoc.ignition_stub import (
    ScandocIgnitionStub,
)
from burnharness_protocol import (
    PROTOCOL,
    admit_leg,
    create_stabiliser_packet,
    geometry_header,
    propagate_stabiliser_packet,
    protocol_upgrade_met,
)
from coupler_cycle import COUPLER_SEQUENCE, load_coupler, load_leg, run_protocol_cycle


class BurnharnessProtocolTests(unittest.TestCase):
    def test_protocol_requires_all_upgrade_conditions(self):
        self.assertTrue(protocol_upgrade_met())
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
                self.assertIs(coupler.couple()["stabiliser_packet"], packet)

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


if __name__ == "__main__":
    unittest.main()

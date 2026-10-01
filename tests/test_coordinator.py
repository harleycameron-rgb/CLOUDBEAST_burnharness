import hashlib
import json
import threading
import unittest

from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import (
    SentinelDotIgnitionStub,
)
from companion import Companion
from coordinator import ParabolaProjection, SentinelDotCoordinator
from couplers.orrery_sentinel_dot.coupler import OrrerySentinelDotCoupler


class SentinelDotCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = SentinelDotCoordinator()
        self.sentinels = {
            instance_id: SentinelDotIgnitionStub()
            for instance_id in self.coordinator.instance_ids
        }
        threads = [
            threading.Thread(
                target=self.sentinels[instance_id].bind,
                args=(self.coordinator, instance_id),
            )
            for instance_id in self.coordinator.instance_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def test_genesis_gate_distributes_same_anchor_before_divergence(self):
        first, second = (
            self.sentinels[instance_id]
            for instance_id in self.coordinator.instance_ids
        )
        self.assertTrue(self.coordinator.state["genesis_anchor_locked"])
        self.assertEqual(first.genesis_anchor_id, second.genesis_anchor_id)
        self.assertEqual(
            first.state["invariant_projection_anchor"],
            second.state["initial_symbol_state"],
        )
        genesis_id = first.genesis_anchor_id
        self.assertEqual(len(genesis_id), 128)

        first.publish_invariant_projection(
            ParabolaProjection(a=1, b=0, c=0)
        )
        second.publish_accumulated_symbol({"x": 3, "y": 9})
        self.assertNotEqual(
            first.state["invariant_projection_anchor"],
            second.state["accumulated_symbol"],
        )
        self.assertEqual(self.coordinator.release.genesis_block_id, genesis_id)
        self.assertEqual(
            first.fire_record["block_id"], second.fire_record["block_id"]
        )

    def test_valid_projection_releases_gate_and_fires_both_instances(self):
        projection = ParabolaProjection(a=1, b=0, c=0, tolerance=0.01)
        self.assertIsNone(
            self.sentinels[self.coordinator.invariant_source_id]
            .publish_invariant_projection(projection)
        )
        self.assertFalse(self.coordinator.state["gate_released"])
        self.assertTrue(all(
            sentinel.fire_record is None for sentinel in self.sentinels.values()
        ))

        release = self.sentinels[self.coordinator.symbol_source_id]\
            .publish_accumulated_symbol({"x": 2, "y": 4.005})
        records = [
            self.sentinels[instance_id].fire_record
            for instance_id in self.coordinator.instance_ids
        ]
        self.assertTrue(self.coordinator.state["validation_passed"])
        self.assertTrue(self.coordinator.state["gate_released"])
        self.assertTrue(self.coordinator.state["superposition_integrity"])
        self.assertTrue(self.coordinator.state["no_bung"])
        self.assertTrue(self.coordinator.state["continuity_flow"])
        self.assertTrue(all(record["fired"] for record in records))
        self.assertTrue(all(record["gate_released"] for record in records))
        self.assertEqual(records[0]["block_id"], records[1]["block_id"])
        self.assertEqual(records[0]["block_id"], release.block_id)
        self.assertEqual(len(release.block_id), 128)
        self.assertEqual(
            release.genesis_block_id,
            self.coordinator.state["genesis_block_id"],
        )

    def test_symbol_need_not_equal_projection_representation(self):
        projection = {"members": [{"state": "invariant-member"}]}
        self.coordinator.publish_invariant_projection(projection)
        release = self.coordinator.publish_accumulated_symbol(
            {"state": "invariant-member"}
        )
        self.assertIsNotNone(release)
        self.assertTrue(self.coordinator.state["validation_passed"])

    def test_hash_projection_validates_accumulated_symbol(self):
        symbol = {"accumulated": ["s", "t", "a", "t", "e"]}
        digest = hashlib.sha512(
            json.dumps(symbol, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.coordinator.publish_invariant_projection(
            {"symbol_hashes": [digest]}
        )
        self.assertIsNotNone(
            self.coordinator.publish_accumulated_symbol(symbol)
        )

    def test_outside_projection_does_not_release_or_fire(self):
        self.coordinator.publish_invariant_projection(
            ParabolaProjection(a=1, b=0, c=0, tolerance=1e-9)
        )
        self.assertIsNone(
            self.coordinator.publish_accumulated_symbol({"x": 2, "y": 5})
        )
        self.assertFalse(self.coordinator.state["gate_released"])
        self.assertFalse(self.coordinator.state["validation_passed"])
        self.assertTrue(all(
            sentinel.fire_record is None for sentinel in self.sentinels.values()
        ))

    def test_changed_accumulated_symbol_revokes_prior_release(self):
        self.coordinator.publish_invariant_projection({"members": ["valid"]})
        first_release = self.coordinator.publish_accumulated_symbol("valid")
        self.assertTrue(all(
            sentinel.fire_record is not None for sentinel in self.sentinels.values()
        ))

        self.assertIsNone(
            self.coordinator.publish_accumulated_symbol("outside")
        )
        self.assertFalse(self.coordinator.state["gate_released"])
        self.assertFalse(self.coordinator.accepts_release(
            first_release, self.coordinator.instance_ids[0]
        ))

    def test_coupler_publishes_asymmetric_state_without_equality_checks(self):
        class Leg:
            def __init__(self, state):
                self.state = state

            def ignite(self):
                return self.state

        projection = ParabolaProjection(a=1, b=0, c=0)
        result = OrrerySentinelDotCoupler(
            Leg({"invariant_projection": projection}),
            Leg({"accumulated_symbol": {"x": 3, "y": 9}}),
            coordinator=self.coordinator,
        ).couple()
        self.assertTrue(result["sentinel_validation"]["passed"])
        self.assertIsNotNone(result["sentinel_release"])
        self.assertTrue(all(
            sentinel.fire_record is not None for sentinel in self.sentinels.values()
        ))

    def test_companion_integrity_requires_validation_gate_release(self):
        companion = Companion()
        self.assertTrue(companion.required_invariants["genesis_anchor_locked"])
        valid_system_state = {
            "paths_valid": True,
            "imports_valid": True,
            "load_order_locked": True,
        }
        self.assertFalse(companion.superposition_integrity(valid_system_state))
        self.assertFalse(
            companion.superposition_integrity(
                valid_system_state, self.coordinator.state
            )
        )
        self.coordinator.publish_invariant_projection({"members": [1]})
        self.coordinator.publish_accumulated_symbol(1)
        self.assertTrue(
            companion.superposition_integrity(
                valid_system_state, self.coordinator.state
            )
        )

    def test_runtime_publication_is_rejected_before_genesis_distribution(self):
        coordinator = SentinelDotCoordinator()
        with self.assertRaises(RuntimeError):
            coordinator.publish_invariant_projection({"members": ["seed"]})
        with self.assertRaises(RuntimeError):
            coordinator.publish_accumulated_symbol("seed")


if __name__ == "__main__":
    unittest.main()

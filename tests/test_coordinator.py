import hashlib
import json
import unittest

from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import (
    SentinelDotIgnitionStub,
)
from companion import BIG_PROMPT_INVARIANTS, Companion
from coordinator import (
    GenesisBootstrapError,
    ParabolaProjection,
    SentinelDotCoordinator,
    benchmark_genesis_bootstrap,
    bootstrap_genesis,
)
from couplers.orrery_sentinel_dot.coupler import OrrerySentinelDotCoupler


class SentinelDotCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = SentinelDotCoordinator()
        self.sentinels = {
            instance_id: SentinelDotIgnitionStub()
            for instance_id in self.coordinator.instance_ids
        }
        for instance_id, sentinel in self.sentinels.items():
            sentinel.bind(self.coordinator, instance_id)
        self.genesis = bootstrap_genesis(self.coordinator)

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

    def test_published_symbol_is_defensively_copied(self):
        symbol = {"values": [1]}
        self.assertIsNone(self.coordinator.publish_accumulated_symbol(symbol))
        symbol["values"].append(2)

        self.coordinator.publish_invariant_projection(
            {"members": [{"values": [1]}]}
        )
        self.assertTrue(self.coordinator.state["gate_released"])

    def test_equivalent_publications_preserve_release_and_revisions(self):
        projection = {"members": [{"state": "valid"}]}
        symbol = {"state": "valid"}
        self.coordinator.publish_invariant_projection(projection)
        release = self.coordinator.publish_accumulated_symbol(symbol)
        revisions = (
            self.coordinator.state["projection_revision"],
            self.coordinator.state["symbol_revision"],
        )

        self.assertIs(
            self.coordinator.publish_invariant_projection(projection), release
        )
        self.assertIs(
            self.coordinator.publish_accumulated_symbol(symbol), release
        )
        self.assertEqual(
            (
                self.coordinator.state["projection_revision"],
                self.coordinator.state["symbol_revision"],
            ),
            revisions,
        )

    def test_changed_projection_revokes_release_until_symbol_is_revalidated(self):
        self.coordinator.publish_invariant_projection({"members": ["valid"]})
        first_release = self.coordinator.publish_accumulated_symbol("valid")
        self.assertIsNotNone(first_release)

        self.assertIsNone(
            self.coordinator.publish_invariant_projection({"members": ["new"]})
        )
        self.assertFalse(self.coordinator.state["gate_released"])
        self.assertFalse(self.coordinator.accepts_release(
            first_release, self.coordinator.instance_ids[0]
        ))

        second_release = self.coordinator.publish_accumulated_symbol("new")
        self.assertIsNotNone(second_release)
        self.assertNotEqual(second_release.block_id, first_release.block_id)
        self.assertGreater(
            second_release.projection_revision, first_release.projection_revision
        )

    def test_non_finite_symbol_is_rejected_without_revoking_release(self):
        self.coordinator.publish_invariant_projection({"members": ["valid"]})
        release = self.coordinator.publish_accumulated_symbol("valid")

        with self.assertRaises(ValueError):
            self.coordinator.publish_accumulated_symbol({"value": float("nan")})

        self.assertIs(self.coordinator.release, release)
        self.assertTrue(self.coordinator.accepts_release(
            release, self.coordinator.instance_ids[0]
        ))

    def test_release_is_bound_to_identity_instance_and_genesis(self):
        self.coordinator.publish_invariant_projection({"members": ["valid"]})
        release = self.coordinator.publish_accumulated_symbol("valid")
        other_coordinator = SentinelDotCoordinator()

        self.assertFalse(self.coordinator.accepts_release(
            type(release)(**release.__dict__), self.coordinator.instance_ids[0]
        ))
        self.assertFalse(self.coordinator.accepts_release(
            release, "unregistered-sentinel"
        ))
        self.assertFalse(other_coordinator.accepts_release(
            release, other_coordinator.instance_ids[0]
        ))

    def test_invalid_projection_fails_closed_without_exception(self):
        for projection in (
            {"members": "not-a-sequence"},
            {"symbol_hashes": ["not-a-sha512-digest"]},
            {"a": float("nan"), "b": 0, "c": 0},
        ):
            with self.subTest(projection=projection):
                self.assertIsNone(
                    self.coordinator.publish_invariant_projection(projection)
                )
                self.assertIsNone(
                    self.coordinator.publish_accumulated_symbol("anything")
                )
                self.assertFalse(self.coordinator.state["gate_released"])

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


class GenesisBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = SentinelDotCoordinator()
        self.sentinels = {
            instance_id: SentinelDotIgnitionStub()
            for instance_id in self.coordinator.instance_ids
        }
        for instance_id, sentinel in self.sentinels.items():
            sentinel.bind(self.coordinator, instance_id)

    def test_both_instances_start_from_same_genesis_block_before_diverging(self):
        self.assertFalse(self.coordinator.state["genesis_anchor_locked"])
        self.assertTrue(all(
            sentinel.genesis_record is None for sentinel in self.sentinels.values()
        ))
        genesis = bootstrap_genesis(self.coordinator)

        sentinel_a = self.sentinels[self.coordinator.invariant_source_id]
        sentinel_b = self.sentinels[self.coordinator.symbol_source_id]
        self.assertEqual(len(genesis.block_id), 128)
        int(genesis.block_id, 16)
        self.assertEqual(sentinel_a.genesis_block_id, genesis.block_id)
        self.assertEqual(sentinel_b.genesis_block_id, genesis.block_id)
        self.assertEqual(sentinel_a.genesis_block_id, sentinel_b.genesis_block_id)
        self.assertEqual(sentinel_a.genesis_record["parabola_anchor"], genesis.block_id)
        self.assertEqual(
            sentinel_b.genesis_record["accumulated_symbol"], genesis.block_id
        )
        with self.assertRaises(TypeError):
            sentinel_a.genesis_record["parabola_anchor"] = "mutated"
        state = self.coordinator.state
        self.assertTrue(state["genesis_anchor_locked"])
        self.assertEqual(state["genesis_block_id"], genesis.block_id)
        self.assertTrue(state["no_bung"])
        self.assertTrue(state["continuity_flow"])

        sentinel_a.publish_invariant_projection(ParabolaProjection(a=1, b=0, c=0))
        release = sentinel_b.publish_accumulated_symbol({"x": 2, "y": 4})
        self.assertEqual(release.genesis_block_id, genesis.block_id)
        self.assertNotEqual(release.block_id, genesis.block_id)
        for sentinel in self.sentinels.values():
            self.assertEqual(sentinel.fire_record["genesis_block_id"], genesis.block_id)
            self.assertEqual(sentinel.genesis_block_id, genesis.block_id)

    def test_runtime_validation_is_blocked_until_genesis_is_locked(self):
        with self.assertRaises(RuntimeError):
            self.coordinator.publish_invariant_projection({"members": [1]})
        with self.assertRaises(RuntimeError):
            self.coordinator.publish_accumulated_symbol(1)
        bootstrap_genesis(self.coordinator)
        self.coordinator.publish_invariant_projection({"members": [1]})
        self.assertIsNotNone(self.coordinator.publish_accumulated_symbol(1))

    def test_genesis_bootstrap_is_one_time(self):
        genesis = bootstrap_genesis(self.coordinator)
        with self.assertRaises(GenesisBootstrapError):
            self.coordinator.enter_genesis(self.coordinator.instance_ids[0])
        self.assertIs(self.coordinator.genesis, genesis)

    def test_single_ready_instance_times_out_instead_of_deadlocking(self):
        with self.assertRaises(GenesisBootstrapError):
            self.sentinels[self.coordinator.invariant_source_id].enter_genesis(
                timeout=0.05
            )
        self.assertFalse(self.coordinator.genesis_anchor_locked)
        self.assertIsNone(self.coordinator.genesis)

    def test_late_bound_instance_receives_locked_genesis(self):
        genesis = bootstrap_genesis(self.coordinator)
        late = SentinelDotIgnitionStub()
        late.bind(self.coordinator, self.coordinator.symbol_source_id)
        self.assertEqual(late.genesis_block_id, genesis.block_id)

    def test_big_prompt_invariants_require_genesis_anchor(self):
        self.assertEqual(
            dict(BIG_PROMPT_INVARIANTS),
            {"genesis_anchor_locked": True, "no_bung": True, "continuity_flow": True},
        )
        valid_system_state = {
            "paths_valid": True,
            "imports_valid": True,
            "load_order_locked": True,
        }
        bootstrap_genesis(self.coordinator)
        self.coordinator.publish_invariant_projection({"members": [1]})
        self.coordinator.publish_accumulated_symbol(1)
        companion = Companion()
        self.assertTrue(companion.superposition_integrity(
            valid_system_state, self.coordinator.state
        ))
        unanchored = dict(self.coordinator.state, genesis_anchor_locked=False)
        self.assertFalse(companion.superposition_integrity(
            valid_system_state, unanchored
        ))

    def test_genesis_bootstrap_overhead_does_not_stall_startup(self):
        report = benchmark_genesis_bootstrap(iterations=50)
        self.assertEqual(report["iterations"], 50)
        self.assertLess(report["median_ms"], 50.0)
        self.assertLess(report["max_ms"], 1000.0)


if __name__ == "__main__":
    unittest.main()

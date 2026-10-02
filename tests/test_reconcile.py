import hashlib
import json
import unittest
from dataclasses import replace

from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import (
    SentinelDotIgnitionStub,
)
from coordinator import SentinelDotCoordinator, bootstrap_genesis
from coupler_cycle import run_cycle
from reconcile import Divergence, canonical_projection, reconcile
from verify_reconciled import verify_reconciled


def make_head(log, salt=None):
    payload = json.dumps(
        log, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.log_a = {
            "session_id": "session-a",
            "timestamp": "2026-01-01T00:00:00Z",
            "outcomes": [
                {"key": "alpha", "value": {"passed": True}, "transport": "a"},
                {"key": "beta", "value": 7},
            ],
        }
        self.log_b = {
            "session_id": "session-b",
            "timestamp": "2026-05-01T12:00:00Z",
            "outcomes": [
                {"key": "beta", "value": 7, "transport": "b"},
                {"key": "alpha", "value": {"passed": True}},
            ],
        }
        self.head_a = make_head(self.log_a, "a")
        self.head_b = make_head(self.log_b, "b")

    def test_matching_sessions_verify_as_third_party(self):
        block = reconcile("genesis-anchor", self.head_a, self.head_b,
                          self.log_a, self.log_b)
        self.assertTrue(verify_reconciled(
            "genesis-anchor", self.head_a, self.head_b, block
        ))

    def test_verifier_is_idempotent(self):
        block = reconcile("genesis-anchor", self.head_a, self.head_b,
                          self.log_a, self.log_b)
        for _ in range(2):
            self.assertTrue(verify_reconciled(
                "genesis-anchor", self.head_a, self.head_b, block
            ))

        corrupted_block = replace(block, reconciled_hash="invalid")
        for _ in range(2):
            self.assertFalse(verify_reconciled(
                "genesis-anchor", self.head_a, self.head_b, corrupted_block
            ))

    def test_divergent_sessions_return_both_projection_values(self):
        changed = {**self.log_b, "outcomes": [
            {"key": "beta", "value": 8},
            {"key": "alpha", "value": {"passed": True}},
        ]}
        block = reconcile("genesis-anchor", self.head_a, make_head(changed, "b"),
                          self.log_a, changed)
        self.assertIsInstance(block, Divergence)
        self.assertEqual(block.pa, canonical_projection(self.log_a))
        self.assertEqual(block.pb, canonical_projection(changed))

    def test_tampered_head_does_not_verify(self):
        block = reconcile("genesis-anchor", self.head_a, self.head_b,
                          self.log_a, self.log_b)
        self.assertFalse(verify_reconciled(
            "genesis-anchor", self.head_a[:-1] + "0", self.head_b, block
        ))

    def test_wrong_anchor_does_not_verify(self):
        block = reconcile("genesis-anchor", self.head_a, self.head_b,
                          self.log_a, self.log_b)
        self.assertFalse(verify_reconciled(
            "wrong-anchor", self.head_a, self.head_b, block
        ))

    def test_same_head_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile("genesis-anchor", self.head_a, self.head_a,
                      self.log_a, self.log_b)

    def test_projection_is_independent_of_arrival_order(self):
        self.assertEqual(
            canonical_projection(self.log_a),
            canonical_projection(self.log_b),
        )

    def test_head_must_verify_against_its_own_log(self):
        with self.assertRaises(ValueError):
            reconcile("genesis-anchor", "0" * 64, self.head_b,
                      self.log_a, self.log_b)

    def test_projection_rejects_float_in_invariant_value(self):
        with self.assertRaises(ValueError):
            canonical_projection([{"key": "alpha", "value": 0.1}])

    def test_projection_preserves_duplicate_outcomes(self):
        one = [{"key": "alpha", "value": 1}]
        two = one * 2
        self.assertNotEqual(canonical_projection(one), canonical_projection(two))

    def test_projection_excludes_session_metadata(self):
        self.assertEqual(
            canonical_projection(self.log_a),
            canonical_projection({**self.log_a, "timestamp": "elsewhere"}),
        )

    def test_empty_and_partial_sessions(self):
        empty_a = {"session_id": "empty-a", "outcomes": []}
        empty_b = {"session_id": "empty-b", "outcomes": []}
        empty_block = reconcile(
            "genesis-anchor", make_head(empty_a), make_head(empty_b),
            empty_a, empty_b,
        )
        self.assertNotIsInstance(empty_block, Divergence)
        self.assertEqual(
            canonical_projection(empty_a), canonical_projection(empty_b),
        )

        non_empty = {
            "session_id": "non-empty",
            "outcomes": [{"key": "alpha", "value": 1}],
        }
        partial_block = reconcile(
            "genesis-anchor", make_head(empty_a), make_head(non_empty),
            empty_a, non_empty,
        )
        self.assertIsInstance(partial_block, Divergence)

        duplicate_outcome = {"key": "alpha", "value": 1}
        repeated = {
            "session_id": "repeated",
            "outcomes": [duplicate_outcome, duplicate_outcome],
        }
        single = {
            "session_id": "single",
            "outcomes": [duplicate_outcome],
        }
        with self.subTest("duplicate outcomes use multiset semantics"):
            self.assertIsInstance(
                reconcile(
                    "genesis-anchor", make_head(repeated), make_head(single),
                    repeated, single,
                ),
                Divergence,
            )

    def test_anchor_is_immutable_across_full_cycle(self):
        coordinator = SentinelDotCoordinator()
        sentinels = {}
        for instance_id in coordinator.instance_ids:
            sentinel = SentinelDotIgnitionStub()
            sentinel.bind(coordinator, instance_id)
            sentinels[instance_id] = sentinel

        genesis = bootstrap_genesis(coordinator)
        anchor_bytes = genesis.block_id.encode("utf-8")

        invariant_source = sentinels[coordinator.invariant_source_id]
        symbol_source = sentinels[coordinator.symbol_source_id]
        invariant_source.publish_invariant_projection({"members": ["complete"]})
        release = symbol_source.publish_accumulated_symbol("complete")
        self.assertIsNotNone(release)

        cycle = run_cycle(coordinator=coordinator)
        outcomes = [
            {"key": "gate_released", "value": coordinator.state["gate_released"]},
            {"key": "genesis_block_id", "value": genesis.block_id},
            {"key": "session_completed", "value": True},
        ]
        log_a = {
            "session_id": "session-a",
            "cycle": cycle,
            "outcomes": outcomes,
        }
        log_b = {
            "session_id": "session-b",
            "cycle": cycle,
            "outcomes": outcomes,
        }
        head_a = make_head(log_a)
        head_b = make_head(log_b)
        block = reconcile(genesis.block_id, head_a, head_b, log_a, log_b)

        self.assertTrue(verify_reconciled(genesis.block_id, head_a, head_b, block))
        self.assertEqual(anchor_bytes, coordinator.genesis.block_id.encode("utf-8"))

    def test_metadata_does_not_affect_projection(self):
        log_a = {
            "timestamp": "2026-01-01T00:00:00Z",
            "session_id": "session-a",
            "hostname": "host-a",
            "transport": {"protocol": "tcp", "port": 8000},
            "outcomes": [
                {
                    "key": "alpha",
                    "value": {"passed": True},
                    "timestamp": "2026-01-01T00:00:01Z",
                    "session_id": "session-a",
                    "hostname": "host-a",
                    "transport": {"sequence": 1, "latency": 0.1},
                },
                {"key": "beta", "value": 7},
            ],
        }
        log_b = {
            "timestamp": "2026-05-01T12:00:00Z",
            "session_id": "session-b",
            "hostname": "host-b",
            "transport": {"protocol": "udp", "port": 9000},
            "outcomes": [
                {
                    "key": "alpha",
                    "value": {"passed": True},
                    "timestamp": "2026-05-01T12:00:02Z",
                    "session_id": "session-b",
                    "hostname": "host-b",
                    "transport": {"sequence": 42, "latency": 0.2},
                },
                {"key": "beta", "value": 7},
            ],
        }
        self.assertEqual(canonical_projection(log_a), canonical_projection(log_b))


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import unittest

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

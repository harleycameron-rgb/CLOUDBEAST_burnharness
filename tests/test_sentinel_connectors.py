import base64
import json
import math
import os
import tempfile
import unittest
from unittest.mock import patch

from engine_alignment.adapter import invariant_core
from engine_alignment.adapter import connect as connect_alignment
from provenance_bridge.adapter import connect as connect_provenance
from sentinel_link.adapter import SentinelLink, connect as connect_link, encode
from temporal_anchor.adapter import connect as connect_temporal

from benchmarks.fire import ORRERY_TEST_VECTOR, probe_adapters
from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import SentinelDotIgnitionStub
from coordinator import SentinelDotCoordinator, bootstrap_genesis

KEY = b"k" * 32


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "ledger.jsonl")
        self.link = connect_link(self.path, key=KEY)

    def tamper(self, line_no, field, value):
        with open(self.path) as fh:
            lines = fh.read().splitlines()
        entry = json.loads(lines[line_no])
        entry["parameters"][field] = value
        lines[line_no] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        with open(self.path, "w") as fh:
            fh.write("\n".join(lines) + "\n")


class SentinelLinkTests(Base):
    def test_opens_with_zero_state_and_verifies(self):
        params = self.link.open_entry["parameters"]
        self.assertEqual(params["zero_state"], "0" * 64)
        self.assertEqual(params["key_mode"], "hmac-supplied")
        self.assertEqual(self.link.verify(), (True, []))

    def test_reopen_existing_ledger_appends(self):
        self.link.ingest_substrate({"density": 0.8})
        again = connect_link(self.path, key=KEY)
        self.assertEqual(again.open_entry["seq"], 2)

    def test_reopen_with_wrong_key_refused(self):
        with self.assertRaises(Exception):
            connect_link(self.path, key=b"x" * 32)

    def test_env_key_and_ephemeral_key(self):
        with patch.dict(os.environ, {"SENTINEL_DOT_KEY": base64.b64encode(KEY).decode()}):
            self.assertEqual(connect_link().key_mode, "hmac-env")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(connect_link().key_mode, "hmac-ephemeral")

    def test_short_key_rejected(self):
        with self.assertRaises(ValueError):
            connect_link(key=b"short")

    def test_binds_genesis_block(self):
        coordinator = SentinelDotCoordinator()
        for iid in coordinator.instance_ids:
            SentinelDotIgnitionStub().bind(coordinator, iid)
        bootstrap_genesis(coordinator)
        link = connect_link(key=KEY, coordinator=coordinator)
        self.assertEqual(link.open_entry["parameters"]["genesis_block_id"], coordinator.genesis.block_id)

    def test_substrate_validation_records_rejection(self):
        with self.assertRaises(ValueError):
            self.link.ingest_substrate({})
        self.assertEqual(self.link.log.read_all()[-1]["msg_type"], "rejection")

    def test_encode_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            encode({"x": math.nan})

    def test_anchor_record_matches_head(self):
        path = self.link.anchor_record(now="2026-10-05T00:00:00Z")
        with open(path) as fh:
            record = json.load(fh)
        self.assertEqual((record["next_seq"], record["hash"]), self.link.head())


class TemporalAnchorTests(Base):
    def test_patch_vector_residue(self):
        out = connect_temporal(self.link).ingest_trajectory(ORRERY_TEST_VECTOR)
        self.assertEqual(len(out["residues"]), 2)
        for r in out["residues"]:
            for got, want in zip(r, (0.1, 0.2, 0.05)):
                self.assertAlmostEqual(got, want, places=12)
        self.assertTrue(os.path.exists(out["anchor_record"]))

    def test_list_input_and_topology_source(self):
        out = connect_temporal(self.link).ingest_trajectory([[0, 0, 0], [1, 1, 1]], source="topology_engine")
        self.assertEqual(out["residues"], [[1.0, 1.0, 1.0]])

    def test_bad_inputs_rejected_and_logged(self):
        anchor = connect_temporal(self.link)
        for bad in ({"t0": [0, 0, 0]}, {"t0": [0, 0, 0], "t2": [1, 1, 1]},
                    [[0, 0], [1, 1]], [[0, 0, math.inf], [1, 1, 1]], {"a": [0, 0, 0], "t1": [1, 1, 1]}):
            with self.assertRaises((ValueError, TypeError)):
                anchor.ingest_trajectory(bad)
        with self.assertRaises(ValueError):
            anchor.ingest_trajectory(ORRERY_TEST_VECTOR, source="unknown")
        rejections = [e for e in self.link.log.read_all() if e["msg_type"] == "rejection"]
        self.assertEqual(len(rejections), 6)
        self.assertTrue(self.link.verify()[0])


class ProvenanceBridgeTests(Base):
    def test_fixity_recorded_and_verified(self):
        bridge = connect_provenance(self.link)
        out = bridge.ingest_root_scan(b"page-0001", "book-1/p1")
        self.assertEqual(len(out["sha256"]), 64)
        self.assertTrue(bridge.verify_scan(b"page-0001", "book-1/p1"))
        self.assertFalse(bridge.verify_scan(b"page-0002", "book-1/p1"))
        self.assertFalse(bridge.verify_scan(b"page-0001", "unknown"))

    def test_dict_scan_is_canonicalised(self):
        bridge = connect_provenance(self.link)
        bridge.ingest_root_scan({"b": 1, "a": 2}, "s")
        self.assertTrue(bridge.verify_scan({"a": 2, "b": 1}, "s"))

    def test_scan_content_not_in_ledger(self):
        connect_provenance(self.link).ingest_root_scan(b"SECRET-PAGE-TEXT", "s")
        with open(self.path) as fh:
            self.assertNotIn("SECRET-PAGE-TEXT", fh.read())

    def test_tampered_ledger_blocks_verification(self):
        bridge = connect_provenance(self.link)
        out = bridge.ingest_root_scan(b"x", "s")
        self.tamper(out["seq"], "sha256", "0" * 64)
        with self.assertRaises(Exception):
            bridge.verify_scan(b"x", "s")


class EngineAlignmentTests(Base):
    def test_invariant_core_formula(self):
        core = invariant_core([[3, 4, 0], [3, 4, 0]])
        self.assertEqual(core["stability"], 1.0)
        self.assertAlmostEqual(core["drift"], 5.0)
        self.assertAlmostEqual(core["phase"], math.atan2(4, 3))
        uneven = invariant_core([[1, 0, 0], [3, 0, 0]])
        self.assertAlmostEqual(uneven["stability"], 0.5)

    def test_aligns_from_ledger_latest_batch(self):
        anchor = connect_temporal(self.link)
        anchor.ingest_trajectory([[0, 0, 0], [1, 0, 0]])
        anchor.ingest_trajectory([[0, 0, 0], [0, 2, 0], [0, 4, 0]])
        core = connect_alignment(self.link).align()
        self.assertEqual(core["samples"], 2)
        self.assertAlmostEqual(core["phase"], math.pi / 2)

    def test_no_residue_raises(self):
        with self.assertRaises(ValueError):
            connect_alignment(self.link).align()

    def test_tampered_residue_refused(self):
        anchor = connect_temporal(self.link)
        anchor.ingest_trajectory(ORRERY_TEST_VECTOR)
        sample_line = next(i for i, e in enumerate(self.link.log.read_all())
                           if e["action_type"] == "trajectory:sample" and e["parameters"]["residue"])
        self.tamper(sample_line, "residue", ["9.0", "9.0", "9.0"])
        with self.assertRaises(Exception):
            connect_alignment(self.link).align()


class FireProbeTests(unittest.TestCase):
    def test_all_four_connectors_fire(self):
        results = {r["connector"]: r for r in probe_adapters()}
        self.assertEqual(set(results), {"engine_alignment", "provenance_bridge",
                                        "sentinel_link", "temporal_anchor"})
        for r in results.values():
            self.assertEqual(r["status"], "fired", r)
        self.assertEqual(results["engine_alignment"]["result"]["samples"], 2)

    def test_connectors_require_link(self):
        for fn in (connect_temporal, connect_provenance, connect_alignment):
            with self.assertRaises(TypeError):
                fn(object())
        self.assertIsInstance(connect_link(key=KEY), SentinelLink)


if __name__ == "__main__":
    unittest.main()

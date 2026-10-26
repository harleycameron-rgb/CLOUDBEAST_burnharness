"""provenance_bridge -- ScanDoc root_scan -> Burnharness, recorded in Sentinel_dot.

From ``everything.txt``: ``ScanDoc: root_scan -> provenance_bridge``.

A root scan (raw bytes, or a JSON-compatible dict that is canonicalised) is
fingerprinted with SHA-256 and SHA-512 and its fixity record is appended to the
Sentinel_dot ledger. The scan content itself is never written to the ledger.
``verify_scan`` re-hashes a scan and checks it against the recorded fixity,
reading only from a verified ledger. Scans do not modify Orrery trajectory.
"""

import hashlib
import json

from sentinel_link.adapter import SentinelLink, connect as link_connect

SENDER = "burnharness.provenance_bridge"


def scan_bytes(scan):
    if isinstance(scan, (bytes, bytearray)):
        return bytes(scan)
    if isinstance(scan, dict):
        return json.dumps(scan, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    raise TypeError("root_scan must be bytes or a JSON-compatible dict")


def fixity(scan):
    data = scan_bytes(scan)
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest()}


class ProvenanceBridge:
    def __init__(self, link):
        if not isinstance(link, SentinelLink):
            raise TypeError("provenance_bridge requires a SentinelLink")
        self.link = link
        link.record(SENDER, "connector:open", {"accepts": "scandoc:root_scan"})

    def ingest_root_scan(self, scan, source_id):
        if not isinstance(source_id, str) or not source_id:
            self.link.reject(SENDER, "scandoc:root_scan", "source_id must be a non-empty str")
            raise ValueError("source_id must be a non-empty str")
        try:
            fx = fixity(scan)
        except (TypeError, ValueError) as exc:
            self.link.reject(SENDER, "scandoc:root_scan", str(exc), {"source_id": source_id})
            raise
        entry = self.link.record(SENDER, "scandoc:root_scan", {"source_id": source_id, **fx})
        return {"seq": entry["seq"], "entry_hash": entry["entry_hash"], **fx}

    def verify_scan(self, scan, source_id):
        """True iff the latest recorded fixity for source_id matches this scan."""
        records = [e for e in self.link.entries(SENDER, "scandoc:root_scan")
                   if e["parameters"]["source_id"] == source_id]
        if not records:
            return False
        rec = records[-1]["parameters"]
        fx = fixity(scan)
        return rec["sha256"] == fx["sha256"] and rec["sha512"] == fx["sha512"] and rec["bytes"] == fx["bytes"]


def connect(link=None, **link_kwargs):
    return ProvenanceBridge(link if link is not None else link_connect(**link_kwargs))

# provenance_bridge

ScanDoc `root_scan -> provenance_bridge`. Fingerprints each scan (bytes, or a dict
canonicalised to JSON) with SHA-256 + SHA-512 and records the fixity — never the
content — in the Sentinel_dot ledger. `verify_scan(scan, source_id)` re-hashes and
compares against the latest recorded fixity, reading only from a verified ledger.

# provenance_bridge

ScanDoc `root_scan -> provenance_bridge`. Fingerprints each scan (bytes, or a dict
canonicalised to JSON) with SHA-256 + SHA-512 and records the fixity — never the
content — in the process-local Sentinel Link ledger.
`verify_scan(scan, source_id)` re-hashes and compares against the latest
recorded fixity in that in-memory ledger.

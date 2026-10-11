# superblock

`superblock.py` seals the in-memory Burnharness residue into a SHA-512,
hash-chained block: canonical ignition-state digests, fired coupler outputs,
the resonance field, the `system_validation` digest, and the benchmark registry's
deterministic digest. `block_hash` covers
`parent_hash`, so `verify_chain` detects any edit to an earlier block.
Integrity only: blocks are not signed.

Blocks are returned as Python values and are never written to persistent files.
The body is deterministic for the same code and inputs.

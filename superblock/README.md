# superblock

`superblock.py` seals the Burnharness residue into a SHA-512, hash-chained block:
leg-manifest digests, fired coupler outputs, the resonance field, the
`system_validation` digest, the benchmark registry's deterministic digest and the
commit SHA + counts of every cross-repo test suite. `block_hash` covers
`parent_hash`, so `verify_chain` detects any edit to an earlier block.
Integrity only: blocks are not signed.

`superblock_0000.json` is the genesis block (parent = 128 zeros), written by
`python fire_all.py --write`. The body is deterministic: rebuilding on the same
commits yields the same hash.

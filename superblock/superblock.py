"""Superblock: a hash-chained SHA-512 block that seals the Burnharness residue.

A superblock collects, in canonical JSON, everything a cycle leaves behind:

* the six leg manifests (each content-hashed),
* the fired coupler outputs and the normalised resonance field,
* the ``system_validation`` report digest,
* the deterministic digest of the benchmark registry (timings excluded),
* the commit SHA and pass/fail counts of every cross-repo test suite.

``block_hash`` = SHA-512 over the canonical body, which includes
``parent_hash``. Chaining blocks therefore preserves history: altering any
earlier block breaks every later ``parent_hash`` link (see ``verify_chain``).
Nothing is signed -- this is integrity (tamper evidence), not authenticity.
"""

import hashlib
import json
import os

from benchmarks.fire import build_registry, canonical, sha512
from system_validation import validate_system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGS_DIR = os.path.join(ROOT, "burnharness", "ignition_layer", "legs")
GENESIS_PARENT = "0" * 128
SCHEMA = "burnharness.superblock/1"


def leg_manifest_digests():
    out = {}
    for leg in sorted(os.listdir(LEGS_DIR)):
        path = os.path.join(LEGS_DIR, leg, "leg_manifest.json")
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                out[leg] = hashlib.sha512(fh.read()).hexdigest()
    return out


def build_body(parent_hash=GENESIS_PARENT, height=0, registry=None):
    registry = registry if registry is not None else build_registry(iterations=5)
    report = validate_system()
    suites = [
        {k: s[k] for k in ("repo", "runner", "commit", "exit_code", "counts")}
        for s in registry["cross_repo_suites"]
    ]
    return {
        "schema": SCHEMA,
        "height": height,
        "parent_hash": parent_hash,
        "legs": leg_manifest_digests(),
        "connectors": [
            {k: c[k] for k in ("connector", "kind", "status") if k in c}
            | ({"output": c["output"]} if "output" in c else {})
            for c in registry["connectors"]
        ],
        "resonance_field": registry["resonance_field"],
        "system_validation": {"sha512": report["sha512"], "system_ready": report["system_ready"]},
        "registry_deterministic_sha512": registry["deterministic_sha512"],
        "cross_repo_suites": suites,
    }


def seal(body):
    return {"body": body, "block_hash": sha512(body)}


def build_superblock(parent=None, registry=None):
    if parent is None:
        return seal(build_body(registry=registry))
    return seal(build_body(parent["block_hash"], parent["body"]["height"] + 1, registry))


def verify_block(block):
    return isinstance(block, dict) and sha512(block.get("body")) == block.get("block_hash")


def verify_chain(blocks):
    """Return (ok, index_of_first_failure_or_None)."""
    expected_parent = GENESIS_PARENT
    for i, block in enumerate(blocks):
        body = block.get("body", {})
        if (not verify_block(block) or body.get("parent_hash") != expected_parent
                or body.get("height") != i):
            return False, i
        expected_parent = block["block_hash"]
    return True, None


if __name__ == "__main__":
    print(json.dumps(build_superblock(), indent=2, sort_keys=True))

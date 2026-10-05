"""One-shot pipeline: fire connectors -> register benchmarks -> seal superblock
-> run the causal Lk/Z_m burn anchored on the superblock hash.

    python fire_all.py            # print summary only
    python fire_all.py --write    # also write the three artefacts below

Artefacts:
    benchmarks/registry.json         connector results, timings, cross-repo suites
    superblock/superblock_0000.json  hash-sealed residue (height 0, genesis parent)
    causal_lkzm/burn_report.json     invariant burn report anchored on the block
"""

import json
import os
import sys
import time

from benchmarks.fire import REGISTRY_PATH, build_registry
from causal_lkzm.harness import burn
from superblock.superblock import build_superblock, verify_chain

ROOT = os.path.dirname(os.path.abspath(__file__))
SUPERBLOCK_PATH = os.path.join(ROOT, "superblock", "superblock_0000.json")
BURN_PATH = os.path.join(ROOT, "causal_lkzm", "burn_report.json")


def run(m=7, trials=64, seed=0):
    registry = build_registry()
    block = build_superblock(registry=registry)
    ok, _ = verify_chain([block])
    if not ok:
        raise RuntimeError("freshly built superblock failed verification")
    t0 = time.perf_counter()
    report = burn(block["block_hash"], block["body"]["resonance_field"], m=m, trials=trials, seed=seed)
    elapsed = (time.perf_counter() - t0) * 1000.0
    registry["benchmarks"].append({
        "id": "causal_lkzm.burn", "source": "causal_lkzm/harness.py:burn",
        "timing": {"iterations": 1, "trials": trials, "total_ms": elapsed,
                   "per_trial_ms": elapsed / max(trials, 1)},
    })
    return registry, block, report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    registry, block, report = run()
    if "--write" in argv:
        for path, obj in ((REGISTRY_PATH, registry), (SUPERBLOCK_PATH, block), (BURN_PATH, report)):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    summary = {
        "connectors": registry["summary"],
        "superblock_hash": block["block_hash"],
        "burn_passed": report["passed"],
        "declared_residue": f'{report["declared_residue"]} (mod {report["m"]})',
        "base_lk": report["base_lk"],
        "admissible_preserved": f'{report["admissible"]["preserved"]}/{report["trials"]}',
        "adversarial_detected": {k: v["detected"] for k, v in report["adversarial"].items()},
    }
    print(json.dumps(summary, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

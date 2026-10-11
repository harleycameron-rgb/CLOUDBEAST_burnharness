"""One-shot pipeline: fire connectors -> register benchmarks -> seal superblock
-> run the causal Lk/Z_m burn anchored on the superblock hash.

    python fire_all.py            # print an in-memory summary
"""

import json
import sys
import time

from benchmarks.fire import build_registry
from causal_lkzm.harness import burn
from superblock.superblock import build_superblock, verify_chain

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
    if "--write" in argv:
        raise ValueError("persistent pipeline artifacts are disabled")
    registry, block, report = run()
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

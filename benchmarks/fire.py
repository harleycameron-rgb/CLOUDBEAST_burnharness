"""Fire every Burnharness connector and register timing benchmarks.

"Connectors" here means the six leg-to-leg couplers in ``coupler_cycle`` plus
the four Sentinel_dot adapters (engine_alignment, provenance_bridge,
sentinel_link, temporal_anchor). Adapters that still raise
``NotImplementedError`` are recorded as ``unimplemented`` -- they are never
reported as fired.

Run from the repository root::

    python -m benchmarks.fire            # prints the registry JSON

The registry is returned in memory. Timing fields are measurements and are
excluded from its deterministic digest.

"""

import hashlib
import importlib
import json
import statistics
import sys
import time

from burnharness_protocol import create_stabiliser_packet
from coordinator import benchmark_genesis_bootstrap
from coupler_cycle import COUPLER_SEQUENCE, load_coupler, load_leg, run_cycle

ADAPTERS = ("engine_alignment", "provenance_bridge", "sentinel_link", "temporal_anchor")
FIELDS = ("stability", "curvature", "provenance")
def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha512(obj):
    return hashlib.sha512(canonical(obj).encode("utf-8")).hexdigest()


def _timing(fn, iterations):
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    samples.sort()
    return {
        "iterations": iterations,
        "mean_ms": statistics.fmean(samples),
        "median_ms": statistics.median(samples),
        "p95_ms": samples[min(len(samples) - 1, int(0.95 * len(samples)))],
        "max_ms": samples[-1],
    }


def fire_couplers(packet=None):
    """Fire each coupler once; return ordered, numeric-only outputs."""
    fired = []
    for leg_a, leg_b, name in COUPLER_SEQUENCE:
        coupler = load_coupler(name)(load_leg(leg_a), load_leg(leg_b), packet)
        out = coupler.couple()
        fired.append({
            "connector": name,
            "kind": "coupler",
            "legs": [leg_a, leg_b],
            "status": "fired",
            "output": {k: out[k] for k in FIELDS},
            "diagnostic": coupler.diagnostic(),
        })
    return fired


# Test vector from burnharness/integration_patch.txt (PATCH 1).
ORRERY_TEST_VECTOR = {"t0": [0, 0, 1], "t1": [0.1, 0.2, 1.05], "t2": [0.2, 0.4, 1.1]}


def probe_adapters(link_kwargs=None):
    """Fire all four Sentinel_dot connectors end-to-end on one shared ledger.

    sentinel_link opens the ledger and ingests the Waxtablet substrate;
    temporal_anchor ingests the Orrery test vector; provenance_bridge records
    the ScanDoc root scan; engine_alignment derives invariant_core from the
    recorded residue. A connector is ``fired`` only if its step succeeds and
    the ledger verifies afterwards. Outputs exclude key-dependent hashes so
    they stay deterministic.
    """
    results = {}

    def attempt(name, fn):
        try:
            out = fn()
            results[name] = {"connector": name, "kind": "adapter", "status": "fired",
                             "detail": None, "result": out}
        except NotImplementedError as exc:
            results[name] = {"connector": name, "kind": "adapter", "status": "unimplemented",
                             "detail": str(exc)}
        except Exception as exc:  # surfaced, not hidden
            results[name] = {"connector": name, "kind": "adapter", "status": "error",
                             "detail": f"{type(exc).__name__}: {exc}"}

    mods = {n: importlib.import_module(f"{n}.adapter") for n in ADAPTERS}
    state = {}

    def fire_link():
        state["link"] = mods["sentinel_link"].connect(**(link_kwargs or {}))
        substrate = load_leg("waxtablet_engine").ignite()
        state["link"].ingest_substrate(dict(substrate))
        return {"zero_state": state["link"].open_entry["parameters"]["zero_state"]}

    def fire_temporal():
        out = mods["temporal_anchor"].connect(state["link"]).ingest_trajectory(ORRERY_TEST_VECTOR)
        return {"residues": out["residues"], "anchored": out["anchor_record"] is not None}

    def fire_provenance():
        scan = dict(load_leg("scandoc").ignite())
        bridge = mods["provenance_bridge"].connect(state["link"])
        fx = bridge.ingest_root_scan(scan, "scandoc:root_scan")
        if not bridge.verify_scan(scan, "scandoc:root_scan"):
            raise RuntimeError("recorded fixity does not match scan")
        return {"bytes": fx["bytes"], "sha256": fx["sha256"]}

    def fire_alignment():
        core = mods["engine_alignment"].connect(state["link"]).align()
        return {k: core[k] for k in ("stability", "phase", "drift", "mean_residue", "samples")}

    attempt("sentinel_link", fire_link)
    for name, fn in (("temporal_anchor", fire_temporal), ("provenance_bridge", fire_provenance),
                     ("engine_alignment", fire_alignment)):
        if "link" in state:
            attempt(name, fn)
        else:
            results[name] = {"connector": name, "kind": "adapter", "status": "error",
                             "detail": "sentinel_link did not open"}
    if "link" in state:
        ok, issues = state["link"].verify()
        if not ok:
            for r in results.values():
                if r["status"] == "fired":
                    r["status"], r["detail"] = "error", f"ledger failed verification: {issues[:2]}"
        results["sentinel_link"].setdefault("result", {})["ledger_entries"] = state["link"].head()[0]
    return [results[n] for n in ADAPTERS]


def load_cross_repo():
    """Cross-repository results are not loaded from persistent artifacts."""
    return []


def build_registry(iterations=200):
    packet = create_stabiliser_packet()
    couplers = fire_couplers(packet)
    adapters = probe_adapters()
    field = run_cycle(packet)
    benchmarks = [
        {"id": "genesis_bootstrap", "source": "coordinator.benchmark_genesis_bootstrap",
         "timing": benchmark_genesis_bootstrap(iterations)},
        {"id": "coupler_cycle", "source": "coupler_cycle.run_cycle",
         "timing": _timing(lambda: run_cycle(packet), iterations)},
    ]
    for leg_a, leg_b, name in COUPLER_SEQUENCE:
        cls = load_coupler(name)
        benchmarks.append({
            "id": f"coupler.{name}", "source": f"couplers/{name}/coupler.py",
            "timing": _timing(lambda c=cls, a=leg_a, b=leg_b: c(load_leg(a), load_leg(b), packet).couple(),
                              iterations),
        })
    deterministic = {"couplers": couplers, "adapters": adapters, "resonance_field": field}
    return {
        "schema": "burnharness.benchmark_registry/1",
        "python": sys.version.split()[0],
        "connectors": couplers + adapters,
        "resonance_field": field,
        "deterministic_sha512": sha512(deterministic),
        "benchmarks": benchmarks,
        "cross_repo_suites": load_cross_repo(),
        "summary": {
            "couplers_fired": sum(c["status"] == "fired" for c in couplers),
            "adapters_fired": sum(a["status"] == "fired" for a in adapters),
            "adapters_unimplemented": sum(a["status"] == "unimplemented" for a in adapters),
        },
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--write" in argv:
        raise ValueError("persistent benchmark artifacts are disabled")
    registry = build_registry()
    text = json.dumps(registry, indent=2, sort_keys=True)
    print(text)
    return registry


if __name__ == "__main__":
    main()

"""Fire every Burnharness connector and register timing benchmarks.

"Connectors" here means the six leg-to-leg couplers in ``coupler_cycle`` plus
the four Sentinel_dot adapters (engine_alignment, provenance_bridge,
sentinel_link, temporal_anchor). Adapters that still raise
``NotImplementedError`` are recorded as ``unimplemented`` -- they are never
reported as fired.

Run from the repository root::

    python -m benchmarks.fire            # prints the registry JSON
    python -m benchmarks.fire --write    # also writes benchmarks/registry.json

The registry is deterministic except for the ``timing`` blocks, which are
wall-clock measurements on the machine that ran them.
"""

import hashlib
import importlib
import json
import os
import statistics
import sys
import time

from burnharness_protocol import create_stabiliser_packet
from coordinator import benchmark_genesis_bootstrap
from coupler_cycle import COUPLER_SEQUENCE, load_coupler, load_leg, run_cycle

ADAPTERS = ("engine_alignment", "provenance_bridge", "sentinel_link", "temporal_anchor")
FIELDS = ("stability", "curvature", "provenance")
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "registry.json")
CROSS_REPO_PATH = os.path.join(HERE, "cross_repo_results.json")


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


def probe_adapters():
    probed = []
    for name in ADAPTERS:
        module = importlib.import_module(f"{name}.adapter")
        try:
            module.connect()
            status, detail = "fired", None
        except NotImplementedError as exc:
            status, detail = "unimplemented", str(exc)
        except Exception as exc:  # pragma: no cover - surfaced, not hidden
            status, detail = "error", f"{type(exc).__name__}: {exc}"
        probed.append({"connector": name, "kind": "adapter", "status": status, "detail": detail})
    return probed


def load_cross_repo():
    if not os.path.exists(CROSS_REPO_PATH):
        return []
    with open(CROSS_REPO_PATH, encoding="utf-8") as fh:
        return json.load(fh)


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
    registry = build_registry()
    text = json.dumps(registry, indent=2, sort_keys=True)
    if "--write" in argv:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return registry


if __name__ == "__main__":
    main()

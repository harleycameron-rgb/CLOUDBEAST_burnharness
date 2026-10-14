"""Run and verify the Burnharness pipeline without filesystem access."""

import importlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from benchmarks.fire import ADAPTERS, build_registry
from causal_lkzm.harness import burn
from coupler_cycle import COUPLER_SEQUENCE, load_coupler, load_leg
from stabiliser import Stabiliser
from superblock.superblock import build_superblock, verify_chain
from system_validation import check_environment, validate_system
from zero_data import forbid_file_io

TRIALS = 8
ITERATIONS = 2


def _preload_runtime():
    """Import all modules before the no-filesystem execution guard is engaged."""
    manifest_modules = (
        "burnharness_protocol",
        "coupler_cycle",
        "UNIFIED_FIELD_ZIPGATE.geometry.ignition.ignition_algebra",
        "couplers.organism_runtime",
        "burnharness.ignition_layer.legs.scandoc.ignition_stub",
        "burnharness.ignition_layer.legs.invariant_surface.ignition_stub",
        "burnharness.ignition_layer.legs.topology_engine.ignition_stub",
        "burnharness.ignition_layer.legs.waxtablet_engine.ignition_stub",
        "burnharness.ignition_layer.legs.orrery.ignition_stub",
        "burnharness.ignition_layer.legs.sentinel_dot.ignition_stub",
        "sentinel_link.adapter",
        "temporal_anchor.adapter",
        "provenance_bridge.adapter",
        "engine_alignment.adapter",
    )
    for module_name in manifest_modules:
        importlib.import_module(module_name)
    for first, second, name in COUPLER_SEQUENCE:
        load_leg(first)
        load_leg(second)
        load_coupler(name)
    importlib.import_module("benchmarks.fire")
    importlib.import_module("causal_lkzm.harness")
    importlib.import_module("superblock.superblock")
    if not check_environment():
        raise RuntimeError("in-memory runtime preflight failed")


def _registry_projection(registry):
    return {
        "schema": registry["schema"],
        "python": registry["python"],
        "connectors": registry["connectors"],
        "resonance_field": registry["resonance_field"],
        "deterministic_sha512": registry["deterministic_sha512"],
        "benchmarks": [
            {"id": benchmark["id"], "source": benchmark["source"]}
            for benchmark in registry["benchmarks"]
        ],
        "cross_repo_suites": registry["cross_repo_suites"],
        "summary": registry["summary"],
    }


def _run_once():
    stabiliser = Stabiliser()
    registry = build_registry(iterations=ITERATIONS)
    registry_output = _registry_projection(registry)
    connectors_passed = all(
        connector["status"] == "fired"
        for connector in registry_output["connectors"]
    )
    if not connectors_passed:
        raise RuntimeError("one or more connectors failed")
    stabiliser.record("benchmark", registry_output)

    block = build_superblock(registry=registry)
    chain_valid = verify_chain([block]) == (True, None)
    validation = validate_system()
    if not chain_valid or not validation["system_ready"]:
        raise RuntimeError("superblock verification failed")
    stabiliser.record("superblock", block)

    burn_report = burn(
        block["block_hash"],
        block["body"]["resonance_field"],
        m=7,
        trials=TRIALS,
        seed=0,
    )
    if not burn_report["passed"]:
        raise RuntimeError("causal burn verification failed")
    stabiliser.record("causal_burn", burn_report)

    verification = {
        "connectors_passed": connectors_passed,
        "environment_ready": validation["environment_ready"],
        "system_ready": validation["system_ready"],
        "superblock_chain_valid": chain_valid,
        "burn_passed": burn_report["passed"],
    }
    if not all(verification.values()):
        raise RuntimeError("supervised verification failed")
    stabiliser.record("verification", verification)
    steps = stabiliser.finish()
    return {
        "steps": steps,
        "outputs": {
            "registry": registry_output,
            "superblock": block,
            "burn_report": burn_report,
            "verification": verification,
        },
    }


def run_supervised_build():
    """Run two independent in-memory passes and fail on any step drift."""
    _preload_runtime()
    with forbid_file_io():
        first = _run_once()
        second = _run_once()
    Stabiliser.verify_repeat(first["steps"], second["steps"])
    return {
        "mode": "zero_data",
        "passed": True,
        "deterministic": True,
        "persistent_artifacts": False,
        "steps": first["steps"],
        "sentinel_hash": Stabiliser.sentinel_hash(first["steps"]),
        "outputs": first["outputs"],
    }


def main():
    result = run_supervised_build()
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return result


if __name__ == "__main__":
    main()

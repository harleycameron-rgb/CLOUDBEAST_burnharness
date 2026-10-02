"""Validate the local Burnharness cycle and its resonance field."""

import hashlib
import importlib
import json
import math
from pathlib import Path

from coupler_cycle import COUPLER_SEQUENCE, load_leg, run_cycle
from burnharness_protocol import protocol_upgrade_met
from repo_manifest import REPOSITORY_ROOT, get_manifest

FIELD_NAMES = ("stability", "curvature", "provenance")
MAX_INPUT_BYTES = 4096
DRIFT_LIMIT = 0.05
TOLERANCE = 1e-9


def check_environment(coordinator=None):
    """Check local modules, paths, and leg/coupler configuration."""
    if not protocol_upgrade_met():
        return False
    manifest = get_manifest()
    try:
        for section in manifest["paths"].values():
            for path in section.values():
                if not Path(path).exists():
                    return False
        for module in manifest["imports"].values():
            importlib.import_module(module)
        root = Path(REPOSITORY_ROOT)
        for first, second, coupler in COUPLER_SEQUENCE:
            for leg in (first, second):
                path = root / "burnharness" / "ignition_layer" / "legs" / leg / "leg_manifest.json"
                with path.open(encoding="utf-8") as stream:
                    config = json.load(stream)
                if (not isinstance(config, dict) or config.get("leg") != leg
                        or not isinstance(config.get("ignition_state"), dict)
                        or config["ignition_state"] != load_leg(
                            leg, coordinator=coordinator
                        ).ignite()):
                    return False
            path = root / "couplers" / coupler / "coupler_manifest.json"
            with path.open(encoding="utf-8") as stream:
                config = json.load(stream)
            if (not isinstance(config, dict) or config.get("coupler") != coupler
                    or list(config.get("legs", [])) != [first, second]):
                return False
    except Exception:
        return False
    return True


def canonical_model(data):
    """Serialize the resonance field with deterministic key ordering."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _configuration_snapshot():
    root = Path(REPOSITORY_ROOT)
    legs = {leg for first, second, _ in COUPLER_SEQUENCE for leg in (first, second)}
    paths = [
        root / "burnharness" / "ignition_layer" / "legs" / leg / "leg_manifest.json"
        for leg in sorted(legs)
    ]
    paths.extend(
        root / "couplers" / coupler / "coupler_manifest.json"
        for _, _, coupler in COUPLER_SEQUENCE
    )
    return get_manifest(), tuple(path.read_bytes() for path in paths)


def check_boundary(data):
    """Only accept small, finite resonance fields with expected keys."""
    if not isinstance(data, dict) or set(data) != set(FIELD_NAMES):
        return False
    if any(type(data[key]) not in (int, float) or not math.isfinite(data[key])
           or not 0 <= data[key] <= 1 for key in FIELD_NAMES):
        return False
    try:
        return len(canonical_model(data).encode("utf-8")) <= MAX_INPUT_BYTES
    except (TypeError, ValueError, OverflowError):
        return False


def check_consistency(data):
    """Serialize a field forward, then reconstruct it from that representation."""
    forward_result = canonical_model(data)
    reverse_result = json.loads(forward_result)
    return all(math.isclose(data[key], reverse_result[key], rel_tol=0,
                            abs_tol=TOLERANCE) for key in FIELD_NAMES)


def check_integrity(data):
    """Check repeatability, length and input sensitivity of the SHA-512 seal."""
    model = canonical_model(data)
    digest = hashlib.sha512(model.encode("utf-8")).hexdigest()
    altered = dict(data)
    altered["stability"] = 0 if data["stability"] != 0 else 1
    changed = hashlib.sha512(canonical_model(altered).encode("utf-8")).hexdigest()
    in_range = 0 <= data["stability"] <= 1
    return (in_range
            and len(digest) == 128
            and digest == hashlib.sha512(model.encode("utf-8")).hexdigest()
            and digest != changed), digest


def validate_system(input_data=None, coordinator=None):
    """Return a fail-closed readiness report for the local cycle.

    If input_data is omitted, use the first cycle output as the input field.
    Subsequent cycles must remain within the strict drift threshold.
    """
    report = {
        "environment_ready": check_environment(coordinator=coordinator),
        "boundary_valid": False,
        "stable": False,
        "consistent": False,
        "integrity_verified": False,
        "drift": None,
        "canonical_model": None,
        "sha512": None,
        "system_ready": False,
    }
    if not report["environment_ready"]:
        return report
    if input_data is not None and not check_boundary(input_data):
        return report
    try:
        initial_config = _configuration_snapshot()
        samples = [
            run_cycle(coordinator=coordinator) for _ in range(3)
        ]
        report["environment_ready"] = (
            check_environment(coordinator=coordinator)
            and _configuration_snapshot() == initial_config
        )
        if not report["environment_ready"]:
            return report
        data = samples[0] if input_data is None else input_data
        report["boundary_valid"] = check_boundary(data) and all(
            check_boundary(sample) for sample in samples
        )
        if not report["boundary_valid"]:
            return report
        report["drift"] = max(
            abs(sample[key] - samples[0][key])
            for sample in samples[1:] for key in FIELD_NAMES
        )
        report["stable"] = report["drift"] < DRIFT_LIMIT
        report["consistent"] = (
            check_consistency(data)
            and all(math.isclose(data[key], samples[0][key], rel_tol=0,
                                 abs_tol=TOLERANCE) for key in FIELD_NAMES)
        )
        report["integrity_verified"], report["sha512"] = check_integrity(data)
        report["canonical_model"] = canonical_model(data)
    except Exception:
        return report
    report["system_ready"] = all(report[key] for key in (
        "environment_ready", "boundary_valid", "stable", "consistent",
        "integrity_verified"
    ))
    return report


def system_heartbeat(coordinator):
    """Return anchored readiness without sampling before Genesis."""
    try:
        coordinator._require_genesis()
    except (AttributeError, RuntimeError):
        return {
            "anchored": False,
            "genesis_block_id": None,
            "readiness": None,
            "reason": "genesis_not_locked",
        }
    genesis = coordinator.genesis
    if genesis is None or not coordinator.genesis_anchor_locked:
        return {
            "anchored": False,
            "genesis_block_id": None,
            "readiness": None,
            "reason": "genesis_not_locked",
        }
    try:
        sentinel = load_leg("sentinel_dot", coordinator=coordinator)
    except (RuntimeError, ValueError):
        return {
            "anchored": False,
            "genesis_block_id": None,
            "readiness": None,
            "reason": "genesis_not_locked",
        }
    if sentinel.genesis_block_id is None or (
        sentinel.genesis_block_id != genesis.block_id
    ):
        return {
            "anchored": False,
            "genesis_block_id": None,
            "readiness": None,
            "reason": "genesis_not_locked",
        }
    report = validate_system(coordinator=coordinator)
    checks = (
        "environment_ready", "boundary_valid", "stable", "consistent",
        "integrity_verified"
    )
    return {
        "anchored": True,
        "genesis_block_id": genesis.block_id,
        "readiness": all(report.get(check) is True for check in checks),
    }


if __name__ == "__main__":
    print(json.dumps(validate_system(), indent=2))

"""Local Invariant Tap TEST -> TOPOLOGY -> RETEST -> EVIDENCE slice.

No upstream importer, sensor driver, persistence, external receipt, or launcher.
All public execution is guarded; dependencies must be preloaded by the caller.
"""

from dataclasses import dataclass
import hashlib
import json
import math
import re

from burnharness_protocol import create_stabiliser_packet, propagate_stabiliser_packet
from coupler_cycle import COUPLER_SEQUENCE, run_cycle
from stabiliser import canonical_bytes
from system_validation import (
    DRIFT_LIMIT, FIELD_NAMES, TOLERANCE, check_boundary, validate_system,
)
from zero_data import FileIOViolation, forbid_file_io

ENVELOPE_SCHEMA = "invariant-test-envelope/1"
TOPOLOGY_SCHEMA = "invariant-interface-topology/1"
RETEST_SCHEMA = "invariant-retest/1"
EVIDENCE_SCHEMA = "invariant-harvest-evidence/1"
LOCAL_REVISION = "local-invariant-tap/1"
FIXTURE_ID = "local-burnharness-cycle/1"
PROFILE_ID = "local-resonance-retest/1"
PRIVACY = {"raw_payloads": "forbidden", "evidence": "process_memory_only"}
_IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,79}\Z")
ENVELOPE_KEYS = {
    "schema", "event_id", "module_id", "revision", "input_schema",
    "output_schema", "fixture_id", "reference_id", "transform", "privacy",
    "test_profile", "source",
}


def _copy(value):
    # Canonical JSON detaches metadata, and rejects NaN/Infinity.
    return json.loads(canonical_bytes(value))


def commitment(domain, value):
    """Domain-separated representation equality, never a metric or signature."""
    if domain not in (ENVELOPE_SCHEMA, TOPOLOGY_SCHEMA, RETEST_SCHEMA, EVIDENCE_SCHEMA, "invariant-derived-sample/1"):
        raise ValueError("unknown commitment domain")
    return hashlib.sha512(domain.encode("ascii") + b"\0" + canonical_bytes(value)).hexdigest()


def _identifier(value):
    return (type(value) is str and _IDENTIFIER.fullmatch(value) is not None
            and "//" not in value)


def _number(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_envelope(value):
    """A narrow declaration boundary, not arbitrary upstream schema execution."""
    if not isinstance(value, dict) or set(value) != ENVELOPE_KEYS:
        raise ValueError("invalid envelope boundary")
    fixed = {
        "schema": ENVELOPE_SCHEMA, "module_id": "invarianttap",
        "revision": LOCAL_REVISION, "input_schema": "declared-local-tap/1",
        "output_schema": "burnharness-resonance/1",
        "fixture_id": FIXTURE_ID, "privacy": PRIVACY,
    }
    if any(value[key] != expected for key, expected in fixed.items()):
        raise ValueError("unsupported declaration or privacy policy")
    if (not _identifier(value["event_id"]) or not _identifier(value["reference_id"])
            or value["source"] not in ("synthetic_local_fixture", "declared_local_event")):
        raise ValueError("invalid local identity")
    transform = value["transform"]
    if (not isinstance(transform, dict) or set(transform) != {"id", "scale"}
            or transform["id"] not in ("identity/1", "uniform-scale/1")
            or not _number(transform["scale"], .1, 2)
            or transform["id"] == "identity/1" and transform["scale"] != 1):
        raise ValueError("invalid declared transform")
    profile = value["test_profile"]
    if (not isinstance(profile, dict) or set(profile) != {"id", "scope", "drift_limit"}
            or profile["id"] != PROFILE_ID
            or profile["scope"] not in ("local_fixture", "upstream")
            or not _number(profile["drift_limit"], .000001, DRIFT_LIMIT)):
        raise ValueError("invalid test profile")
    if len(canonical_bytes(value)) > 4096:
        raise ValueError("envelope too large")
    return _copy(value)


@dataclass(frozen=True)
class CapturedTap:
    """Ephemeral derived field, separate from the metadata-only envelope."""
    envelope_bytes: bytes
    field: tuple

    @property
    def envelope(self):
        return json.loads(self.envelope_bytes)


def capture_tap(event, field, *, reference_id=FIXTURE_ID, scope="local_fixture",
                scale=1, drift_limit=DRIFT_LIMIT):
    """Capture a declared local event, without reading hardware or retaining media."""
    if (not isinstance(event, dict) or set(event) != {"event_id", "revision", "source"}
            or not check_boundary(field)):
        raise ValueError("invalid local tap boundary")
    envelope = validate_envelope({
        "schema": ENVELOPE_SCHEMA, "event_id": event["event_id"],
        "module_id": "invarianttap", "revision": event["revision"],
        "source": event["source"], "input_schema": "declared-local-tap/1",
        "output_schema": "burnharness-resonance/1", "fixture_id": FIXTURE_ID,
        "reference_id": reference_id,
        "transform": {"id": "identity/1" if scale == 1 else "uniform-scale/1", "scale": scale},
        "privacy": dict(PRIVACY),
        "test_profile": {"id": PROFILE_ID, "scope": scope, "drift_limit": drift_limit},
    })
    return CapturedTap(canonical_bytes(envelope), tuple(field[key] for key in FIELD_NAMES))


def extract_topology(envelope):
    """Extract declared interfaces only; seals cannot reconstruct unknown source."""
    e = validate_envelope(envelope)
    edges = [{"from": "invarianttap", "to": "burnharness", "schema": e["output_schema"],
              "basis": "declared_adapter_contract"}]
    edges.extend({"from": a, "to": b, "coupler": c, "basis": "declared_local_stub"}
                 for a, b, c in COUPLER_SEQUENCE)
    edges.sort(key=lambda edge: canonical_bytes(edge))
    body = {"schema": TOPOLOGY_SCHEMA, "module_id": e["module_id"],
            "envelope_commitment": commitment(ENVELOPE_SCHEMA, e),
            "nodes": sorted({name for edge in edges for name in (edge["from"], edge["to"])}),
            "edges": edges, "observed_upstream": False,
            "unresolved_upstream": ["invarianttap"], "hash_is_distance_metric": False}
    return {"body": body, "sha512": commitment(TOPOLOGY_SCHEMA, body)}


def retest(captured, reference, packet):
    """Re-execute the existing local cycle; never substitutes it for upstream.

    Residue is max absolute field error in dimensionless resonance units.
    Exact reproduction requires the existing system validation gates as well.
    """
    if not isinstance(captured, CapturedTap):
        raise ValueError("captured tap required")
    e = validate_envelope(captured.envelope)
    if len(captured.field) != len(FIELD_NAMES):
        raise ValueError("invalid ephemeral field")
    data = dict(zip(FIELD_NAMES, captured.field))
    if not check_boundary(data):
        raise ValueError("invalid ephemeral field")
    propagate_stabiliser_packet(packet)
    result = {
        "schema": RETEST_SCHEMA, "event_id": e["event_id"], "reference_id": e["reference_id"],
        "envelope_commitment": commitment(ENVELOPE_SCHEMA, e),
        "status": "indeterminate", "reason": "reference_unavailable",
        "sample_commitment": commitment("invariant-derived-sample/1", data),
        "conditions": {"profile": e["test_profile"], "transform": e["transform"],
                       "source": e["source"], "sensor_hardware_tested": False},
        "residue": None, "uncertainty": "local numerical comparison only; upstream unbound",
        "system_ready": False, "packet_preserved": False,
        "observed_interfaces": [], "upstream_verified": False,
        "production_launch_authorized": False,
    }
    if e["test_profile"]["scope"] == "upstream":
        result["reason"] = "upstream_unbound"
        return result
    if e["reference_id"] != FIXTURE_ID or reference is None:
        return result
    if not check_boundary(reference):
        raise ValueError("invalid local reference")
    transformed = {k: value * e["transform"]["scale"] for k, value in data.items()}
    if not check_boundary(transformed):
        result.update(status="failed", reason="transformed_boundary_invalid")
        return result
    before = dict(packet)
    # This is reviewed, preloaded repository code, not a caller-supplied callback.
    with forbid_file_io():
        try:
            observed = run_cycle(stabiliser_packet=packet)
            validation = validate_system(transformed)
        except FileIOViolation:
            raise
        except Exception as exc:
            result.update(status="failed", reason="local_execution_error", exception_type=type(exc).__name__)
            return result
        preserved = propagate_stabiliser_packet(packet) is packet and dict(packet) == before
        if not check_boundary(observed):
            result.update(status="failed", reason="local_cycle_boundary_invalid")
            return result
        result["packet_preserved"] = preserved
        result["observed_interfaces"] = [{"from": "invarianttap", "to": "burnharness",
                                         "basis": "local_adapter_invocation"}]
        residue = max(abs(transformed[k] - reference[k]) for k in FIELD_NAMES)
        reference_error = max(abs(observed[k] - reference[k]) for k in FIELD_NAMES)
        result["residue"] = {"maximum_absolute_error": residue,
                             "reference_cycle_error": reference_error,
                             "units": "dimensionless_resonance",
                             "exact_tolerance": TOLERANCE,
                             "strict_drift_limit": e["test_profile"]["drift_limit"]}
        base_checks = all(validation.get(key) is True for key in (
            "environment_ready", "boundary_valid", "stable", "integrity_verified",
        ))
        result["system_ready"] = (base_checks and validation.get("consistent") is True
                                  and validation.get("system_ready") is True)
        if reference_error > TOLERANCE or not preserved:
            result.update(status="failed", reason="reference_or_packet_mismatch")
        elif residue >= e["test_profile"]["drift_limit"]:
            result.update(status="failed", reason="drift_limit_reached")
        elif residue <= TOLERANCE and result["system_ready"]:
            result.update(status="reproduced", reason="local_fixture_reproduced")
        elif residue > TOLERANCE and base_checks and validation.get("consistent") is False:
            result.update(status="partial", reason="within_drift_limit_but_not_exact")
        else:
            result.update(status="failed", reason="existing_validation_rejected")
    return result


def run_integration(captured, reference, packet=None):
    """Return permitted process-local evidence; no files, services or upstream loads."""
    with forbid_file_io():
        e = validate_envelope(captured.envelope)
        topology = extract_topology(e)
        packet = create_stabiliser_packet() if packet is None else packet
        result = retest(captured, reference, packet)
        body = {"schema": EVIDENCE_SCHEMA, "envelope": e, "topology": topology,
                "retest": result, "retest_commitment": commitment(RETEST_SCHEMA, result),
                "scope": "local_adapter_only", "persistent_artifacts": False,
                "issuer_authenticated": False, "execution_proven_by_hash": False,
                "upstream_verified": False, "production_launch_authorized": False}
        return {"body": body, "sha512": commitment(EVIDENCE_SCHEMA, body)}


def _retest_consistent(result, envelope):
    if (result["schema"] != RETEST_SCHEMA
            or result["event_id"] != envelope["event_id"]
            or result["reference_id"] != envelope["reference_id"]
            or result["conditions"] != {
                "profile": envelope["test_profile"], "transform": envelope["transform"],
                "source": envelope["source"], "sensor_hardware_tested": False,
            }
            or not re.fullmatch(r"[0-9a-f]{128}", result["sample_commitment"])):
        return False
    required = {
        "schema", "event_id", "reference_id", "envelope_commitment", "status", "reason",
        "sample_commitment", "conditions", "residue", "uncertainty", "system_ready",
        "packet_preserved", "observed_interfaces", "upstream_verified", "production_launch_authorized",
    }
    if set(result) not in (required, required | {"exception_type"}):
        return False
    if "exception_type" in result and (result["status"] != "failed"
                                       or not _identifier(result["exception_type"])):
        return False
    status = result["status"]
    if status == "indeterminate":
        return (result["residue"] is None and result["system_ready"] is False
                and result["observed_interfaces"] == []
                and result["reason"] in ("reference_unavailable", "upstream_unbound"))
    if status == "failed":
        return result["reason"] in (
            "transformed_boundary_invalid", "local_cycle_boundary_invalid",
            "reference_or_packet_mismatch", "drift_limit_reached",
            "existing_validation_rejected", "local_execution_error",
        )
    residue = result["residue"]
    if (envelope["test_profile"]["scope"] != "local_fixture"
            or result["packet_preserved"] is not True
            or not _number(residue["reference_cycle_error"], 0, TOLERANCE)
            or residue["exact_tolerance"] != TOLERANCE
            or residue["strict_drift_limit"] != envelope["test_profile"]["drift_limit"]
            or result["observed_interfaces"] != [{"from": "invarianttap", "to": "burnharness",
                                                   "basis": "local_adapter_invocation"}]):
        return False
    error = residue["maximum_absolute_error"]
    if status == "reproduced":
        return (result["reason"] == "local_fixture_reproduced"
                and result["system_ready"] is True and _number(error, 0, TOLERANCE))
    return (status == "partial" and result["system_ready"] is False
            and result["reason"] == "within_drift_limit_but_not_exact"
            and _number(error, 0, DRIFT_LIMIT)
            and TOLERANCE < error < envelope["test_profile"]["drift_limit"])


def verify_evidence(evidence):
    """Integrity and local consistency only; a recomputed digest is not attestation."""
    try:
        body = evidence["body"]
        return (set(evidence) == {"body", "sha512"}
                and set(body) == {
                    "schema", "envelope", "topology", "retest", "retest_commitment", "scope",
                    "persistent_artifacts", "issuer_authenticated", "execution_proven_by_hash",
                    "upstream_verified", "production_launch_authorized",
                }
                and body["schema"] == EVIDENCE_SCHEMA and body["scope"] == "local_adapter_only"
                and evidence["sha512"] == commitment(EVIDENCE_SCHEMA, body)
                and body["topology"] == extract_topology(body["envelope"])
                and body["retest_commitment"] == commitment(RETEST_SCHEMA, body["retest"])
                and body["retest"]["envelope_commitment"] == commitment(ENVELOPE_SCHEMA, body["envelope"])
                and _retest_consistent(body["retest"], body["envelope"])
                and body["retest"]["upstream_verified"] is False
                and body["retest"]["production_launch_authorized"] is False
                and body["upstream_verified"] is False
                and body["persistent_artifacts"] is False
                and body["issuer_authenticated"] is False
                and body["execution_proven_by_hash"] is False
                and body["production_launch_authorized"] is False)
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def local_fixture():
    """Run the smallest deterministic vertical slice, without a hardware claim."""
    with forbid_file_io():
        reference = run_cycle()
        captured = capture_tap({"event_id": "local-tap-fixture-001", "revision": LOCAL_REVISION,
                                "source": "synthetic_local_fixture"}, reference)
        return run_integration(captured, reference)

"""Order-independent reconciliation of invariant outcomes from two sessions."""

import hashlib
import json
from dataclasses import dataclass

from verify_reconciled import verify


# Invariant allowlist: each outcome contributes only its string "key" and
# JSON-compatible "value"; session metadata, timestamps, and transport are excluded.
# Floats are forbidden recursively in invariant values to avoid representation drift.
# Duplicate outcomes have multiset semantics: every occurrence is preserved.
OUTCOME_FIELDS = ("key", "value")


@dataclass(frozen=True)
class Divergence:
    pa: bytes
    pb: bytes
    reason: str


@dataclass(frozen=True)
class ReconciledBlock:
    anchor_id: str
    head_a_hash: str
    head_b_hash: str
    projection_sha512: str
    reconciled_hash: str
    invariant_summary: dict
    projection: bytes


def _reject_floats(value):
    if type(value) is float:
        raise ValueError("floating-point values are forbidden in invariant outcomes")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("invariant object keys must be strings")
        for nested in value.values():
            _reject_floats(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_floats(nested)


def _outcomes(log):
    if isinstance(log, dict):
        outcomes = log.get("outcomes")
    else:
        outcomes = log
    if not isinstance(outcomes, (list, tuple)):
        raise ValueError("log must contain an outcomes list")
    return outcomes


def canonical_projection(log):
    """Return canonical UTF-8 JSON for the allowlisted invariant outcomes."""
    projected = []
    for outcome in _outcomes(log):
        if not isinstance(outcome, dict) or not isinstance(outcome.get("key"), str):
            raise ValueError("each outcome must be an object with a string key")
        item = {field: outcome[field] for field in OUTCOME_FIELDS if field in outcome}
        if "value" not in item:
            raise ValueError("each outcome must include a value")
        _reject_floats(item)
        projected.append(item)

    # A serialized tie-breaker makes equal-key outcomes deterministic without
    # depending on arrival order; repeated identical entries remain repeated.
    projected.sort(
        key=lambda item: (
            item["key"],
            json.dumps(item, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False),
        )
    )
    return json.dumps(
        projected, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _head_hash(head):
    if isinstance(head, str):
        return head
    if isinstance(head, dict):
        for field in ("head_hash", "hash"):
            value = head.get(field)
            if isinstance(value, str):
                return value
    raise ValueError("head must be a SHA-256 hash or contain one")


def reconcile(anchor, head_a, head_b, log_a, log_b):
    """Verify two session logs and reconcile their invariant projections."""
    if not isinstance(anchor, str) or not anchor:
        raise ValueError("anchor must be a non-empty string")
    hash_a, hash_b = _head_hash(head_a), _head_hash(head_b)
    if hash_a == hash_b:
        raise ValueError(
            "a single sentinel cannot produce an invariant; "
            "the two sessions must have distinct head hashes"
        )
    if not verify(head_a, log_a) or not verify(head_b, log_b):
        raise ValueError("a session head does not verify against its log")

    pa = canonical_projection(log_a)
    pb = canonical_projection(log_b)
    if pa != pb:
        return Divergence(pa, pb, "invariant outcomes differ")

    # Genesis anchors use SHA-512, session heads use SHA-256, and the
    # reconciliation seal uses SHA-512 over the exact UTF-8/byte concatenation.
    reconciled_hash = hashlib.sha512(
        anchor.encode("utf-8") + pa + hash_a.encode("utf-8") + hash_b.encode("utf-8")
    ).hexdigest()
    return ReconciledBlock(
        anchor_id=anchor,
        head_a_hash=hash_a,
        head_b_hash=hash_b,
        projection_sha512=hashlib.sha512(pa).hexdigest(),
        reconciled_hash=reconciled_hash,
        invariant_summary={
            "outcome_count": len(_outcomes(log_a)),
            "outcome_keys": [item["key"] for item in json.loads(pa)],
        },
        projection=pa,
    )

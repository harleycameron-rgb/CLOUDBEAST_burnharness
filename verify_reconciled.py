"""Verification helpers for session heads and reconciled blocks."""

import hashlib
import json


def _head_hash(head):
    if isinstance(head, str):
        return head
    if isinstance(head, dict):
        for field in ("head_hash", "hash"):
            value = head.get(field)
            if isinstance(value, str):
                return value
    return None


def verify(head, log):
    """Verify a SHA-256 head hash against canonical JSON for its complete log."""
    try:
        digest = hashlib.sha256(json.dumps(
            log, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")).hexdigest()
        return _head_hash(head) == digest
    except (TypeError, ValueError, OverflowError, UnicodeError):
        return False


def verify_reconciled(anchor_id, head_a_hash, head_b_hash, block):
    """Return whether a block's SHA-512 seal matches its anchor, heads, and P."""
    try:
        if (not isinstance(anchor_id, str) or not isinstance(head_a_hash, str)
                or not isinstance(head_b_hash, str) or head_a_hash == head_b_hash
                or block.anchor_id != anchor_id
                or block.head_a_hash != head_a_hash
                or block.head_b_hash != head_b_hash
                or not isinstance(block.projection, bytes)):
            return False
        expected_projection_hash = hashlib.sha512(block.projection).hexdigest()
        expected_reconciled_hash = hashlib.sha512(
            anchor_id.encode("utf-8") + block.projection
            + head_a_hash.encode("utf-8") + head_b_hash.encode("utf-8")
        ).hexdigest()
        return (
            block.projection_sha512 == expected_projection_hash
            and block.reconciled_hash == expected_reconciled_hash
        )
    except Exception:
        return False

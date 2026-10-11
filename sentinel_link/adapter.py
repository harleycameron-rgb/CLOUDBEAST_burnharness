"""In-memory, tamper-evident Sentinel_dot-compatible connector ledger."""

import base64
import copy
import hashlib
import hmac
import json
import math
import os

SENDER = "burnharness.sentinel_link"
KEY_ENV = "SENTINEL_DOT_KEY"
GENESIS_HASH = "0" * 64


def encode(value):
    """Coerce values into the ledger schema, representing finite floats as text."""
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float cannot be recorded")
        return repr(value)
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        return {str(key): encode(item) for key, item in value.items()}
    raise TypeError(f"unsupported value type {type(value).__name__}")


def decode_vector(values):
    return [float(value) for value in values]


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _resolve_key(key):
    if key is not None:
        if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
            raise ValueError("key must be bytes of length >= 32")
        return bytes(key), "hmac-supplied"
    raw = os.environ.get(KEY_ENV)
    if raw:
        resolved = base64.b64decode(raw, validate=True)
        if len(resolved) < 32:
            raise ValueError(f"{KEY_ENV} must decode to at least 32 bytes")
        return resolved, "hmac-env"
    return os.urandom(32), "hmac-ephemeral"


class InMemoryAppendOnlyLog:
    """A per-instance append-only log held only in process memory."""

    def __init__(self, key):
        self._key = key
        self._entries = []

    def append(self, msg_type, sender, status_code, action_type, parameters, note):
        previous = self._entries[-1]["entry_hash"] if self._entries else GENESIS_HASH
        entry = {
            "seq": len(self._entries),
            "msg_type": msg_type,
            "sender": sender,
            "status_code": status_code,
            "action_type": action_type,
            "parameters": copy.deepcopy(parameters),
            "note": note,
            "prev_hash": previous,
        }
        entry_hash = hashlib.sha256(_canonical(entry)).hexdigest()
        entry["entry_hash"] = entry_hash
        entry["hmac"] = hmac.new(
            self._key, entry_hash.encode("ascii"), hashlib.sha256
        ).hexdigest()
        self._entries.append(entry)
        return copy.deepcopy(entry)

    def read_all(self):
        return copy.deepcopy(self._entries)

    def head(self):
        last_hash = self._entries[-1]["entry_hash"] if self._entries else GENESIS_HASH
        return len(self._entries), last_hash

    def verify(self, expected_head=None):
        previous = GENESIS_HASH
        issues = []
        for index, entry in enumerate(self._entries):
            try:
                if not isinstance(entry, dict):
                    raise TypeError("ledger entry must be an object")
                payload = {key: value for key, value in entry.items()
                           if key not in ("entry_hash", "hmac")}
                actual_hash = hashlib.sha256(_canonical(payload)).hexdigest()
                expected_hmac = hmac.new(
                    self._key, actual_hash.encode("ascii"), hashlib.sha256
                ).hexdigest()
                entry_hash, signature = entry.get("entry_hash"), entry.get("hmac")
                if (entry.get("seq") != index or entry.get("prev_hash") != previous
                        or not isinstance(entry_hash, str)
                        or not isinstance(signature, str)
                        or not hmac.compare_digest(entry_hash, actual_hash)
                        or not hmac.compare_digest(signature, expected_hmac)):
                    issues.append(index)
                    break
            except (TypeError, ValueError, OverflowError, UnicodeError):
                issues.append(index)
                break
            previous = entry_hash
        if expected_head is not None:
            try:
                if self.head() != expected_head:
                    issues.append("head")
            except (KeyError, TypeError, IndexError):
                issues.append("head")
        return not issues, issues


class SentinelLink:
    """Connector that records and verifies data without touching the filesystem."""

    def __init__(self, log_path=None, key=None, coordinator=None):
        if log_path is not None:
            raise ValueError("persistent ledger paths are disabled")
        self.log_path = None
        self._key, self.key_mode = _resolve_key(key)
        self.log = InMemoryAppendOnlyLog(self._key)
        genesis_id = None
        if coordinator is not None:
            coordinator._require_genesis()
            genesis_id = coordinator.genesis.block_id
        self.genesis_block_id = genesis_id
        self.open_entry = self.record(SENDER, "link:open", {
            "zero_state": GENESIS_HASH,
            "genesis_block_id": genesis_id,
            "key_mode": self.key_mode,
        })

    def record(self, sender, action_type, parameters):
        return self.log.append(
            "action", sender, 0, action_type, encode(parameters), None
        )

    def reject(self, sender, action_type, reason, parameters=None):
        encoded = dict(encode(parameters or {}), reason=reason)
        return self.log.append(
            "rejection", sender, 0, action_type, encoded, None
        )

    def entries(self, sender=None, action_type=None):
        ok, issues = self.verify()
        if not ok:
            raise ValueError(f"ledger verification failed: {issues[:3]}")
        return [entry for entry in self.log.read_all()
                if (sender is None or entry["sender"] == sender)
                and (action_type is None or entry["action_type"] == action_type)]

    def head(self):
        return self.log.head()

    def verify(self, expected_head=None, raise_on_fail=False):
        result = self.log.verify(expected_head)
        if not result[0] and raise_on_fail:
            raise ValueError(f"ledger verification failed: {result[1][:3]}")
        return result

    def anchor_record(self, now=None):
        """Return an ephemeral anchor value; no record is written to disk."""
        sequence, head_hash = self.head()
        record = {"next_seq": sequence, "hash": head_hash}
        if now is not None:
            record["timestamp"] = now
        return record

    def ingest_substrate(self, substrate):
        if not isinstance(substrate, dict) or not substrate:
            self.reject(
                SENDER, "waxtablet:ignition_substrate",
                "substrate must be a non-empty dict",
            )
            raise ValueError("substrate must be a non-empty dict")
        return self.record(
            SENDER, "waxtablet:ignition_substrate", {"substrate": substrate}
        )

    def status(self):
        ok, issues = self.verify()
        next_seq, last = self.head()
        return {
            "connector": "sentinel_link",
            "verified": ok,
            "issues": len(issues),
            "next_seq": next_seq,
            "head": last,
            "key_mode": self.key_mode,
            "genesis_block_id": self.genesis_block_id,
        }


def connect(log_path=None, key=None, coordinator=None):
    """Create a process-local ledger; persistent paths are intentionally refused."""
    return SentinelLink(log_path=log_path, key=key, coordinator=coordinator)

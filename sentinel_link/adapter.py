"""sentinel_link -- the Burnharness connection to Sentinel_dot.

Sentinel_dot (github.com/harleycameron-rgb/sentinel_dot) is a tamper-evident,
append-only JSONL log chained with HMAC-SHA256. ``sentinel_link`` opens one such
log as the shared Burnharness ledger. The other three connectors
(temporal_anchor, provenance_bridge, engine_alignment) write through a
``SentinelLink`` so every crossing into or out of the Burnharness is recorded,
hash-chained and verifiable.

Roles (from ``everything.txt`` / ``burnharness/integration_patch.txt``):

* Sentinel_dot root anchor -- the zero-state is Sentinel_dot's genesis hash
  (64 zeros); the link records it, plus the Genesis ``block_id`` when a
  ``SentinelDotCoordinator`` is supplied.
* Waxtablet_Engine ``ignition_substrate -> sentinel_link`` -- ``ingest_substrate``.

Key handling: pass ``key=`` (>= 32 bytes) or set ``SENTINEL_DOT_KEY`` (base64).
With neither, an ephemeral random key is generated and ``key_mode`` is
``"hmac-ephemeral"``: the log verifies for the lifetime of the object only.
"""

import base64
import math
import os
import tempfile

try:
    from sentinel_dot.anchor import write_anchor_record
    from sentinel_dot.log import GENESIS_HASH, AppendOnlyLog, LogError, verify_log
except ImportError as exc:  # pragma: no cover - surfaced by connect()
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

SENDER = "burnharness.sentinel_link"
KEY_ENV = "SENTINEL_DOT_KEY"


def encode(value):
    """Coerce into Sentinel_dot's strict schema (no floats): floats -> repr."""
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite float cannot be recorded")
        return repr(value)
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    raise TypeError(f"unsupported value type {type(value).__name__}")


def decode_vector(values):
    return [float(v) for v in values]


def _resolve_key(key):
    if key is not None:
        if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
            raise ValueError("key must be bytes of length >= 32")
        return bytes(key), "hmac-supplied"
    raw = os.environ.get(KEY_ENV)
    if raw:
        k = base64.b64decode(raw)
        if len(k) < 32:
            raise ValueError(f"{KEY_ENV} must decode to at least 32 bytes")
        return k, "hmac-env"
    return os.urandom(32), "hmac-ephemeral"


class SentinelLink:
    def __init__(self, log_path=None, key=None, coordinator=None):
        if _IMPORT_ERROR is not None:
            raise ImportError("sentinel_dot is not installed; see requirements.txt") from _IMPORT_ERROR
        if log_path is None:
            self._tmpdir = tempfile.mkdtemp(prefix="burnharness-sentinel-")
            log_path = os.path.join(self._tmpdir, "burnharness.jsonl")
        self.log_path = log_path
        self._key, self.key_mode = _resolve_key(key)
        self.log = AppendOnlyLog(log_path, key=self._key)
        ok, issues = verify_log(log_path, key=self._key) if os.path.exists(log_path) else (True, [])
        if not ok:
            raise LogError(f"existing ledger failed verification: {issues[:3]}")
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

    # -- ledger primitives used by every connector -------------------------
    def record(self, sender, action_type, parameters):
        return self.log.append("action", sender, 0, action_type, encode(parameters), None)

    def reject(self, sender, action_type, reason, parameters=None):
        params = dict(encode(parameters or {}), reason=reason)
        return self.log.append("rejection", sender, 0, action_type, params, None)

    def entries(self, sender=None, action_type=None):
        """Verified read: refuses to return anything from a tampered ledger."""
        self.verify(raise_on_fail=True)
        return [e for e in self.log.read_all()
                if (sender is None or e["sender"] == sender)
                and (action_type is None or e["action_type"] == action_type)]

    def head(self):
        return self.log.head()

    def verify(self, expected_head=None, raise_on_fail=False):
        ok, issues = verify_log(self.log_path, key=self._key, expected_head=expected_head)
        if not ok and raise_on_fail:
            raise LogError(f"ledger verification failed: {issues[:3]}")
        return ok, issues

    def anchor_record(self, now=None):
        """Write an offline Sentinel_dot anchor record of the current head (no network)."""
        return write_anchor_record(self.log_path, now=now)

    # -- Waxtablet_Engine: ignition_substrate -> sentinel_link -------------
    def ingest_substrate(self, substrate):
        if not isinstance(substrate, dict) or not substrate:
            self.reject(SENDER, "waxtablet:ignition_substrate", "substrate must be a non-empty dict")
            raise ValueError("substrate must be a non-empty dict")
        return self.record(SENDER, "waxtablet:ignition_substrate", {"substrate": substrate})

    def status(self):
        ok, issues = self.verify()
        next_seq, last = self.head()
        return {"connector": "sentinel_link", "verified": ok, "issues": len(issues),
                "next_seq": next_seq, "head": last, "key_mode": self.key_mode,
                "genesis_block_id": self.genesis_block_id}


def connect(log_path=None, key=None, coordinator=None):
    """Open (or create) the shared Sentinel_dot ledger and return a SentinelLink."""
    return SentinelLink(log_path=log_path, key=key, coordinator=coordinator)

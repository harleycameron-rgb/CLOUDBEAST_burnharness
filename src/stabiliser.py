"""Canonical state checks for the in-memory agent runtime."""

import hashlib
import json
import re

from zero_data import forbid_file_io


_SENTINEL = re.compile(r"^[0-9a-f]{12}$")


def stabilise_step(step_name, output):
    if not isinstance(step_name, str) or not step_name:
        raise ValueError("step name must be a non-empty string")
    try:
        json.dumps(output, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{step_name} output must be finite JSON-compatible data") from exc
    return True


def enforce_zero_data():
    """Return the filesystem guard context manager for the supervised step scope."""
    return forbid_file_io()


def harmonise_state(state_log):
    return [
        hashlib.sha256(
            json.dumps(
                item, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        ).hexdigest()[:8]
        for item in state_log
    ]


def verify_sentinel(sentinel):
    if not isinstance(sentinel, str) or not _SENTINEL.fullmatch(sentinel):
        raise ValueError("sentinel must be a 12-character lowercase hexadecimal digest")
    return True

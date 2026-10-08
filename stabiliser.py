"""Deterministic step sealing and drift checks for supervised execution."""

import hashlib
import json
import re


STEP_SEQUENCE = ("benchmark", "superblock", "causal_burn", "verification")
_STEP_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class Stabiliser:
    """Seal ordered step outputs and fail closed on malformed or drifting data."""

    def __init__(self, expected_steps=STEP_SEQUENCE):
        self.expected_steps = tuple(expected_steps)
        if (not self.expected_steps
                or any(not isinstance(name, str) or not _STEP_NAME.fullmatch(name)
                       for name in self.expected_steps)
                or len(set(self.expected_steps)) != len(self.expected_steps)):
            raise ValueError("expected step names must be unique valid identifiers")
        self._records = []

    @property
    def records(self):
        return tuple(dict(record) for record in self._records)

    def record(self, name, output):
        if not isinstance(name, str) or not _STEP_NAME.fullmatch(name):
            raise ValueError("step name must be a valid identifier")
        if name not in self.expected_steps:
            raise ValueError(f"unexpected supervised step: {name!r}")
        if len(self._records) >= len(self.expected_steps):
            raise ValueError("all supervised steps have already been recorded")
        expected_name = self.expected_steps[len(self._records)]
        if name != expected_name:
            raise ValueError(
                f"invalid step order: expected {expected_name!r}, got {name!r}"
            )
        try:
            encoded = canonical_bytes(output)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("step output must be finite JSON-compatible data") from exc
        digest = hashlib.sha512(encoded).hexdigest()
        record = {"step": name, "sha512": digest, "passed": True}
        self._records.append(record)
        return dict(record)

    def finish(self):
        names = tuple(record["step"] for record in self._records)
        if names != self.expected_steps:
            raise RuntimeError("supervised run is missing required steps")
        return self.records

    @staticmethod
    def verify_repeat(first, second):
        if tuple(first) != tuple(second):
            raise RuntimeError("supervised step outputs drifted between runs")
        return True

    @staticmethod
    def sentinel_hash(records):
        return hashlib.sha512(canonical_bytes(records)).hexdigest()

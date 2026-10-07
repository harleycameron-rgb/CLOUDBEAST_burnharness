"""In-memory execution and verification of named agent steps."""

import copy
import hashlib
import json


class Supervisor:
    def __init__(self):
        self.steps = {}
        self._results = {}

    def add_step(self, name, *, action, verify):
        if not isinstance(name, str) or not name:
            raise ValueError("step name must be a non-empty string")
        if name in self.steps:
            raise ValueError(f"step already exists: {name!r}")
        if not callable(action) or not callable(verify):
            raise TypeError("step action and verifier must be callable")
        self.steps[name] = {"action": action, "verify": verify}

    def run(self, step, mode="y"):
        if mode != "y":
            raise ValueError("only supervised mode 'y' is supported")
        try:
            definition = self.steps[step]
        except KeyError as exc:
            raise KeyError(f"unknown supervised step: {step!r}") from exc
        if step == next(iter(self.steps)) and tuple(self._results) == tuple(self.steps):
            self._results.clear()
        result = definition["action"]()
        try:
            encoded = json.dumps(
                result, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("step output must be finite JSON-compatible data") from exc
        if not definition["verify"](result):
            raise RuntimeError(f"step verification failed: {step}")
        self._results[step] = json.loads(encoded)
        return copy.deepcopy(self._results[step])

    def residue(self):
        if tuple(self._results) != tuple(self.steps):
            raise RuntimeError("all registered steps must pass before sealing residue")
        payload = json.dumps(
            self._results, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return {
            "sentinel": hashlib.sha256(payload).hexdigest()[:12],
            "steps": copy.deepcopy(self._results),
        }

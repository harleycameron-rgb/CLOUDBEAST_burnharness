"""Validate asymmetric Sentinel Dot state and emit gate-release events."""

import hashlib
import json
import math
import os
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class ParabolaProjection:
    a: float
    b: float
    c: float
    x_min: float = -math.inf
    x_max: float = math.inf
    tolerance: float = 1e-9

    def contains(self, symbol):
        if not isinstance(symbol, dict):
            return False
        x, y = symbol.get("x"), symbol.get("y")
        if (type(x) not in (int, float) or type(y) not in (int, float)
                or not math.isfinite(x) or not math.isfinite(y)
                or not self.x_min <= x <= self.x_max):
            return False
        return math.isclose(
            y, self.a * x * x + self.b * x + self.c,
            rel_tol=0, abs_tol=self.tolerance,
        )


@dataclass(frozen=True)
class ValidationRelease:
    projection_revision: int
    symbol_revision: int
    block_id: str
    genesis_block_id: str
    gate_released: bool = True


@dataclass(frozen=True)
class GenesisAnchor:
    block_id: str


class SentinelDotCoordinator:
    """Non-blocking validation gate for an invariant source and a symbol stream."""

    def __init__(self, instance_ids=("sentinel-a", "sentinel-b")):
        if (len(instance_ids) != 2 or len(set(instance_ids)) != 2
                or any(not isinstance(value, str) or not value
                       for value in instance_ids)):
            raise ValueError("exactly two distinct Sentinel Dot instance IDs are required")
        self.invariant_source_id, self.symbol_source_id = tuple(instance_ids)
        self.instance_ids = tuple(instance_ids)
        self._genesis_barrier = threading.Barrier(len(self.instance_ids))
        self._genesis_distribution_barrier = threading.Barrier(
            len(self.instance_ids)
        )
        self._lock = threading.RLock()
        self._genesis_ready = set()
        self._genesis_distributed = set()
        self._genesis_anchor = None
        self._projection = None
        self._symbol = None
        self._has_projection = False
        self._has_symbol = False
        self._projection_revision = 0
        self._symbol_revision = 0
        self._release = None
        self._listeners = {}
        self._delivered = set()
        self._last_validation = {
            "passed": False,
            "reason": "awaiting invariant projection and accumulated symbol",
        }

    @property
    def state(self):
        with self._lock:
            passed = self._release is not None
            return {
                "genesis_anchor_locked": (
                    self._genesis_anchor is not None
                    and self._genesis_distributed == set(self.instance_ids)
                ),
                "genesis_block_id": (
                    None if self._genesis_anchor is None
                    else self._genesis_anchor.block_id
                ),
                "sync_mechanism_active": True,
                "sync_mode": "ASYMMETRIC_VALIDATION",
                "validation_passed": passed,
                "gate_released": passed,
                "superposition_integrity": passed,
                "no_bung": True,
                "continuity_flow": True,
                "frozen_modules": (),
                "invariant_source_id": self.invariant_source_id,
                "symbol_source_id": self.symbol_source_id,
                "projection_revision": self._projection_revision,
                "symbol_revision": self._symbol_revision,
                "validation": dict(self._last_validation),
                "block_id": None if self._release is None else self._release.block_id,
            }

    @property
    def release(self):
        with self._lock:
            return self._release

    def report_genesis_ready(self, instance_id, timeout=None):
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        with self._lock:
            if self._genesis_anchor is not None:
                return self._genesis_anchor
            if instance_id in self._genesis_ready:
                raise RuntimeError(
                    f"Sentinel Dot instance {instance_id!r} already reported genesis readiness"
                )
            self._genesis_ready.add(instance_id)

        try:
            self._genesis_barrier.wait(timeout)
        except threading.BrokenBarrierError:
            raise TimeoutError("both Sentinel Dot instances must reach genesis") from None

        with self._lock:
            if self._genesis_anchor is None:
                self._genesis_anchor = GenesisAnchor(
                    hashlib.sha512(os.urandom(64)).hexdigest()
                )
            return self._genesis_anchor

    def confirm_genesis_distributed(self, instance_id, anchor, timeout=None):
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        with self._lock:
            if anchor is not self._genesis_anchor:
                raise ValueError("only the coordinator's Genesis anchor can be distributed")
            if instance_id in self._genesis_distributed:
                raise RuntimeError(
                    f"Sentinel Dot instance {instance_id!r} already received Genesis"
                )
            self._genesis_distributed.add(instance_id)
        try:
            self._genesis_distribution_barrier.wait(timeout)
        except threading.BrokenBarrierError:
            raise TimeoutError("both Sentinel Dot instances must receive Genesis") from None
        return anchor

    def subscribe(self, instance_id, callback):
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        if not callable(callback):
            raise TypeError("gate event callback must be callable")
        with self._lock:
            self._listeners[instance_id] = callback
            deliveries = self._pending_deliveries()
            self._dispatch(deliveries)

    def publish_invariant_projection(self, projection):
        self._require_genesis_anchor()
        normalized = self._normalize_projection(projection)
        with self._lock:
            if not self._has_projection or normalized != self._projection:
                self._projection_revision += 1
                self._projection = normalized
                self._has_projection = True
                self._release = None
                self._delivered.clear()
            self._evaluate()
            release = self._release
            deliveries = self._pending_deliveries()
            self._dispatch(deliveries)
            return release

    def publish_accumulated_symbol(self, symbol):
        self._require_genesis_anchor()
        normalized = self._copy_json_value(symbol)
        with self._lock:
            if not self._has_symbol or normalized != self._symbol:
                self._symbol_revision += 1
                self._symbol = normalized
                self._has_symbol = True
                self._release = None
                self._delivered.clear()
            self._evaluate()
            release = self._release
            deliveries = self._pending_deliveries()
            self._dispatch(deliveries)
            return release

    def _require_genesis_anchor(self):
        with self._lock:
            if (self._genesis_anchor is None
                    or self._genesis_distributed != set(self.instance_ids)):
                raise RuntimeError(
                    "both Sentinel Dot instances must receive the Genesis anchor first"
                )

    def _normalize_projection(self, projection):
        if isinstance(projection, ParabolaProjection):
            values = (projection.a, projection.b, projection.c,
                      projection.x_min, projection.x_max, projection.tolerance)
            if (any(type(value) not in (int, float) for value in values)
                    or any(math.isnan(value) for value in values)
                    or not all(math.isfinite(value) for value in values[:3])
                    or projection.x_min > projection.x_max
                    or not math.isfinite(projection.tolerance)
                    or projection.tolerance < 0):
                return None
            return projection
        if not isinstance(projection, dict):
            return None
        if "members" in projection:
            members = projection["members"]
            if not isinstance(members, (list, tuple)):
                return None
            try:
                return {"members": tuple(self._copy_json_value(value) for value in members)}
            except (TypeError, ValueError):
                return None
        if "symbol_hashes" in projection:
            hashes = projection["symbol_hashes"]
            if (not isinstance(hashes, (list, tuple, set))
                    or any(not isinstance(value, str) or len(value) != 128
                           or any(character not in "0123456789abcdefABCDEF"
                                  for character in value)
                           for value in hashes)):
                return None
            return {"symbol_hashes": frozenset(hashes)}
        if {"a", "b", "c"}.issubset(projection):
            try:
                parabola = ParabolaProjection(
                    projection["a"], projection["b"], projection["c"],
                    projection.get("x_min", -math.inf),
                    projection.get("x_max", math.inf),
                    projection.get("tolerance", 1e-9),
                )
            except (TypeError, ValueError):
                return None
            return self._normalize_projection(parabola)
        return None

    def _copy_json_value(self, value):
        try:
            encoded = json.dumps(
                value, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            return json.loads(encoded)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("published symbols must be finite JSON values") from exc

    def _contains(self, projection, symbol):
        if isinstance(projection, ParabolaProjection):
            return projection.contains(symbol)
        if "members" in projection:
            return symbol in projection["members"]
        digest = hashlib.sha512(
            json.dumps(
                symbol, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
        return digest in projection["symbol_hashes"]

    def _evaluate(self):
        if (self._genesis_anchor is None
                or self._genesis_distributed != set(self.instance_ids)):
            self._release = None
            self._last_validation = {
                "passed": False,
                "reason": "awaiting locked Genesis anchor",
            }
            return
        if not self._has_projection or not self._has_symbol:
            self._release = None
            self._last_validation = {
                "passed": False,
                "reason": "awaiting invariant projection and accumulated symbol",
            }
            return
        if self._projection is None:
            self._release = None
            self._last_validation = {
                "passed": False,
                "reason": "invalid invariant projection",
            }
            return
        try:
            valid = self._contains(self._projection, self._symbol)
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            self._release = None
            self._delivered.clear()
            self._last_validation = {
                "passed": False,
                "reason": "accumulated symbol is outside the invariant projection",
            }
            return
        if (self._release is not None
                and self._release.projection_revision == self._projection_revision
                and self._release.symbol_revision == self._symbol_revision):
            return
        self._release = ValidationRelease(
            projection_revision=self._projection_revision,
            symbol_revision=self._symbol_revision,
            block_id=hashlib.sha512(os.urandom(64)).hexdigest(),
            genesis_block_id=self._genesis_anchor.block_id,
        )
        self._delivered.clear()
        self._last_validation = {
            "passed": True,
            "reason": "accumulated symbol satisfies invariant projection",
        }

    def _pending_deliveries(self):
        if self._release is None:
            return ()
        pending = []
        for instance_id in self.instance_ids:
            callback = self._listeners.get(instance_id)
            if callback is not None and instance_id not in self._delivered:
                self._delivered.add(instance_id)
                pending.append((callback, self._release))
        return tuple(pending)

    @staticmethod
    def _dispatch(deliveries):
        for callback, release in deliveries:
            callback(release)

    def accepts_release(self, release, instance_id):
        with self._lock:
            return (
                release is self._release
                and instance_id in self.instance_ids
                and self._last_validation["passed"]
            )

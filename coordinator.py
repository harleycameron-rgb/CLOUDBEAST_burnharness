"""Bootstrap Sentinel Dot from a shared Genesis anchor, then validate
asymmetric state and emit gate-release events."""

import hashlib
import json
import math
import statistics
import threading
import time
from dataclasses import dataclass

GENESIS_TIMEOUT_SECONDS = 5.0


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
class GenesisBlock:
    block_id: str
    invariant_source_id: str
    symbol_source_id: str


@dataclass(frozen=True)
class ValidationRelease:
    projection_revision: int
    symbol_revision: int
    block_id: str
    gate_released: bool = True
    genesis_block_id: str = None


class GenesisBootstrapError(RuntimeError):
    """Raised when the one-time Genesis rendezvous cannot complete."""


def assert_genesis_uniform(coordinator, stubs):
    stubs = tuple(stubs)
    records = [stub.genesis_record for stub in stubs]
    if any(record is not None for record in records) and any(
        record is None for record in records
    ):
        raise AssertionError("Sentinel Dot instances have partially seeded Genesis")
    genesis = coordinator.genesis
    if genesis is not None and any(
        stub.genesis_block_id != genesis.block_id for stub in stubs
    ):
        raise AssertionError("Sentinel Dot instances do not share the Genesis anchor")


class SentinelDotCoordinator:
    """Non-blocking validation gate for an invariant source and a symbol stream."""

    def __init__(self, instance_ids=("sentinel-a", "sentinel-b")):
        if (len(instance_ids) != 2 or len(set(instance_ids)) != 2
                or any(not isinstance(value, str) or not value
                       for value in instance_ids)):
            raise ValueError("exactly two distinct Sentinel Dot instance IDs are required")
        self.invariant_source_id, self.symbol_source_id = tuple(instance_ids)
        self.instance_ids = tuple(instance_ids)
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
        self._genesis = None
        self._genesis_listeners = {}
        self._genesis_ready = set()
        self._genesis_distributed = frozenset()
        self._genesis_lock = threading.RLock()
        self._genesis_barrier = threading.Barrier(
            len(self.instance_ids), action=self._mint_and_distribute_genesis
        )

    @property
    def genesis(self):
        with self._genesis_lock:
            return self._genesis

    @property
    def genesis_anchor_locked(self):
        with self._genesis_lock:
            return (
                self._genesis is not None
                and self._genesis_distributed == frozenset(self.instance_ids)
            )

    def subscribe_genesis(self, instance_id, callback):
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        if not callable(callback):
            raise TypeError("genesis callback must be callable")
        with self._genesis_lock:
            self._genesis_listeners[instance_id] = callback
            genesis = self._genesis
        if genesis is not None:
            callback(genesis)

    def enter_genesis(self, instance_id, timeout=GENESIS_TIMEOUT_SECONDS):
        """Phase 1: one-time symmetric rendezvous; blocks until both are Ready."""
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        with self._genesis_lock:
            if self._genesis is not None:
                raise GenesisBootstrapError("Genesis bootstrap is one-time only")
            if instance_id in self._genesis_ready:
                raise GenesisBootstrapError(
                    f"Sentinel Dot instance already reported Ready: {instance_id!r}"
                )
            self._genesis_ready.add(instance_id)
        try:
            self._genesis_barrier.wait(timeout)
        except threading.BrokenBarrierError as exc:
            raise GenesisBootstrapError(
                "Genesis rendezvous failed before both instances were Ready"
            ) from exc
        if not self.genesis_anchor_locked:
            raise GenesisBootstrapError("Genesis anchor was not distributed")
        return self._genesis

    def _mint_and_distribute_genesis(self):
        with self._genesis_lock:
            try:
                if self._genesis_ready != set(self.instance_ids):
                    raise GenesisBootstrapError(
                        "both Sentinel Dot instances must be Ready"
                    )
                missing = [
                    instance_id for instance_id in self.instance_ids
                    if instance_id not in self._genesis_listeners
                ]
                if missing:
                    raise GenesisBootstrapError(
                        f"Sentinel Dot instances not bound for Genesis: {missing!r}"
                    )
                genesis = GenesisBlock(
                    block_id=hashlib.sha512(
                        json.dumps(
                            ["burnharness.genesis/1", *self.instance_ids],
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ).encode("utf-8")
                    ).hexdigest(),
                    invariant_source_id=self.invariant_source_id,
                    symbol_source_id=self.symbol_source_id,
                )
                listeners = [
                    self._genesis_listeners[instance_id]
                    for instance_id in self.instance_ids
                ]
                self._genesis = genesis
                self._genesis_distributed = frozenset(self.instance_ids)
                for callback in listeners:
                    callback(genesis)
                assert_genesis_uniform(
                    self,
                    (
                        getattr(callback, "__self__", None)
                        for callback in listeners
                        if getattr(callback, "__self__", None) is not None
                    ),
                )
            except Exception:
                self._genesis = None
                self._genesis_distributed = frozenset()
                for callback in self._genesis_listeners.values():
                    stub = getattr(callback, "__self__", None)
                    if stub is not None and hasattr(stub, "_genesis_record"):
                        stub._genesis_record = None
                self._genesis_ready.clear()
                raise

    def _require_genesis(self):
        if not self.genesis_anchor_locked:
            raise RuntimeError(
                "Genesis anchor must be locked before runtime validation"
            )

    @property
    def state(self):
        passed = self._release is not None
        return {
            "sync_mechanism_active": True,
            "sync_mode": "ASYMMETRIC_VALIDATION",
            "validation_passed": passed,
            "gate_released": passed,
            "superposition_integrity": passed,
            "no_bung": True,
            "continuity_flow": True,
            "genesis_anchor_locked": self.genesis_anchor_locked,
            "genesis_block_id": (
                None if self._genesis is None else self._genesis.block_id
            ),
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
        return self._release

    def subscribe(self, instance_id, callback):
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        if not callable(callback):
            raise TypeError("gate event callback must be callable")
        self._listeners[instance_id] = callback
        deliveries = self._pending_deliveries()
        self._dispatch(deliveries)

    def publish_invariant_projection(self, projection):
        self._require_genesis()
        normalized = self._normalize_projection(projection)
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
        self._require_genesis()
        normalized = self._copy_json_value(symbol)
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
            block_id=hashlib.sha512(
                (
                    f"burnharness.release/1:{self._genesis.block_id}:"
                    f"{self._projection_revision}:{self._symbol_revision}"
                ).encode("utf-8")
            ).hexdigest(),
            genesis_block_id=self._genesis.block_id,
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
        return (
            release is self._release
            and instance_id in self.instance_ids
            and self._last_validation["passed"]
            and self.genesis_anchor_locked
            and release.genesis_block_id == self._genesis.block_id
        )


def bootstrap_genesis(coordinator, timeout=GENESIS_TIMEOUT_SECONDS):
    """Run both Sentinel Dot Genesis rendezvous calls concurrently."""
    results = {}
    errors = []

    def enter(instance_id):
        try:
            results[instance_id] = coordinator.enter_genesis(instance_id, timeout)
        except Exception as exc:  # propagated to the caller below
            errors.append(exc)

    threads = [
        threading.Thread(target=enter, args=(instance_id,), daemon=True)
        for instance_id in coordinator.instance_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout + 1.0)
    if errors:
        if coordinator.genesis is None:
            coordinator._genesis_barrier.reset()
        raise errors[0]
    if any(thread.is_alive() for thread in threads):
        raise GenesisBootstrapError("Genesis rendezvous did not complete")
    return coordinator.genesis


def benchmark_genesis_bootstrap(iterations=200):
    """Return Genesis bootstrap timings in milliseconds."""
    from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import (
        SentinelDotIgnitionStub,
    )

    samples = []
    for _ in range(iterations):
        coordinator = SentinelDotCoordinator()
        for instance_id in coordinator.instance_ids:
            SentinelDotIgnitionStub().bind(coordinator, instance_id)
        start = time.perf_counter()
        bootstrap_genesis(coordinator)
        samples.append((time.perf_counter() - start) * 1000.0)
    ordered = sorted(samples)
    return {
        "iterations": iterations,
        "mean_ms": statistics.fmean(samples),
        "median_ms": statistics.median(samples),
        "p95_ms": ordered[max(0, math.ceil(0.95 * iterations) - 1)],
        "max_ms": ordered[-1],
    }


if __name__ == "__main__":
    print("Genesis bootstrap benchmark:")
    print(benchmark_genesis_bootstrap())

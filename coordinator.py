"""Coordinate a one-shot release for two Sentinel Dot instances."""

import hashlib
import os
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class BarrierRelease:
    participants: tuple
    block_id: str
    barrier_released: bool = True


class SentinelDotCoordinator:
    def __init__(self, instance_ids=("sentinel-1", "sentinel-2")):
        if (len(instance_ids) != 2 or len(set(instance_ids)) != 2
                or any(not isinstance(value, str) or not value
                       for value in instance_ids)):
            raise ValueError("exactly two distinct Sentinel Dot instance IDs are required")
        self.instance_ids = tuple(instance_ids)
        self._condition = threading.Condition()
        self._ready = set()
        self._release = None
        self._failure = None

    @property
    def state(self):
        with self._condition:
            released = self._release is not None
            return {
                "sync_mechanism_active": True,
                "barrier_blocking": True,
                "barrier_released": released,
                "superposition_integrity": (
                    released and self._ready == set(self.instance_ids)
                ),
                "no_bung": True,
                "continuity_flow": True,
                "frozen_modules": (),
                "ready_instances": tuple(
                    name for name in self.instance_ids if name in self._ready
                ),
                "blocked_instances": (
                    tuple(name for name in self.instance_ids if name in self._ready)
                    if not released else ()
                ),
            }

    def report_alignment(
        self, instance_id, *, p_i, p_j, a_i, a_j, timeout=None
    ):
        if (p_i is None or p_j is None or a_i is None or a_j is None
                or p_i != p_j or a_i != a_j):
            return None
        return self.report_ready(instance_id, timeout=timeout)

    def report_ready(self, instance_id, timeout=None):
        if instance_id not in self.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            if self._failure is not None:
                raise TimeoutError("Sentinel Dot barrier failed") from self._failure
            if self._release is not None:
                return self._release
            self._ready.add(instance_id)
            if self._ready == set(self.instance_ids):
                block_id = hashlib.sha512(os.urandom(64)).hexdigest()
                self._release = BarrierRelease(self.instance_ids, block_id)
                self._condition.notify_all()
                return self._release

            while self._release is None and self._failure is None:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    self._failure = TimeoutError(
                        "both Sentinel Dot instances did not become ready"
                    )
                    self._condition.notify_all()
                    break
                self._condition.wait(remaining)
            if self._failure is not None:
                raise TimeoutError("Sentinel Dot barrier failed") from self._failure
            return self._release

    def accepts_release(self, release, instance_id):
        with self._condition:
            return (
                release is self._release
                and instance_id in self.instance_ids
                and self._ready == set(self.instance_ids)
            )

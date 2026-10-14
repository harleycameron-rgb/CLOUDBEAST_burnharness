"""Detect sentinel drift across agent runs."""

from .stabiliser import verify_sentinel


class AgentValidator:
    def __init__(self):
        self.last_sentinel = None

    def validate(self, sentinel):
        verify_sentinel(sentinel)
        if self.last_sentinel is None:
            self.last_sentinel = sentinel
            return True
        if sentinel != self.last_sentinel:
            raise RuntimeError("Sentinel drift detected")
        return True

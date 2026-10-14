"""In-memory adapter for actions submitted as Python mappings."""

import json

from .orchestrator import Orchestrator


class WaxtabletAdapter:
    def __init__(self):
        self.orch = Orchestrator()

    def initialise(self):
        return {
            "waxtablet_runtime": "initialised",
            "engine": self.orch.initialise(),
        }

    def handle(self, payload):
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")
        action = payload.get("action")
        if action == "run":
            return self.orch.run_full_engine()
        if action == "benchmark":
            data = payload.get("data")
            if data is None:
                return {"error": "benchmark requires data"}
            self.orch.load_benchmark_data(data)
            return self.orch.run_benchmark()
        if action == "harmonic":
            return self.orch.harmonic_cycle()
        return {"error": f"unknown action {action!r}"}

    def encode(self, response):
        return json.dumps(response, sort_keys=True, separators=(",", ":"), allow_nan=False)

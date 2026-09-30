# ---------------------------------------------------------
# Organism Runtime
# Executes the full Burnharness engine loop:
#   - ignition layer
#   - leg generation
#   - coupler cycle
#   - drift tracking
#   - resonance stabilisation
#   - organism pulse emission
# ---------------------------------------------------------

import time
import importlib

CYCLE_PATH = "coupler_cycle"

class OrganismRuntime:
    def __init__(self, tick_rate=1.0):
        self.tick_rate = tick_rate
        self.cycle = self._load_cycle()
        self.previous_field = None
        self.drift_history = []

    def _load_cycle(self):
        module = importlib.import_module(CYCLE_PATH)
        return module.run_cycle

    def _compute_drift(self, current, previous):
        if previous is None:
            return 0.0

        drift = (
            abs(current["stability"] - previous["stability"]) +
            abs(current["curvature"] - previous["curvature"]) +
            abs(current["provenance"] - previous["provenance"])
        ) / 3.0

        return drift

    def _stabilise(self, field, drift):
        # Simple stabiliser: reduce wobble if drift spikes
        if drift > 0.05:
            field["stability"] *= 0.98
            field["curvature"] *= 0.98
        return field

    def tick(self):
        current_field = self.cycle()
        drift = self._compute_drift(current_field, self.previous_field)

        self.drift_history.append(drift)
        current_field = self._stabilise(current_field, drift)

        self.previous_field = current_field

        return {
            "pulse": current_field,
            "drift": drift
        }

    def run(self, ticks=10):
        print("Organism Runtime Starting...")
        for i in range(ticks):
            output = self.tick()
            print(f"[Tick {i}] Pulse={output['pulse']} Drift={output['drift']}")
            time.sleep(self.tick_rate)
        print("Organism Runtime Complete.")
        return self.drift_history


if __name__ == "__main__":
    runtime = OrganismRuntime(tick_rate=0.5)
    runtime.run(ticks=12)

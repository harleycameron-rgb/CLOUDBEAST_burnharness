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

from burnharness_protocol import PROTOCOL

CYCLE_PATH = "coupler_cycle"

class OrganismRuntime:
    def __init__(self, tick_rate=1.0):
        self.tick_rate = tick_rate
        self.cycle = self._load_cycle()
        self.previous_field = None
        self.drift_history = []
        self.halted = False

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
        stabilised = dict(field)
        if drift > PROTOCOL["oath_protocol"]["friction_threshold"]:
            stabilised["stability"] *= 0.98
            stabilised["curvature"] *= 0.98
        return stabilised

    def tick(self):
        if self.halted:
            return {
                "pulse": None,
                "drift": None,
                "halted": True,
                "fallback_stub": PROTOCOL["ai_entry_gate"]["sandbox_on_failure"],
            }

        current_field = self.cycle()
        drift = self._compute_drift(current_field, self.previous_field)

        self.drift_history.append(drift)
        current_field = self._stabilise(current_field, drift)
        self.previous_field = current_field

        output = {
            "pulse": current_field,
            "drift": drift,
            "halted": drift > PROTOCOL["oath_protocol"]["friction_threshold"],
        }
        if output["halted"]:
            self.halted = True
            output["fallback_stub"] = (
                PROTOCOL["drift_targeting"]["route_to_stub_on_drift"]
            )
        return output

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

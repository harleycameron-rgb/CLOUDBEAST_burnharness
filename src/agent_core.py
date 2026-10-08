"""Cloudburner agent with deterministic, guarded in-memory execution."""

from .autonomy import autonomous_cycle, invariant_loop, self_verify
from .harmony import align_modules, smooth_residue, unify_lambdas
from .stabiliser import (
    enforce_zero_data,
    harmonise_state,
    stabilise_step,
    verify_sentinel,
)
from .supervisor import Supervisor


class CloudburnerAgent:
    def __init__(self):
        self.supervisor = Supervisor()
        self.state = []
        self.sentinel = None
        self._initialised = False

    def initialise(self):
        if self._initialised:
            return {"status": "initialised"}
        self.supervisor.add_step(
            "burn",
            action=lambda: {"lambda_updated": [0.55, 0.77]},
            verify=lambda output: (
                isinstance(output, dict) and "lambda_updated" in output
            ),
        )
        self.supervisor.add_step(
            "ignite",
            action=lambda: {
                "InvariantEngine": {"sound": [1, 2, 3], "lambda": [0.5, 0.7]}
            },
            verify=lambda output: (
                isinstance(output, dict) and "InvariantEngine" in output
            ),
        )
        self.supervisor.add_step(
            "residue",
            action=lambda: (6.0, "mapping-definition-6"),
            verify=lambda output: (
                isinstance(output, (tuple, list))
                and bool(output)
                and type(output[0]) in (int, float)
            ),
        )
        self._initialised = True
        return {"status": "initialised"}

    def execute(self):
        if not self._initialised:
            raise RuntimeError("agent must be initialised before execution")
        results = []
        with enforce_zero_data():
            for step in ("burn", "ignite", "residue"):
                result = self.supervisor.run(step, "y")
                stabilise_step(step, result)
                results.append(result)
            harmonise_state(results)
            self.sentinel = self.supervisor.residue()["sentinel"]
            verify_sentinel(self.sentinel)
        self.state.extend(results)
        return {"status": "complete", "sentinel": self.sentinel}

    def autonomous_mode(self):
        if not self._initialised:
            raise RuntimeError("agent must be initialised before autonomous execution")
        with enforce_zero_data():
            autonomous_cycle(self.supervisor)
            invariant_loop()
            return self_verify()

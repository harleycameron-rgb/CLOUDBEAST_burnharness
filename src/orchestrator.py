"""In-memory orchestration of the agent and optional benchmark."""

from .agent_core import CloudburnerAgent
from .autonomy import autonomous_cycle, invariant_loop, self_verify
from .benchmark_agent import BenchmarkAgent
from .stabiliser import enforce_zero_data, harmonise_state, verify_sentinel


class Orchestrator:
    def __init__(self):
        self.agent = CloudburnerAgent()
        self.benchmark = None
        self.state_log = []
        self.sentinel = None

    def initialise(self):
        return self.agent.initialise()

    def run_agent(self):
        result = self.agent.execute()
        self.state_log.append(result)
        self.sentinel = result["sentinel"]
        verify_sentinel(self.sentinel)
        return result

    def load_benchmark_data(self, data):
        self.benchmark = BenchmarkAgent(data)

    def run_benchmark(self):
        if self.benchmark is None:
            raise RuntimeError("Benchmark data not loaded")
        results = self.benchmark.run()
        leakage = self.benchmark.worst_case_leakage()
        self.state_log.append({
            "benchmark_results": results,
            "worst_case_leakage": leakage,
        })
        return {"benchmark": "complete", "worst_case_leakage": leakage}

    def harmonic_cycle(self):
        if not self.agent._initialised:
            raise RuntimeError("agent must be initialised before harmonic execution")
        with enforce_zero_data():
            autonomous_cycle(self.agent.supervisor)
            invariant_loop()
            self_verify()
        return {"harmonic_state": harmonise_state(self.state_log)}

    def run_full_engine(self):
        out_agent = self.run_agent()
        out_benchmark = self.run_benchmark() if self.benchmark is not None else None
        out_harmonic = self.harmonic_cycle()
        verify_sentinel(self.sentinel)
        return {
            "agent": out_agent,
            "benchmark": out_benchmark,
            "harmonic": out_harmonic,
            "sentinel": self.sentinel,
        }

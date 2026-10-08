import unittest

import numpy as np

from src.agent_core import CloudburnerAgent
from src.agent_interface import AgentInterface
from src.agent_memory import AgentMemory
from src.agent_validator import AgentValidator
from src.benchmark_agent import BenchmarkAgent, compute_benchmark_row, phi
from src.waxtablet_adapter import WaxtabletAdapter
from zero_data import FileIOViolation, forbid_file_io


class AgentRuntimeTests(unittest.TestCase):
    def test_agent_sentinel_is_reproducible_and_guard_is_active(self):
        agents = [CloudburnerAgent(), CloudburnerAgent()]
        outputs = []
        for agent in agents:
            agent.initialise()
            outputs.append(agent.execute())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(len(outputs[0]["sentinel"]), 12)
        with self.assertRaises(FileIOViolation):
            with forbid_file_io():
                open("blocked-by-agent-test.txt", "w")

    def test_agent_requires_initialisation(self):
        with self.assertRaises(RuntimeError):
            CloudburnerAgent().execute()

    def test_benchmark_outputs_are_finite_and_repeatable_without_global_rng_change(self):
        row = {"x_params": [1, 2, 3], "p_params": [0.2, 0.4, 0.6]}
        state_before = np.random.get_state()
        first = compute_benchmark_row(row, seed=21)
        second = compute_benchmark_row(row, seed=21)
        state_after = np.random.get_state()
        self.assertEqual(first, second)
        self.assertTrue(np.array_equal(state_before[1], state_after[1]))
        self.assertEqual(state_before[2:], state_after[2:])
        with self.assertRaises(ValueError):
            phi([0, 0, 0])

    def test_benchmark_agent_accepts_in_memory_records(self):
        benchmark = BenchmarkAgent([
            {"x_params": [1, 0, 0], "p_params": [0.2, 0.3, 0.4]},
            {"x_params": [0, 1, 1], "p_params": [0.1, 0.2, 0.3]},
        ])
        results = benchmark.run()
        self.assertEqual(len(results), 2)
        self.assertGreaterEqual(benchmark.worst_case_leakage(), 0)
        with self.assertRaises(RuntimeError):
            BenchmarkAgent([]).worst_case_leakage()

    def test_orchestrator_interface_and_adapter(self):
        interface = AgentInterface()
        self.assertEqual(interface.initialise(), {"status": "initialised"})
        output = interface.run()
        self.assertEqual(output["sentinel"], output["agent"]["sentinel"])
        adapter = WaxtabletAdapter()
        adapter.initialise()
        self.assertEqual(
            adapter.handle({"action": "benchmark"}),
            {"error": "benchmark requires data"},
        )
        self.assertIn("sentinel", adapter.handle({"action": "run"}))
        self.assertIn("sentinel", adapter.encode(adapter.orch.run_full_engine()))

    def test_memory_and_validator(self):
        memory = AgentMemory()
        self.assertIsNone(memory.pull())
        memory.push({"value": 1})
        self.assertEqual(memory.pull(), {"value": 1})
        memory.push(2)
        memory.clear()
        self.assertIsNone(memory.pull())

        validator = AgentValidator()
        self.assertTrue(validator.validate("0123456789ab"))
        self.assertTrue(validator.validate("0123456789ab"))
        with self.assertRaises(RuntimeError):
            validator.validate("abcdef012345")
        with self.assertRaises(ValueError):
            AgentValidator().validate("invalid")


if __name__ == "__main__":
    unittest.main()

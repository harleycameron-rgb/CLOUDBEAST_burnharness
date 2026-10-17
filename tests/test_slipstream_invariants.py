import math
import unittest

from src.slipstream import Interface, Module, Slipstream, rot


class SlipstreamInvariantTests(unittest.TestCase):
    def test_shared_lambda_positive(self):
        lam = math.log(2)
        m = Module(
            'A', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([m], lam=lam)
        self.assertIs(ss.shared_lambda(), True)

    def test_relative_sizes_preserved(self):
        lam = math.log(2)
        times = [0, 1, 2, 3]
        A = Module(
            'A', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        B = Module(
            'B', u=(0, 0), d0=0.5,
            gamma=lambda t: (t, 1),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([A, B], lam=lam)
        self.assertTrue(ss.relative_sizes_preserved(times))

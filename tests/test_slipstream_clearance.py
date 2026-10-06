import math
import unittest

from src.slipstream import Interface, Module, Slipstream, rot


class SlipstreamClearanceTests(unittest.TestCase):
    def test_clearance_positive(self):
        times = [0, 1, 2]
        lam = math.log(2)
        A = Module(
            'A', u=(0.2, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        B = Module(
            'B', u=(0.1, 0), d0=0.5,
            gamma=lambda t: (t, 1),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([A, B], lam=lam)
        self.assertTrue(ss.clearance_ok(0, 1, times))

    def test_clearance_violation(self):
        times = [0, 1, 2]
        lam = math.log(2)
        A = Module(
            'A', u=(0.2, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        E = Module(
            'E', u=(0.2, 0), d0=1.0,
            gamma=lambda t: (t, 0),  # same path → collision
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([A, E], lam=lam)
        self.assertIs(ss.clearance_ok(0, 1, times), False)

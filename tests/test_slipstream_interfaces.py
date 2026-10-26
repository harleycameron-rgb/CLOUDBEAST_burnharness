import math
import unittest

from src.slipstream import Interface, Module, Slipstream, rot


class SlipstreamInterfaceTests(unittest.TestCase):
    def test_interface_match(self):
        A = Module(
            'A', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float', 'confidence': 'float'}),
        )
        B = Module(
            'B', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 1),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([A, B], lam=math.log(2))
        iface = ss.interfaces_compatible(0, 1)
        self.assertIs(iface['ok'], True)
        self.assertEqual(iface['mismatchedTypes'], [])

    def test_interface_mismatch(self):
        A = Module(
            'A', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        D = Module(
            'D', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 2),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'string'}),
        )
        ss = Slipstream([A, D], lam=math.log(2))
        iface = ss.interfaces_compatible(0, 1)
        self.assertIs(iface['ok'], False)
        self.assertEqual(iface['mismatchedTypes'], ['hz'])

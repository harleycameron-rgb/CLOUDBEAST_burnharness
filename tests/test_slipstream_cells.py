import math
import unittest

from src.slipstream import Interface, Module, Slipstream, Tessellation, rot


class SlipstreamCellTests(unittest.TestCase):
    def test_cells_distinct(self):
        times = [0, 1, 2]
        lam = math.log(2)
        A = Module(
            'A', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        B = Module(
            'B', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 2),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([A, B], lam=lam, tess=Tessellation(cell_size=1.0))
        self.assertTrue(ss.cells_distinct(times))

    def test_cells_collision(self):
        times = [0, 1, 2]
        lam = math.log(2)
        A = Module(
            'A', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        C = Module(
            'C', u=(0, 0), d0=1.0,
            gamma=lambda t: (t, 0),  # same cell
            R=lambda t: rot(0),
            interface=Interface({'hz': 'float'}),
        )
        ss = Slipstream([A, C], lam=lam, tess=Tessellation(cell_size=1.0))
        self.assertIs(ss.cells_distinct(times), False)

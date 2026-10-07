"""Small deterministic geometry primitives for the Slipstream invariant tests."""

import math
from dataclasses import dataclass


def rot(angle):
    if isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(angle):
        raise ValueError("rotation angle must be finite")
    cosine, sine = math.cos(angle), math.sin(angle)
    return ((cosine, -sine), (sine, cosine))


@dataclass(frozen=True)
class Interface:
    fields: dict

    def __post_init__(self):
        if (not isinstance(self.fields, dict)
                or any(not isinstance(name, str) or not isinstance(kind, str)
                       for name, kind in self.fields.items())):
            raise ValueError("interface fields must map string names to string types")


@dataclass(frozen=True)
class Module:
    name: str
    u: tuple
    d0: float
    gamma: object
    R: object
    interface: Interface

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("module name must be a non-empty string")
        if (not isinstance(self.u, (tuple, list)) or len(self.u) != 2
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in self.u)):
            raise ValueError("module offset must be a finite 2-vector")
        if type(self.d0) not in (int, float) or not math.isfinite(self.d0) or self.d0 < 0:
            raise ValueError("module base size must be finite and non-negative")
        if not callable(self.gamma) or not callable(self.R):
            raise TypeError("module trajectory and rotation must be callable")
        if not isinstance(self.interface, Interface):
            raise TypeError("module interface must be an Interface")


@dataclass(frozen=True)
class Tessellation:
    cell_size: float = 1.0

    def __post_init__(self):
        if (type(self.cell_size) not in (int, float)
                or not math.isfinite(self.cell_size) or self.cell_size <= 0):
            raise ValueError("cell_size must be finite and positive")

    def cell(self, point):
        return tuple(math.floor(coordinate / self.cell_size) for coordinate in point)


class Slipstream:
    def __init__(self, modules, lam, tess=None):
        self.modules = tuple(modules)
        if not self.modules or any(not isinstance(module, Module) for module in self.modules):
            raise ValueError("Slipstream requires one or more Module instances")
        if type(lam) not in (int, float) or not math.isfinite(lam):
            raise ValueError("shared lambda must be finite")
        self.lam = float(lam)
        self.tess = tess if tess is not None else Tessellation()
        if not isinstance(self.tess, Tessellation):
            raise TypeError("tess must be a Tessellation")

    def shared_lambda(self):
        return math.isfinite(self.lam) and self.lam > 0

    def _center(self, module, time):
        point = module.gamma(time)
        matrix = module.R(time)
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in point)
                or not isinstance(matrix, (list, tuple)) or len(matrix) != 2
                or any(not isinstance(row, (list, tuple)) or len(row) != 2
                       or any(type(value) not in (int, float)
                              or not math.isfinite(value) for value in row)
                       for row in matrix)):
            raise ValueError("trajectory and rotation must produce finite 2D values")
        scale = math.exp(self.lam * time)
        return tuple(
            sum(matrix[i][j] * point[j] for j in range(2))
            + scale * module.u[i]
            for i in range(2)
        )

    def interfaces_compatible(self, first, second):
        left, right = self.modules[first].interface.fields, self.modules[second].interface.fields
        mismatched = sorted(
            name for name in left.keys() & right.keys()
            if left[name] != right[name]
        )
        return {"ok": not mismatched, "mismatchedTypes": mismatched}

    def cells_distinct(self, times):
        for time in times:
            occupied = set()
            for module in self.modules:
                cell = self.tess.cell(self._center(module, time))
                if cell in occupied:
                    return False
                occupied.add(cell)
        return True

    def clearance_ok(self, first, second, times):
        left, right = self.modules[first], self.modules[second]
        threshold = (left.d0 * math.hypot(*left.u)
                     + right.d0 * math.hypot(*right.u))
        for time in times:
            a, b = self._center(left, time), self._center(right, time)
            if math.dist(a, b) <= threshold:
                return False
        return True

    def relative_sizes_preserved(self, times):
        if not times:
            return False
        baseline = None
        for time in times:
            scale = math.exp(self.lam * time)
            sizes = tuple(module.d0 * scale for module in self.modules)
            ratios = tuple(
                size / sizes[0] if sizes[0] else (0.0 if size == 0 else math.inf)
                for size in sizes
            )
            if baseline is None:
                baseline = ratios
            elif ratios != baseline:
                return False
        return True

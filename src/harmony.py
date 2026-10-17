"""Small deterministic helpers for aligning agent state."""

import math


def align_modules(modules):
    if any(not isinstance(module, dict) for module in modules):
        raise TypeError("modules must contain dictionaries")
    return sorted(modules, key=lambda module: module.get("name", ""))


def unify_lambdas(lambda_values):
    values = list(lambda_values)
    if any(type(value) not in (int, float) or not math.isfinite(value)
           for value in values):
        raise ValueError("lambda values must be finite numbers")
    return [round(value, 3) for value in values]


def smooth_residue(residue):
    if (not isinstance(residue, (tuple, list)) or not residue
            or type(residue[0]) not in (int, float)
            or not math.isfinite(residue[0])):
        raise ValueError("residue must begin with a finite number")
    return round(residue[0], 2)

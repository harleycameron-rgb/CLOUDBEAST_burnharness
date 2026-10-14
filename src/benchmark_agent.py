"""Finite and reproducible geometric benchmark calculations."""

import math

import numpy as np


def _vector(values, name):
    vector = np.asarray(values, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError(f"{name} must be a finite 3-vector")
    return vector


def phi(x):
    vector = _vector(x, "x")
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("x must be non-zero")
    return vector / norm


def A(p):
    return np.diag(_vector(p, "p"))


def G(state):
    vector = _vector(state, "state")
    return vector[:2]


def F(z, u):
    point = np.asarray(z, dtype=float)
    vector = np.asarray(u, dtype=float)
    if (point.shape != (2,) or vector.shape != (3,)
            or not np.isfinite(point).all() or not np.isfinite(vector).all()):
        raise ValueError("flow inputs must be a finite 2-vector and 3-vector")
    return np.array([point[0] * vector[0], point[1] * vector[1], 0.0])


def parabolic_step_down(state, target, control_offset=0.7, t=1.0):
    start = _vector(state, "state")
    endpoint = np.asarray(target, dtype=float)
    if (endpoint.ndim != 1 or endpoint.size > 3
            or not np.isfinite(endpoint).all()
            or type(control_offset) not in (int, float)
            or not math.isfinite(control_offset)
            or type(t) not in (int, float) or not math.isfinite(t)):
        raise ValueError("parabolic path parameters must be finite")
    destination = start.copy()
    destination[:endpoint.size] = endpoint
    control = start + control_offset * (destination - start)
    return (1 - t) ** 2 * start + 2 * t * (1 - t) * control + t ** 2 * destination


def compute_benchmark_row(row, *, seed=0):
    try:
        x = row["x_params"]
        p = row["p_params"]
    except (KeyError, TypeError) as exc:
        raise ValueError("benchmark row requires x_params and p_params") from exc

    start = phi(x)
    tangent = (np.eye(3) - np.outer(start, start)) @ A(p) @ start
    perturbed = start + tangent
    norm = np.linalg.norm(perturbed)
    if not math.isfinite(float(norm)) or norm == 0:
        raise ValueError("benchmark perturbation must be non-zero and finite")
    shifted = perturbed / norm

    surface_distance = float(np.arccos(np.clip(start @ shifted, -1.0, 1.0)))
    start_surface = parabolic_step_down(start, start[:2])
    shifted_surface = parabolic_step_down(shifted, shifted[:2])
    start_core = G(start)
    shifted_core = G(shifted)
    core_distance = float(np.linalg.norm(shifted_core - start_core))

    rng = np.random.default_rng(seed)
    samples = rng.normal(size=(100, 3))
    lengths = np.linalg.norm(samples, axis=1, keepdims=True)
    samples = samples / lengths * rng.random((100, 1))
    flow_differences = np.array([
        np.linalg.norm(F(shifted_core, sample) - F(start_core, sample)) ** 2
        for sample in samples
    ])
    flow_distance = float(np.sqrt(np.mean(flow_differences)))

    return {
        "D_surface": surface_distance,
        "D_core": core_distance,
        "D_flow": flow_distance,
        "s0": start.tolist(),
        "sp": shifted.tolist(),
        "z0": start_core.tolist(),
        "zp": shifted_core.tolist(),
        "s0_surf": start_surface.tolist(),
        "sp_surf": shifted_surface.tolist(),
    }


class BenchmarkAgent:
    def __init__(self, data):
        self.data = data
        self.results = None

    def _records(self):
        if hasattr(self.data, "to_dict"):
            try:
                records = self.data.to_dict(orient="records")
            except TypeError as exc:
                raise ValueError("benchmark data must be a table of row mappings") from exc
        else:
            records = self.data
        if not isinstance(records, (list, tuple)) or not records:
            raise ValueError("benchmark data must contain one or more rows")
        if any(not isinstance(record, dict) for record in records):
            raise ValueError("each benchmark row must be a mapping")
        return records

    def run(self):
        self.results = [
            compute_benchmark_row(row, seed=index)
            for index, row in enumerate(self._records())
        ]
        return self.results

    def worst_case_leakage(self):
        if self.results is None:
            raise RuntimeError("benchmark has not been run")
        if not self.results:
            raise ValueError("benchmark results are empty")
        return max(result["D_core"] for result in self.results)

    def structural_control(self, x, x_prime):
        return float(np.linalg.norm(G(phi(x_prime)) - G(phi(x))))

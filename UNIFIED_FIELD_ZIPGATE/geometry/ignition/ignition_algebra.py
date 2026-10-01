"""Numerical helpers for the sphere-surface ignition algebra."""

import cmath
import math
from collections.abc import Mapping


def _finite_real(value):
    return type(value) in (int, float) and math.isfinite(value)


def harmonic_field(time, frequencies, phases):
    """Return the complex harmonic sum for corresponding frequencies/phases."""
    if not _finite_real(time):
        raise ValueError("time must be a finite number")
    if len(frequencies) != len(phases):
        raise ValueError("frequencies and phases must have the same length")
    if any(not _finite_real(value) for value in (*frequencies, *phases)):
        raise ValueError("frequencies and phases must be finite numbers")
    return sum(
        (cmath.exp(1j * (frequency * time + phase))
         for frequency, phase in zip(frequencies, phases)),
        0j,
    )


def ignition_time(phase_i, phase_j, frequency_i, frequency_j, cycle=0):
    """Return the pairwise phase-alignment time, or None for equal frequencies."""
    values = (phase_i, phase_j, frequency_i, frequency_j, cycle)
    if any(not _finite_real(value) for value in values):
        raise ValueError("phases, frequencies, and cycle must be finite numbers")
    frequency_delta = frequency_i - frequency_j
    if frequency_delta == 0:
        return None
    return (phase_j - phase_i + 2 * math.pi * cycle) / frequency_delta


def ignition_condition(surface_flow, core_velocity, tolerance):
    """Check the strict surface-flow/core-velocity alignment condition."""
    try:
        return (
            isinstance(tolerance, (int, float))
            and not isinstance(tolerance, bool)
            and math.isfinite(tolerance)
            and tolerance > 0
            and abs(surface_flow - core_velocity) < tolerance
        )
    except (TypeError, ValueError, OverflowError):
        return False


def _in_domain(value, domain):
    try:
        if callable(domain):
            return bool(domain(value))
        if isinstance(domain, tuple) and len(domain) == 2:
            return domain[0] <= value <= domain[1]
        return value in domain
    except (TypeError, ValueError, OverflowError):
        return False


def destiny_alignment(harmonic_value, destiny_domains):
    """Return whether the harmonic value belongs to every sphere's invariant."""
    return (
        isinstance(destiny_domains, Mapping)
        and bool(destiny_domains)
        and all(_in_domain(harmonic_value, domain)
                for domain in destiny_domains.values())
    )


def system_recurrence(
    coherence,
    minimum_coherence,
    core_positions,
    destiny_domains,
    harmonic_value,
):
    """Return the alliance recurrence bit, failing closed on incomplete inputs."""
    if (not _finite_real(coherence) or not _finite_real(minimum_coherence)
            or not isinstance(core_positions, Mapping)
            or not isinstance(destiny_domains, Mapping)
            or not core_positions
            or core_positions.keys() != destiny_domains.keys()):
        return 0
    if coherence <= minimum_coherence or not destiny_alignment(
        harmonic_value, destiny_domains
    ):
        return 0
    return int(all(
        _in_domain(position, destiny_domains[sphere])
        for sphere, position in core_positions.items()
    ))

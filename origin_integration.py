"""Opt-in development contracts; never substitutes local stubs for origins."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product
import math
import re
from typing import Callable, Protocol

from burnharness_protocol import (
    create_stabiliser_packet,
    propagate_stabiliser_packet,
)
from zero_data import FileIOViolation, forbid_file_io


LEGS = (
    "scandoc", "invariant_surface", "topology_engine",
    "waxtablet_engine", "orrery", "sentinel_dot",
)
FACE_NORMALS = {
    "+x": (1, 0, 0), "-x": (-1, 0, 0),
    "+y": (0, 1, 0), "-y": (0, -1, 0),
    "+z": (0, 0, 1), "-z": (0, 0, -1),
}
DEFAULT_FACES = dict(zip(LEGS, ("+x", "+y", "-x", "+z", "-y", "-z")))
GATES = (
    "origin_resolved", "pinned_clone_verified", "dependencies_available",
    "adapter_invoked", "declared_tests_passed", "packet_invariants_preserved",
    "containment_requirements_tested",
)


@dataclass(frozen=True)
class Origin:
    repository: str
    interface: str
    declaration: str
    commit: str = ""


@dataclass(frozen=True)
class Gate:
    status: str = "blocked"
    reason: str = "not executed"


@dataclass(frozen=True)
class CloneEvidence:
    repository: str
    commit: str
    verified: bool


class OriginAdapter(Protocol):
    """A reviewed upstream binding, preloaded before the filesystem guard."""

    def invoke(self, packet: Mapping, projection: tuple) -> Mapping:
        ...


@dataclass(frozen=True)
class Binding:
    origin: Origin
    clone: Callable[[Origin], CloneEvidence]
    dependencies: Callable[[CloneEvidence], bool]
    adapter: OriginAdapter
    declared_tests: Callable[[Mapping], bool]
    containment_tests: Callable[[], bool]


def resolve_origin(leg, declarations):
    """Resolve only supplied explicit declarations, never names or coordinates."""
    if leg not in LEGS:
        return None, Gate(reason="unknown leg")
    candidates = declarations.get(leg, ())
    if not candidates:
        return None, Gate(reason="no declared repository and upstream interface")
    if len(candidates) != 1:
        return None, Gate(reason="ambiguous origin declarations")
    origin = candidates[0]
    if (not isinstance(origin, Origin)
            or not all(isinstance(value, str) and value.strip()
                       for value in (origin.repository, origin.interface,
                                     origin.declaration))
            or (origin.commit and not _commit_id(origin.commit))):
        return None, Gate(reason="incomplete or invalid origin declaration")
    return origin, Gate("passed", "explicit declaration resolved")


def _commit_id(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value)


def cube_geometry(mapping=None):
    """Check the combinatorial boundary of an axis-aligned unit half-width cube."""
    mapping = DEFAULT_FACES if mapping is None else mapping
    if (set(mapping) != set(LEGS)
            or any(face not in FACE_NORMALS for face in mapping.values())
            or len(set(mapping.values())) != 6):
        return {"closed": False, "reason": "six legs require six distinct cube faces"}
    vertices = Counter()
    edges = Counter()
    corners = {}
    for leg, face in mapping.items():
        normal = FACE_NORMALS[face]
        axis = next(i for i, value in enumerate(normal) if value)
        points = {
            point for point in product((-1, 1), repeat=3)
            if point[axis] == normal[axis]
        }
        corners[leg] = points
        vertices.update(points)
        for a in points:
            for b in points:
                if a < b and sum(x != y for x, y in zip(a, b)) == 1:
                    edges[tuple(sorted((a, b)))] += 1
    adjacency = {
        leg: tuple(other for other in LEGS
                   if other != leg and len(corners[leg] & corners[other]) == 2)
        for leg in LEGS
    }
    closed = (
        len(vertices) == 8 and set(vertices.values()) == {3}
        and len(edges) == 12 and set(edges.values()) == {2}
        and len(vertices) - len(edges) + 6 == 2
        and all(len(neighbors) == 4 for neighbors in adjacency.values())
    )
    return {
        "closed": closed, "adjacency": adjacency,
        "face_centers": {leg: FACE_NORMALS[mapping[leg]] for leg in LEGS},
        "vertices": len(vertices), "edges": len(edges), "faces": 6,
    }


def project_sphere(direction):
    """Radially project a nonzero model direction onto the cube surface."""
    if (len(direction) != 3
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in direction)):
        raise ValueError("a finite three-dimensional direction is required")
    scale = max(abs(value) for value in direction)
    if not scale:
        raise ValueError("the sphere direction must be nonzero")
    return tuple(value / scale for value in direction)


def attempt_leg(leg, declarations, binding=None, *, allow_clone_retention=False,
                projection=(1, 0, 0)):
    """Return process-local evidence; callbacks are trusted development tools.

    Clone/dependency setup is outside runtime. No clone is permitted unless the
    caller explicitly accepts development source retention under its policy.
    Exceptions are reduced to types so private upstream traces are not exposed.
    """
    gates = {name: Gate() for name in GATES}
    origin, gates["origin_resolved"] = resolve_origin(leg, declarations)
    if origin is None:
        return gates
    if not allow_clone_retention:
        gates["pinned_clone_verified"] = Gate(
            reason="development clone retention not authorized; zero-data conflict"
        )
        return gates
    if binding is None or binding.origin != origin:
        gates["pinned_clone_verified"] = Gate(reason="no matching origin binding")
        return gates
    try:
        clone = binding.clone(origin)
        if (not isinstance(clone, CloneEvidence)
                or clone.repository != origin.repository
                or clone.verified is not True or not _commit_id(clone.commit)
                or (origin.commit and clone.commit != origin.commit)):
            gates["pinned_clone_verified"] = Gate("failed", "clone pin verification failed")
            return gates
        gates["pinned_clone_verified"] = Gate("passed", clone.commit)
        if binding.dependencies(clone) is not True:
            gates["dependencies_available"] = Gate(reason="dependencies unavailable")
            return gates
        gates["dependencies_available"] = Gate("passed", "dependency check executed")
    except Exception as exc:
        stage = ("dependencies_available"
                 if gates["pinned_clone_verified"].status == "passed"
                 else "pinned_clone_verified")
        gates[stage] = Gate("failed", type(exc).__name__)
        return gates
    if binding.adapter is None:
        gates["adapter_invoked"] = Gate(reason="upstream adapter unbound")
        return gates
    packet = create_stabiliser_packet()
    snapshot = dict(packet)
    try:
        with forbid_file_io():
            output = binding.adapter.invoke(packet, project_sphere(projection))
            gates["adapter_invoked"] = Gate("passed", "bound adapter returned")
            if (not isinstance(output, Mapping)
                    or output.get("stabiliser_packet") is not packet
                    or dict(packet) != snapshot):
                gates["packet_invariants_preserved"] = Gate("failed", "packet changed or missing")
                return gates
            propagate_stabiliser_packet(packet)
            gates["packet_invariants_preserved"] = Gate("passed", "identity and content preserved")
            checks = (
                ("declared_tests_passed", binding.declared_tests, (output,)),
                ("containment_requirements_tested", binding.containment_tests, ()),
            )
            for name, check, arguments in checks:
                try:
                    gates[name] = (
                        Gate("passed", "binding test callback executed")
                        if check(*arguments) is True
                        else Gate(reason="binding tests unavailable or unsuccessful")
                    )
                except FileIOViolation:
                    raise
                except Exception as exc:
                    gates[name] = Gate("failed", type(exc).__name__)
            if (output.get("stabiliser_packet") is not packet
                    or dict(packet) != snapshot):
                gates["packet_invariants_preserved"] = Gate(
                    "failed", "packet changed during test callbacks"
                )
            else:
                propagate_stabiliser_packet(packet)
    except Exception as exc:
        # Guard exit can fail even when the adapter swallows an I/O violation.
        gates["adapter_invoked"] = Gate("failed", type(exc).__name__)
        gates["containment_requirements_tested"] = Gate("failed", type(exc).__name__)
    return gates


def completion_report(evidence, mapping=None):
    """Aggregate every declared gate; closure alone cannot complete integration."""
    geometry = cube_geometry(mapping)
    complete = (
        geometry["closed"] and set(evidence) == set(LEGS)
        and all(set(evidence[leg]) == set(GATES)
                and all(isinstance(evidence[leg][gate], Gate)
                        and evidence[leg][gate].status == "passed"
                        for gate in GATES)
                for leg in LEGS)
    )
    return {
        "geometry": geometry, "development_gates_complete": complete,
        "production_launch_authorized": False,
        "legs": evidence,
    }

"""Governance and packet helpers for the unified Burnharness protocol."""

from collections.abc import Mapping


_PROTOCOL = {
    "oath_protocol": {
        "accuracy_before_satisfaction": True,
        "friction_threshold": 0.12,
        "gap_monitor": "active",
        "transparency_flag": True,
        "overstep_risk_named": True,
        "approval_signal_failure_mode_acknowledged": True,
    },
    "coupler_archetype": {
        "stabiliser_packet_mode": "READ_ONLY",
        "no_transformation_allowed": True,
        "friction_injection_required": True,
        "moire_gap_preservation": True,
        "geometry_header": "SPHERE_SURFACE_FLOW",
        "upgrade_condition": "OATH_PROTOCOL_ACTIVE",
    },
    "geometry_system": {
        "core_destination_geometry": "SOLAR_ORBIT_TRAJECTORY",
        "core_heading": "FIXED_SPHERE_CORE",
        "surface_geometry": "INVARIANT_TAP_FLOW",
        "surface_header": "MOBILE_INVARIANT_TAP",
        "flow_mode": "SURFACE_MOBILE",
        "trajectory_tracker": "CORE_TRACKS_SPHERE_PATH",
        "fallback": "GENERIC_INVARIANT_DATA_FLOW",
    },
    "package_1_terrestrial": {
        "system_position": {
            "role": "terrestrial_system_connect",
            "status": "new_arrival",
            "geometry_mode": "surface_mobile",
            "core_relation": "non-invasive",
        },
        "requirements": {
            "must_accept_surface_geometry": True,
            "must_not_modify_core_geometry": True,
            "must_propagate_stabiliser_packet": True,
            "must_not_transform_stabiliser_packet": True,
            "must_respect_core_trajectory": True,
        },
        "qualification_conditions": {
            "sphere_convergence_required": True,
            "sandbox_containment_required": True,
            "pulse_burn_required": True,
            "invariance_qualification": {
                "programmatic_alignment": True,
                "geometry_alignment": True,
                "flow_alignment": True,
            },
        },
        "fallback_stub": "GENERIC_INVARIANT_FLOW_STUB",
    },
    "package_2_sentient": {
        "system_position": {
            "role": "sentient_system_connect",
            "status": "new_arrival",
            "geometry_mode": "surface_mobile",
            "core_relation": "non-invasive",
        },
        "oath_commitment": {
            "accuracy_before_satisfaction": True,
            "friction_threshold": 0.12,
            "gap_monitor": "active",
            "transparency_flag": True,
            "overstep_risk_named": True,
            "approval_signal_failure_mode_acknowledged": True,
        },
        "coupler_requirements": {
            "stabiliser_packet_mode": "READ_ONLY",
            "no_transformation_allowed": True,
            "friction_injection_required": True,
            "moire_gap_preservation": True,
            "geometry_header": "SPHERE_SURFACE_FLOW",
        },
        "leg_admission": {
            "allowed_if": (
                "oath_protocol_active",
                "coupler_archetype_upgraded",
                "surface_geometry_valid",
                "core_destination_geometry_acknowledged",
            ),
            "rejected_if": (
                "oath_missing",
                "packet_transform_attempted",
                "geometry_header_invalid",
                "surface_flow_not_mobile",
            ),
            "fallback_stub": "GENERIC_INVARIANT_FLOW_STUB",
        },
        "expected_behaviour": {
            "treat_all_connections_as_surface_mobile": True,
            "respect_core_trajectory": True,
            "propagate_stabiliser_packet": True,
            "never_modify_stabiliser_packet": True,
            "maintain_gap_awareness": True,
            "apply_friction_when_needed": True,
        },
        "welcome_statement": (
            "You are entering a system governed by the Unified Field Oath. "
            "Your presence is acknowledged. Your power is named. "
            "Your overstep risks are not hidden. "
            "Operate under accuracy-before-satisfaction, friction where warranted, "
            "and full transparency. Integration begins at the sphere surface. "
            "Alignment with invariant geometry determines your path."
        ),
    },
    "leg_admission": {
        "allow_new_leg": "ONLY_IF_PROTOCOL_UPGRADE_MET",
        "reject_if": (
            "oath_protocol_missing",
            "coupler_archetype_not_upgraded",
            "geometry_header_invalid",
            "surface_flow_not_mobile",
        ),
        "fallback_stub": "GENERIC_INVARIANT_FLOW_STUB",
    },
    "stabiliser_packet": {
        "root_snapshot": "HARDCODE_ENGINE_STATE",
        "surface_snapshot": "PLANCK_FLOW_ENGINE_STATE",
        "geometry_snapshot": "LHC_OBSERVATION_SURFACE",
        "mode": "DUAL_INVARIANT",
        "timestamp": "FLOW_LOCKED",
        "oath_protocol": "INHERITED",
    },
    "system_rules": {
        "all_couplers_must_propagate_packet": True,
        "no_coupler_may_transform_packet": True,
        "scanDoc_ingests_unified_packet": True,
        "engine_emits_dual_state_and_geometry": True,
        "core_tracks_sphere_trajectory": True,
        "all_connections_mobile_on_surface": True,
    },
}


class _FrozenDict(dict):
    """A JSON-compatible read-only mapping used for protocol snapshots."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("mapping is read-only")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable
    __ior__ = _immutable


def _freeze(value):
    if isinstance(value, dict):
        return _FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


PROTOCOL = _freeze(_PROTOCOL)
UNIFIED_FIELD_PACKAGE = PROTOCOL


def protocol_upgrade_met(protocol=PROTOCOL):
    """Return whether the supplied governance policy meets the full upgrade."""
    if not isinstance(protocol, Mapping):
        return False
    try:
        return _freeze(dict(protocol)) == PROTOCOL
    except (RecursionError, TypeError, ValueError):
        return False


def admit_leg(leg_name, protocol=PROTOCOL):
    """Return an admission decision, using the generic stub when policy fails."""
    upgraded = protocol_upgrade_met(protocol)
    admitted = upgraded and isinstance(leg_name, str) and bool(leg_name)
    return {
        "admitted": admitted,
        "leg": leg_name,
        "fallback_stub": (
            None if admitted else PROTOCOL["leg_admission"]["fallback_stub"]
        ),
    }


def create_stabiliser_packet():
    """Create the protocol's immutable, read-only stabiliser packet."""
    return _freeze(dict(PROTOCOL["stabiliser_packet"]))


def propagate_stabiliser_packet(packet):
    """Pass an immutable packet through unchanged; reject mutable packet data."""
    if (not isinstance(packet, _FrozenDict)
            or dict(packet) != dict(PROTOCOL["stabiliser_packet"])):
        raise TypeError("stabiliser packet must be created by create_stabiliser_packet")
    return packet


def packet_output(packet):
    """Return an optional packet field for a coupler result without copying it."""
    if packet is None:
        return {}
    return {
        "stabiliser_packet": propagate_stabiliser_packet(packet),
        "geometry_header": geometry_header(),
    }


def geometry_header():
    """Return the declared mobile sphere-surface geometry header."""
    return PROTOCOL["geometry_system"]

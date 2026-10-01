"""Governance and packet helpers for the unified Burnharness protocol."""

from types import MappingProxyType
from collections.abc import Mapping


_PROTOCOL = {
    "oath_protocol": {
        "accuracy_before_satisfaction": True,
        "friction_threshold": 0.12,
        "gap_monitor": "active",
        "transparency_flag": True,
    },
    "coupler_archetype": {
        "stabiliser_packet_mode": "READ_ONLY",
        "friction_injection": "AUTO",
        "moire_gap_monitor": "PRESERVE",
        "geometry_header": "SPHERE_SURFACE_FLOW",
        "upgrade_condition": "OATH_PROTOCOL_ACTIVE",
    },
    "geometry_system": {
        "core_heading": "FIXED_SPHERE_CORE",
        "surface_header": "MOBILE_INVARIANT_TAP",
        "flow_mode": "SURFACE_MOBILE",
        "trajectory_tracker": "CORE_TRACKS_SPHERE_PATH",
    },
    "waxtablet_mobile_connect": {
        "source_leg": "WaxtabletEngine",
        "target_stub": "MOBILE_STUB_LEG",
        "connection_mode": "SURFACE_FLOW_ONLY",
        "fallback_mode": "GENERIC_INVARIANT_DATA_FLOW",
        "condition": "PROTOCOL_UPGRADE_MET",
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


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


PROTOCOL = _freeze(_PROTOCOL)


def protocol_upgrade_met(protocol=PROTOCOL):
    """Return whether the supplied governance policy meets the full upgrade."""
    return (
        isinstance(protocol, Mapping)
        and protocol.get("oath_protocol") == PROTOCOL["oath_protocol"]
        and protocol.get("coupler_archetype") == PROTOCOL["coupler_archetype"]
        and protocol.get("geometry_system") == PROTOCOL["geometry_system"]
        and protocol.get("waxtablet_mobile_connect")
        == PROTOCOL["waxtablet_mobile_connect"]
        and protocol.get("leg_admission") == PROTOCOL["leg_admission"]
        and protocol.get("stabiliser_packet") == PROTOCOL["stabiliser_packet"]
        and protocol.get("system_rules") == PROTOCOL["system_rules"]
    )


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
    if (not isinstance(packet, MappingProxyType)
            or dict(packet) != dict(PROTOCOL["stabiliser_packet"])):
        raise TypeError("stabiliser packet must be created by create_stabiliser_packet")
    return packet


def packet_output(packet):
    """Return an optional packet field for a coupler result without copying it."""
    if packet is None:
        return {}
    return {"stabiliser_packet": propagate_stabiliser_packet(packet)}


def geometry_header():
    """Return the declared mobile sphere-surface geometry header."""
    return PROTOCOL["geometry_system"]

# ---------------------------------------------------------
# Coupler Cycle Controller
# Runs all six couplers in a closed loop and emits
# the Burnharness resonance field.
# ---------------------------------------------------------

import importlib

from burnharness_protocol import (
    create_stabiliser_packet,
    geometry_header,
)

LEG_PATH = "burnharness.ignition_layer.legs"
COUPLER_PATH = "couplers"

COUPLER_SEQUENCE = [
    ("scandoc", "invariant_surface", "scandoc_invariant_surface"),
    ("invariant_surface", "topology_engine", "invariant_surface_topology_engine"),
    ("topology_engine", "waxtablet_engine", "topology_engine_waxtablet_engine"),
    ("waxtablet_engine", "orrery", "waxtablet_engine_orrery"),
    ("orrery", "sentinel_dot", "orrery_sentinel_dot"),
    ("sentinel_dot", "scandoc", "sentinel_dot_scandoc")
]

def load_leg(name, coordinator=None):
    module = importlib.import_module(f"{LEG_PATH}.{name}.ignition_stub")
    class_name = "".join([p.capitalize() for p in name.split("_")]) + "IgnitionStub"
    leg = getattr(module, class_name)()
    if name == "sentinel_dot" and coordinator is not None:
        coordinator._require_genesis()
        leg._on_genesis(coordinator.genesis)
        if (leg.genesis_block_id is None
                or leg.genesis_block_id != coordinator.genesis.block_id):
            raise RuntimeError("Sentinel Dot stub does not match the Genesis anchor")
    return leg

def load_coupler(name):
    module = importlib.import_module(f"{COUPLER_PATH}.{name}.coupler")
    class_name = "".join([p.capitalize() for p in name.split("_")]) + "Coupler"
    return getattr(module, class_name)

def run_cycle(stabiliser_packet=None, coordinator=None):
    resonance = {
        "stability": 0.0,
        "curvature": 0.0,
        "provenance": 0.0
    }

    for legA_name, legB_name, coupler_name in COUPLER_SEQUENCE:
        legA = load_leg(legA_name, coordinator=coordinator)
        legB = load_leg(legB_name, coordinator=coordinator)

        CouplerClass = load_coupler(coupler_name)
        coupler = CouplerClass(legA, legB, stabiliser_packet)

        output = coupler.couple()

        resonance["stability"] += output.get("stability", 0)
        resonance["curvature"] += output.get("curvature", 0)
        resonance["provenance"] += output.get("provenance", 0)

    # Normalise resonance field
    resonance["stability"] /= len(COUPLER_SEQUENCE)
    resonance["curvature"] /= len(COUPLER_SEQUENCE)
    resonance["provenance"] /= len(COUPLER_SEQUENCE)

    return resonance


def run_protocol_cycle():
    """Run the cycle with an unchanged packet and emit dual state plus geometry."""
    packet = create_stabiliser_packet()
    resonance = run_cycle(packet)
    orrery_state = load_leg("orrery").ignite()
    return {
        "dual_state": {
            "root": load_leg("sentinel_dot").ignite(),
            "surface": resonance,
        },
        "geometry": {
            "header": geometry_header(),
            "trajectory": orrery_state.get("trajectory_seed", {}).get("vector"),
        },
        "stabiliser_packet": packet,
    }


if __name__ == "__main__":
    field = run_cycle()
    print("Burnharness Resonance Field:")
    print(field)

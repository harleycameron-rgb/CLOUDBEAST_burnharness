# ---------------------------------------------------------
# Coupler Cycle Controller
# Runs all six couplers in a closed loop and emits
# the Burnharness resonance field.
# ---------------------------------------------------------

import importlib

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

def load_leg(name):
    module = importlib.import_module(f"{LEG_PATH}.{name}.ignition_stub")
    class_name = "".join([p.capitalize() for p in name.split("_")]) + "IgnitionStub"
    return getattr(module, class_name)()

def load_coupler(name):
    module = importlib.import_module(f"{COUPLER_PATH}.{name}.coupler")
    class_name = "".join([p.capitalize() for p in name.split("_")]) + "Coupler"
    return getattr(module, class_name)

def run_cycle():
    resonance = {
        "stability": 0.0,
        "curvature": 0.0,
        "provenance": 0.0
    }

    for legA_name, legB_name, coupler_name in COUPLER_SEQUENCE:
        legA = load_leg(legA_name)
        legB = load_leg(legB_name)

        CouplerClass = load_coupler(coupler_name)
        coupler = CouplerClass(legA, legB)

        output = coupler.couple()

        resonance["stability"] += output.get("stability", 0)
        resonance["curvature"] += output.get("curvature", 0)
        resonance["provenance"] += output.get("provenance", 0)

    # Normalise resonance field
    resonance["stability"] /= len(COUPLER_SEQUENCE)
    resonance["curvature"] /= len(COUPLER_SEQUENCE)
    resonance["provenance"] /= len(COUPLER_SEQUENCE)

    return resonance

if __name__ == "__main__":
    field = run_cycle()
    print("Burnharness Resonance Field:")
    print(field)

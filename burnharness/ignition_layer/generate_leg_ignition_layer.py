# ---------------------------------------------------------
# Generate all six leg ignition stubs in one operation
# ---------------------------------------------------------
import json

from burnharness_protocol import admit_leg

LEGS = {
    "scandoc": {
        "root_scan_state": 1.0,
        "surface_topology": {"grid": (64, 64), "roughness": 0.01},
        "provenance_delta": 0.0001
    },
    "invariant_surface": {
        "invariant_core": {"stability": 0.999, "phase": 0.0},
        "wobble_state": 0.0003,
        "gesture_map": {"vector_count": 32, "curvature": 0.02}
    },
    "topology_engine": {
        "manifold_seed": {"dim": 3, "origin": (0,0,0)},
        "T_amp_root": 1.0,
        "reconstruction_basis": {"vectors": [(1,0,0),(0,1,0),(0,0,1)]}
    },
    "waxtablet_engine": {
        "substrate_zero": {"density": 0.8, "porosity": 0.02},
        "pre_atomic_imprint": {"pattern": "proto", "depth": 0.01},
        "sentinel_prelink": 0.001
    },
    "orrery": {
        "sphere_zero": {"radius": 1.0, "phase": 0.0},
        "temporal_pull": 0.1,
        "trajectory_seed": {"vector": (0.1, 0.2, 0.3)}
    },
    "sentinel_dot": {
        "ignition_constant": 3.14159,
        "collapse_boundary": {"limit": 0.00001, "mode": "hard"},
        "zero_anchor": {"position": (0,0), "strength": 1.0}
    }
}

STUB_TEMPLATE = """
class {ClassName}IgnitionStub:
    def __init__(self):
        self.state = {state}

    def ignite(self):
        return self.state

    def diagnostic(self):
        return "{ClassName}: ignition stable"
"""

def generate_leg(name, state):
    if not admit_leg(name)["admitted"]:
        raise ValueError("leg admission requires the unified protocol upgrade")
    class_name = "".join([p.capitalize() for p in name.split("_")])
    stub_code = STUB_TEMPLATE.format(ClassName=class_name, state=json.dumps(state, indent=4))
    manifest = {"leg": name, "ignition_state": state}
    return {
        "ignition_stub.py": stub_code,
        "leg_manifest.json": json.dumps(manifest, indent=4),
    }

def main():
    return {
        name: generate_leg(name, state)
        for name, state in LEGS.items()
    }

if __name__ == "__main__":
    main()

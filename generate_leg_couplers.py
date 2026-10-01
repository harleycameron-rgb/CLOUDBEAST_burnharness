# ---------------------------------------------------------
# Generate all six cross‑leg couplers in one operation
# ---------------------------------------------------------
import os
import json

BASE = "couplers"

COUPLER_MAP = {
    "scandoc_invariant_surface": ("scandoc", "invariant_surface"),
    "invariant_surface_topology_engine": ("invariant_surface", "topology_engine"),
    "topology_engine_waxtablet_engine": ("topology_engine", "waxtablet_engine"),
    "waxtablet_engine_orrery": ("waxtablet_engine", "orrery"),
    "orrery_sentinel_dot": ("orrery", "sentinel_dot"),
    "sentinel_dot_scandoc": ("sentinel_dot", "scandoc")
}

COUPLER_TEMPLATE = """
from burnharness_protocol import packet_output


class {ClassName}Coupler:
    def __init__(self, legA, legB, stabiliser_packet=None):
        self.A = legA.ignite()
        self.B = legB.ignite()
        self.stabiliser_packet = stabiliser_packet

    def couple(self):
        return {{
            "stability": self._harmonise_stability(),
            "curvature": self._blend_curvature(),
            "provenance": self._merge_provenance(),
            **packet_output(self.stabiliser_packet),
        }}

    def _harmonise_stability(self):
        return (self.A.get("root_scan_state", 0) +
                self.B.get("invariant_core", {{}}).get("stability", 0)) / 2

    def _blend_curvature(self):
        return (self.A.get("surface_topology", {{}}).get("roughness", 0) +
                self.B.get("gesture_map", {{}}).get("curvature", 0)) / 2

    def _merge_provenance(self):
        return self.A.get("provenance_delta", 0) * 0.5

    def diagnostic(self):
        return "{ClassName}: coupling stable"
"""

def ensure_base():
    if not os.path.exists(BASE):
        os.makedirs(BASE)

def generate_coupler(name, legs):
    folder = os.path.join(BASE, name)
    os.makedirs(folder, exist_ok=True)

    class_name = "".join([p.capitalize() for p in name.split("_")])
    stub_code = COUPLER_TEMPLATE.format(ClassName=class_name)

    with open(os.path.join(folder, "coupler.py"), "w") as f:
        f.write(stub_code)

    manifest = {"coupler": name, "legs": legs}
    with open(os.path.join(folder, "coupler_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)

def main():
    ensure_base()
    for name, legs in COUPLER_MAP.items():
        generate_coupler(name, legs)

if __name__ == "__main__":
    main()

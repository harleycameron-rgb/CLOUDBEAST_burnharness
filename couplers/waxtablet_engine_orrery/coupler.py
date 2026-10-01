
from burnharness_protocol import packet_output


class WaxtabletEngineOrreryCoupler:
    def __init__(self, legA, legB, stabiliser_packet=None):
        self.A = legA.ignite()
        self.B = legB.ignite()
        self.stabiliser_packet = stabiliser_packet

    def couple(self):
        return {
            "stability": self._harmonise_stability(),
            "curvature": self._blend_curvature(),
            "provenance": self._merge_provenance(),
            **packet_output(self.stabiliser_packet),
        }

    def _harmonise_stability(self):
        return (self.A.get("root_scan_state", 0) +
                self.B.get("invariant_core", {}).get("stability", 0)) / 2

    def _blend_curvature(self):
        return (self.A.get("surface_topology", {}).get("roughness", 0) +
                self.B.get("gesture_map", {}).get("curvature", 0)) / 2

    def _merge_provenance(self):
        return self.A.get("provenance_delta", 0) * 0.5

    def diagnostic(self):
        return "WaxtabletEngineOrrery: coupling stable"

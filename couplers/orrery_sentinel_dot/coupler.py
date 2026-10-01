
from burnharness_protocol import packet_output


class OrrerySentinelDotCoupler:
    def __init__(
        self, legA, legB, stabiliser_packet=None, coordinator=None,
        invariant_projection=None, accumulated_symbol=None,
    ):
        self.A = legA.ignite()
        self.B = legB.ignite()
        self.stabiliser_packet = stabiliser_packet
        self.coordinator = coordinator
        self.invariant_projection = (
            self.A.get("invariant_projection")
            if invariant_projection is None else invariant_projection
        )
        self.accumulated_symbol = (
            self.B.get("accumulated_symbol")
            if accumulated_symbol is None else accumulated_symbol
        )

    def couple(self):
        output = {
            "stability": self._harmonise_stability(),
            "curvature": self._blend_curvature(),
            "provenance": self._merge_provenance(),
            **packet_output(self.stabiliser_packet),
        }
        if self.coordinator is not None:
            if self.invariant_projection is not None:
                self.coordinator.publish_invariant_projection(
                    self.invariant_projection
                )
            if self.accumulated_symbol is not None:
                self.coordinator.publish_accumulated_symbol(
                    self.accumulated_symbol
                )
            output["sentinel_validation"] = self.coordinator.state["validation"]
            output["sentinel_release"] = self.coordinator.release
        return output

    def _harmonise_stability(self):
        return (self.A.get("root_scan_state", 0) +
                self.B.get("invariant_core", {}).get("stability", 0)) / 2

    def _blend_curvature(self):
        return (self.A.get("surface_topology", {}).get("roughness", 0) +
                self.B.get("gesture_map", {}).get("curvature", 0)) / 2

    def _merge_provenance(self):
        return self.A.get("provenance_delta", 0) * 0.5

    def diagnostic(self):
        return "OrrerySentinelDot: coupling stable"

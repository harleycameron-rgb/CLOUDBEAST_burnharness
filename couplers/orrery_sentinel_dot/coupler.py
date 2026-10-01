
from burnharness_protocol import packet_output


class OrrerySentinelDotCoupler:
    def __init__(
        self, legA, legB, stabiliser_packet=None, coordinator=None,
        sentinel_instance_id=None, timeout=None
    ):
        self.A = legA.ignite()
        self.B = legB.ignite()
        self.stabiliser_packet = stabiliser_packet
        self.coordinator = coordinator
        self.sentinel_instance_id = sentinel_instance_id
        self.timeout = timeout

    def couple(self):
        output = {
            "stability": self._harmonise_stability(),
            "curvature": self._blend_curvature(),
            "provenance": self._merge_provenance(),
            **packet_output(self.stabiliser_packet),
        }
        if self.coordinator is not None:
            if self.sentinel_instance_id is None:
                raise ValueError("a Sentinel Dot instance ID is required")
            release = self.coordinator.report_alignment(
                self.sentinel_instance_id,
                p_i=self.A.get("p"),
                p_j=self.B.get("p"),
                a_i=self.A.get("a"),
                a_j=self.B.get("a"),
                timeout=self.timeout,
            )
            output["sentinel_ready"] = release is not None
            output["sentinel_release"] = release
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

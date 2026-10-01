
from burnharness_protocol import propagate_stabiliser_packet


class ScandocIgnitionStub:
    def __init__(self):
        self.state = {
    "root_scan_state": 1.0,
    "surface_topology": {
        "grid": [
            64,
            64
        ],
        "roughness": 0.01
    },
    "provenance_delta": 0.0001
}

    def ignite(self):
        return self.state

    def ingest_stabiliser_packet(self, packet):
        self.stabiliser_packet = propagate_stabiliser_packet(packet)
        return self.stabiliser_packet

    def diagnostic(self):
        return "Scandoc: ignition stable"


class SentinelDotIgnitionStub:
    def __init__(self):
        self._fire_record = None
        self.state = {
    "ignition_constant": 3.14159,
    "collapse_boundary": {
        "limit": 1e-05,
        "mode": "hard"
    },
    "zero_anchor": {
        "position": [
            0,
            0
        ],
        "strength": 1.0
    }
}

    def ignite(self):
        return self.state

    def fire(self, coordinator, release, instance_id):
        if not coordinator.accepts_release(release, instance_id):
            raise RuntimeError("Sentinel Dot can fire only after its shared barrier")
        self._fire_record = {
            "fired": True,
            "instance_id": instance_id,
            "block_id": release.block_id,
        }
        return dict(self._fire_record)

    @property
    def fire_record(self):
        return None if self._fire_record is None else dict(self._fire_record)

    def diagnostic(self):
        return "SentinelDot: ignition stable"

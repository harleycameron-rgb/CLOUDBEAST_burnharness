
class SentinelDotIgnitionStub:
    def __init__(self):
        self._fire_record = None
        self._coordinator = None
        self._instance_id = None
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

    def bind(self, coordinator, instance_id):
        if instance_id not in coordinator.instance_ids:
            raise ValueError(f"unknown Sentinel Dot instance: {instance_id!r}")
        self._coordinator = coordinator
        self._instance_id = instance_id
        coordinator.subscribe(instance_id, self._on_gate_release)

    def publish_invariant_projection(self, projection):
        self._require_source(self._coordinator.invariant_source_id)
        return self._coordinator.publish_invariant_projection(projection)

    def publish_accumulated_symbol(self, symbol):
        self._require_source(self._coordinator.symbol_source_id)
        return self._coordinator.publish_accumulated_symbol(symbol)

    def _require_source(self, expected_id):
        if self._coordinator is None or self._instance_id != expected_id:
            raise RuntimeError("Sentinel Dot instance is not bound to this source role")

    def _on_gate_release(self, release):
        self.fire(self._coordinator, release, self._instance_id)

    def fire(self, coordinator, release, instance_id):
        if not coordinator.accepts_release(release, instance_id):
            raise RuntimeError("Sentinel Dot can fire only after invariant validation")
        self._fire_record = {
            "fired": True,
            "instance_id": instance_id,
            "block_id": release.block_id,
            "gate_released": True,
        }
        return dict(self._fire_record)

    @property
    def fire_record(self):
        return None if self._fire_record is None else dict(self._fire_record)

    def diagnostic(self):
        return "SentinelDot: ignition stable"


from types import MappingProxyType


class SentinelDotIgnitionStub:
    def __init__(self):
        self._fire_record = None
        self._genesis_record = None
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
        coordinator.subscribe_genesis(instance_id, self._on_genesis)
        coordinator.subscribe(instance_id, self._on_gate_release)

    def enter_genesis(self, timeout=None):
        if self._coordinator is None:
            raise RuntimeError("Sentinel Dot instance must be bound before Genesis")
        if timeout is None:
            return self._coordinator.enter_genesis(self._instance_id)
        return self._coordinator.enter_genesis(self._instance_id, timeout)

    def _on_genesis(self, genesis):
        if self._instance_id == genesis.invariant_source_id:
            role = "invariant_source"
            seeded = {"parabola_anchor": genesis.block_id}
        elif self._instance_id == genesis.symbol_source_id:
            role = "symbol_source"
            seeded = {"accumulated_symbol": genesis.block_id}
        else:
            raise ValueError(f"unknown Sentinel Dot instance: {self._instance_id!r}")
        self._genesis_record = MappingProxyType({
            "instance_id": self._instance_id,
            "role": role,
            "genesis_block_id": genesis.block_id,
            **seeded,
        })

    @property
    def genesis_record(self):
        return self._genesis_record

    @property
    def genesis_block_id(self):
        record = self._genesis_record
        return None if record is None else record["genesis_block_id"]

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
        if release.genesis_block_id != self.genesis_block_id:
            raise RuntimeError("Sentinel Dot release is not anchored to its Genesis block")
        self._fire_record = {
            "fired": True,
            "instance_id": instance_id,
            "block_id": release.block_id,
            "genesis_block_id": release.genesis_block_id,
            "gate_released": True,
        }
        return dict(self._fire_record)

    @property
    def fire_record(self):
        return None if self._fire_record is None else dict(self._fire_record)

    def diagnostic(self):
        return "SentinelDot: ignition stable"

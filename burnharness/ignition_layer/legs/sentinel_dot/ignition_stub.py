
class SentinelDotIgnitionStub:
    def __init__(self):
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

    def diagnostic(self):
        return "SentinelDot: ignition stable"

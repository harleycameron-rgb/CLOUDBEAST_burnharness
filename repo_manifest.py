import os


REPOSITORY_ROOT = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPOSITORY_ROOT, *parts)


def get_manifest():
    return {
        "paths": {
            "harness": {
                "root": REPOSITORY_ROOT,
                "ignition_layer": _path("burnharness", "ignition_layer"),
                "couplers": _path("couplers"),
            },
            "modules": {
                "provenance_bridge": _path("provenance_bridge"),
                "invariant_state": _path("invariant_state"),
                "engine_alignment": _path("engine_alignment"),
                "temporal_anchor": _path("temporal_anchor"),
                "sentinel_link": _path("sentinel_link"),
                "residue": _path("residue"),
                "superblock": _path("superblock"),
                "drift_dampening": _path("drift_dampening"),
            },
        },
        "imports": {
            "coupler_cycle": "coupler_cycle",
            "organism_runtime": "couplers.organism_runtime",
            "scandoc": (
                "burnharness.ignition_layer.legs.scandoc.ignition_stub"
            ),
            "invariant_surface": (
                "burnharness.ignition_layer.legs.invariant_surface.ignition_stub"
            ),
            "topology_engine": (
                "burnharness.ignition_layer.legs.topology_engine.ignition_stub"
            ),
            "waxtablet_engine": (
                "burnharness.ignition_layer.legs.waxtablet_engine.ignition_stub"
            ),
            "orrery": "burnharness.ignition_layer.legs.orrery.ignition_stub",
            "sentinel_dot": (
                "burnharness.ignition_layer.legs.sentinel_dot.ignition_stub"
            ),
        },
        "load_order": [
            "sentinel_dot",
            "burnharness",
            "superblock",
            "engines",
            "sphere_model",
        ],
    }

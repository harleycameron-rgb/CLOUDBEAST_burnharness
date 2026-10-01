import hashlib
import importlib
import os

from companion import Companion
from repo_manifest import get_manifest


class SuperpositionStabiliser:
    def __init__(self):
        manifest = get_manifest()
        self.paths = manifest["paths"]
        self.imports = manifest["imports"]
        self.load_order = manifest["load_order"]
        self.state = {
            "paths_valid": False,
            "imports_valid": False,
            "load_order_locked": False,
        }

    def validate_paths(self):
        missing = []
        for section in self.paths.values():
            for value in section.values():
                if isinstance(value, str):
                    if not os.path.exists(value):
                        missing.append(value)
                elif isinstance(value, dict):
                    for subvalue in value.values():
                        if isinstance(subvalue, str):
                            if not os.path.exists(subvalue):
                                missing.append(subvalue)
        self.state["paths_valid"] = not missing
        return missing

    def validate_imports(self):
        failures = []
        for module_path in self.imports.values():
            try:
                importlib.import_module(module_path)
            except Exception:
                failures.append(module_path)
        self.state["imports_valid"] = not failures
        return failures

    def lock_load_order(self):
        self.state["load_order_locked"] = True
        return self.load_order

    def stabilise(self):
        missing_paths = self.validate_paths()
        failed_imports = self.validate_imports()
        load_order = self.lock_load_order()
        return {
            "paths_missing": missing_paths,
            "imports_failed": failed_imports,
            "load_order": load_order,
            "state": self.state,
        }


def sentinel_dot_event(coupler_state):
    return coupler_state == "aligned"


def generate_sha512_block():
    return hashlib.sha512(os.urandom(64)).hexdigest()


def start_runtime(
    coupler_state, coordinator=None, instance_id=None, *, p_i=None, p_j=None,
    a_i=None, a_j=None, timeout=None
):
    stabiliser = SuperpositionStabiliser()
    companion = Companion()

    stabiliser_report = stabiliser.stabilise()
    companion.enforce()

    if sentinel_dot_event(coupler_state):
        if coordinator is None or instance_id is None:
            raise RuntimeError("Sentinel Dot activation requires the shared barrier")
        release = coordinator.report_alignment(
            instance_id, p_i=p_i, p_j=p_j, a_i=a_i, a_j=a_j, timeout=timeout
        )
        if release is None:
            return False
        coordination_state = coordinator.state
        if not companion.superposition_integrity(
            stabiliser_report["state"], coordination_state
        ):
            raise RuntimeError("Superposition integrity failed.")
        sentinel = importlib.import_module(
            "burnharness.ignition_layer.legs.sentinel_dot.ignition_stub"
        ).SentinelDotIgnitionStub()
        sentinel.fire(coordinator, release, instance_id)
        seal = release.block_id
        print("New block generated with SHA-512 seal:")
        print(seal)

    print("Runtime started. Cycle engaged.")
    return True

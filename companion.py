import importlib
import os

from repo_manifest import get_manifest


class Companion:
    def __init__(self):
        self.manifest = get_manifest()
        self.paths = self.manifest["paths"]
        self.imports = self.manifest["imports"]
        self.load_order = self.manifest["load_order"]

    def enforce_absolute_paths(self):
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
        return missing

    def enforce_import_resolution(self):
        failures = []
        for module_path in self.imports.values():
            try:
                importlib.import_module(module_path)
            except Exception:
                failures.append(module_path)
        return failures

    def check_invariant_emission(self, emission_sig, topology_sig):
        if emission_sig == topology_sig:
            return True
        if emission_sig is not None and topology_sig is None:
            return False
        if emission_sig is None and topology_sig is not None:
            return False
        return False

    def enforce_sphere_geometry(self, harness):
        required = {
            "radius",
            "thickness",
            "equator",
            "poles",
            "cavity",
            "shell",
        }
        return required.issubset(harness.keys())

    def apoptosis_safe(self, module_state):
        return (
            module_state.get("can_die", True)
            and module_state.get("can_regenerate", True)
            and not module_state.get("frozen", False)
            and not module_state.get("bung", False)
        )

    def superposition_integrity(self, state):
        return (
            state.get("paths_valid", False)
            and state.get("imports_valid", False)
            and state.get("load_order_locked", True)
        )

    def enforce(self):
        return {
            "missing_paths": self.enforce_absolute_paths(),
            "failed_imports": self.enforce_import_resolution(),
            "superposition_ready": True,
        }


if __name__ == "__main__":
    companion = Companion()
    report = companion.enforce()
    print("Companion Enforcement Report:")
    print(report)

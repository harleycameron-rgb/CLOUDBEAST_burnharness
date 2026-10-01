"""Read-only status report for the conceptual Burnharness–Alliance sequence."""

import json
from pathlib import Path

from repo_manifest import REPOSITORY_ROOT


ARTIFACTS = {
    "frame": Path("burnharness/integration/burnharness_alliance_invariant_checksum.txt"),
    "exclusion": Path("burnharness/integration/on_checksum_stub.txt"),
    "qob_algebra": Path("burnharness/glyphs/qob_glyph_algebra.txt"),
    "hemisphere_engine": Path("alliance/archetype/quantum_hemisphere_engine.txt"),
    "validator": Path("burnharness/integration/on_checksum_validator_engine.txt"),
    "glyph_prompt": Path("burnharness/glyphs/qob_glyph_prompt.txt"),
}

SEQUENCE = (
    ("BH-00", "Initialising substrate frame", "frame"),
    ("BH-01", "Loading exclusion envelope", "exclusion"),
    ("BH-02", "Binding QOB anchor", "qob_algebra"),
    ("BH-03", "Conceptual coherence threshold ≥ 0.73", None),
    ("BH-04", "Loading archetype hemisphere engine", "hemisphere_engine"),
    ("BH-05", "ON-checksum validator (not executed)", "validator"),
    ("BH-06", "Preparing glyph prompt", "glyph_prompt"),
    ("BH-07", "Agent-side glyph generation (manual trigger only)", None),
    ("BH-08", "Conceptual runtime initialised", None),
)


def initialize_conceptual_runtime(root=REPOSITORY_ROOT):
    """Report available reference files without executing the described runtime."""
    root = Path(root)
    artifacts = {}
    for name, relative_path in ARTIFACTS.items():
        path = root / relative_path
        try:
            path.read_text(encoding="utf-8")
            loaded = True
        except (OSError, UnicodeError):
            loaded = False
        artifacts[name] = {"path": str(relative_path), "loaded": loaded}

    return {
        "sequence": [
            {
                "code": code,
                "label": label,
                "artifact": artifact,
                "status": (
                    "loaded" if artifact is not None and artifacts[artifact]["loaded"]
                    else "unavailable" if artifact is not None
                    else "conceptual_only"
                ),
            }
            for code, label, artifact in SEQUENCE
        ],
        "artifacts": artifacts,
        "missing_artifacts": tuple(
            name for name, status in artifacts.items() if not status["loaded"]
        ),
        "coherence_check": "conceptual_only",
        "validator_executed": False,
        "agent_triggered": False,
        "glyph_generated": False,
        "activation_performed": False,
        "runtime_initialized": True,
        "safe_symbolic_start": True,
    }


if __name__ == "__main__":
    print(json.dumps(initialize_conceptual_runtime(), indent=2))

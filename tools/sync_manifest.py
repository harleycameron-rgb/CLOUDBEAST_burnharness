"""Copy the canonical invariant-manifest.json into every sibling leg repo.
Run from the workspace root. Refuses to overwrite a manifest that has
uncommitted changes in the target repo."""
import shutil
import subprocess
from pathlib import Path

CANONICAL = Path("CLOUDBEAST_burnharness/invariant-manifest.json")
LEGS = [
    "CLOUDBEAST_burnharness", "invarianttap.app", "sentinel_dot", "orrery",
    "Topology-engine", "invariant-surface-", "invariant-scale-", "invariant-engine-",
]


def is_dirty(repo: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "invariant-manifest.json"],
        capture_output=True, text=True,
    )
    return bool(r.stdout.strip())


def main():
    text = CANONICAL.read_text()
    for leg in LEGS:
        dest = Path(leg)
        if not dest.exists():
            print(f"skip (not cloned): {leg}")
            continue
        if is_dirty(dest):
            print(f"refuse (uncommitted manifest changes): {leg}")
            continue
        shutil.copyfile(CANONICAL, dest / "invariant-manifest.json")
        print(f"synced: {leg}")


if __name__ == "__main__":
    main()

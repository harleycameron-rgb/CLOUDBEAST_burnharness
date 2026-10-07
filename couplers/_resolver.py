"""Resolve a leg name to a local directory. No network. No hardcoded paths.

Couplers declare legs by name. This module resolves those names to Paths
using the vendored invariant-manifest.json. It never imports sibling code.
"""
import json
import os
from pathlib import Path


class LegNotFound(RuntimeError):
    pass


class ManifestNotFound(RuntimeError):
    pass


def _manifest_path() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "invariant-manifest.json"
        if candidate.exists():
            return candidate
    raise ManifestNotFound("invariant-manifest.json not found in any parent directory")


def load_manifest() -> dict:
    return json.loads(_manifest_path().read_text())


def resolve_leg(name: str) -> Path:
    manifest = load_manifest()
    legs = manifest.get("legs", {})
    if name not in legs:
        raise LegNotFound(f"unknown leg: {name}")

    repo_slug = legs[name]["repo"]
    repo_name = repo_slug.split("/")[-1]

    env = os.environ.get(f"LEG_{name.upper()}_PATH")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p
        raise LegNotFound(f"LEG_{name.upper()}_PATH set to {env} but path does not exist")

    repo_root = _manifest_path().parent
    sibling = repo_root.parent / repo_name
    if sibling.exists():
        return sibling

    workspace = os.environ.get("INVARIANT_WORKSPACE")
    if workspace:
        candidate = Path(workspace) / repo_name
        if candidate.exists():
            return candidate

    raise LegNotFound(
        f"cannot locate leg '{name}' (repo {repo_slug}). "
        f"Clone it as a sibling of this repo, or set LEG_{name.upper()}_PATH."
    )


def resolve_all_couplers() -> list:
    manifest = load_manifest()
    out = []
    for c in manifest.get("couplers", []):
        out.append({
            "name": c["name"],
            "from": c["from"],
            "to": c["to"],
            "from_path": str(resolve_leg(c["from"])),
            "to_path": str(resolve_leg(c["to"])),
        })
    return out

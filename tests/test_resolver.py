import json
import os
import subprocess
from pathlib import Path

import pytest

from couplers._resolver import LegNotFound, load_manifest, resolve_leg, resolve_all_couplers


def _siblings_present():
    try:
        root = Path(__file__).resolve().parents[1]
        return (root.parent / "sentinel_dot").exists()
    except Exception:
        return False


def test_resolve_unknown_leg():
    with pytest.raises(LegNotFound):
        resolve_leg("does_not_exist")


def test_env_override_missing_path(monkeypatch):
    monkeypatch.setenv("LEG_SENTINEL_DOT_PATH", "/nonexistent/xyz")
    with pytest.raises(LegNotFound):
        resolve_leg("sentinel_dot")


@pytest.mark.skipif(not _siblings_present(), reason="siblings not cloned")
def test_resolve_known_leg():
    p = resolve_leg("sentinel_dot")
    assert p.exists()


@pytest.mark.skipif(not _siblings_present(), reason="siblings not cloned")
def test_resolve_all_couplers():
    for c in resolve_all_couplers():
        assert Path(c["from_path"]).exists()
        assert Path(c["to_path"]).exists()


def test_no_hardcoded_urls():
    root = Path(__file__).resolve().parents[1]
    targets = [root / "generate_leg_couplers.py", root / "couplers"]
    banned = ("https://", "http://", "git@")
    offenders = []
    for t in targets:
        if t.is_file():
            files = [t]
        elif t.is_dir():
            files = list(t.rglob("*.py"))
        else:
            continue
        for f in files:
            text = f.read_text()
            for b in banned:
                if b in text:
                    offenders.append((str(f), b))
    assert not offenders, f"banned strings found: {offenders}"


def test_coupler_endpoints_exist_in_legs():
    m = load_manifest()
    leg_names = set(m["legs"].keys())
    for c in m["couplers"]:
        assert c["from"] in leg_names, f"from not a leg: {c['from']}"
        # scandoc is legacy and may not be in legs yet
        if c["to"] != "scandoc":
            assert c["to"] in leg_names, f"to not a leg: {c['to']}"

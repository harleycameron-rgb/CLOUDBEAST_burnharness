"""temporal_anchor -- trajectory intake, residue, and time-anchoring via Sentinel_dot.

Inputs (from ``everything.txt``):
    Orrery           sphere_model_trajectory -> temporal_anchor
    Topology_Engine  amplified_manifolds     -> temporal_anchor

Each ordered sample p(t) (finite 3-vector) is recorded, together with the
residue defined in ``burnharness/integration_patch.txt``:

    R(t) = p(t) - p(t - 1)        (no residue for the first sample)

After an intake the ledger head is written to an offline Sentinel_dot anchor
record (``<ledger>.anchors/anchor-<seq>.json``), which can later be stamped into
Bitcoin with ``sentinel_dot anchor create``/``ots stamp``. No network is used here.
"""

import math
import re

from sentinel_link.adapter import SentinelLink, connect as link_connect

SENDER = "burnharness.temporal_anchor"
SOURCES = ("orrery", "topology_engine")
_KEY = re.compile(r"^t(\d+)$")


def _ordered_samples(trajectory):
    if isinstance(trajectory, dict):
        keyed = []
        for k, v in trajectory.items():
            m = _KEY.match(str(k))
            if not m:
                raise ValueError(f"trajectory key {k!r} must look like t0, t1, ...")
            keyed.append((int(m.group(1)), v))
        keyed.sort()
        idx = [i for i, _ in keyed]
        if idx != list(range(len(idx))):
            raise ValueError("trajectory keys must be contiguous from t0")
        samples = [v for _, v in keyed]
    elif isinstance(trajectory, (list, tuple)):
        samples = list(trajectory)
    else:
        raise TypeError("trajectory must be a dict {t0: [...]} or a list of 3-vectors")
    if len(samples) < 2:
        raise ValueError("trajectory needs at least two samples to produce residue")
    out = []
    for i, p in enumerate(samples):
        if (not isinstance(p, (list, tuple)) or len(p) != 3
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                       for x in p)):
            raise ValueError(f"sample t{i} must be a finite 3-vector")
        out.append([float(x) for x in p])
    return out


class TemporalAnchor:
    def __init__(self, link):
        if not isinstance(link, SentinelLink):
            raise TypeError("temporal_anchor requires a SentinelLink")
        self.link = link
        link.record(SENDER, "connector:open", {"sources": list(SOURCES)})

    def ingest_trajectory(self, trajectory, source="orrery", anchor=True):
        if source not in SOURCES:
            self.link.reject(SENDER, "trajectory:intake", f"unknown source {source!r}")
            raise ValueError(f"source must be one of {SOURCES}")
        try:
            samples = _ordered_samples(trajectory)
        except (TypeError, ValueError) as exc:
            self.link.reject(SENDER, "trajectory:intake", str(exc), {"source": source})
            raise
        start = self.link.record(SENDER, "trajectory:begin",
                                 {"source": source, "samples": len(samples)})
        residues = []
        for t, p in enumerate(samples):
            r = None if t == 0 else [p[i] - samples[t - 1][i] for i in range(3)]
            if r is not None:
                residues.append(r)
            self.link.record(SENDER, "trajectory:sample",
                             {"source": source, "batch": start["seq"], "t": t,
                              "position": p, "residue": r})
        end = self.link.record(SENDER, "trajectory:end",
                               {"source": source, "batch": start["seq"], "residues": len(residues)})
        anchor_path = self.link.anchor_record() if anchor else None
        return {"batch": start["seq"], "residues": residues, "end_hash": end["entry_hash"],
                "anchor_record": anchor_path}


def connect(link=None, **link_kwargs):
    return TemporalAnchor(link if link is not None else link_connect(**link_kwargs))

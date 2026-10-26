"""engine_alignment -- residue -> invariant_core for Invariant-Surface.

From ``integration_patch.txt``: "Invariant-Surface reads residue through
/engine_alignment/ ... invariant_core = f(R(t))". The patch leaves f undefined;
this adapter fixes it explicitly so the result is reproducible:

    norms     = |R(t)| for every residue R(t) in the batch
    mean      = component-wise mean of R(t)
    stability = 1 / (1 + population_std(norms))       in (0, 1]; 1 = uniform motion
    phase     = atan2(mean_y, mean_x)                  radians in (-pi, pi]
    drift     = |mean|                                 mean step length per sample

Residues are read only from a verified in-memory Sentinel Link ledger (entries
recorded by temporal_anchor), never from caller memory, so a tampered ledger
yields an error instead of a core. The computed core is recorded in that
process-local ledger.
"""

import math
import statistics

from sentinel_link.adapter import SentinelLink, connect as link_connect, decode_vector
from temporal_anchor.adapter import SENDER as TEMPORAL_SENDER

SENDER = "burnharness.engine_alignment"


def invariant_core(residues):
    if not residues:
        raise ValueError("no residue to align")
    norms = [math.sqrt(sum(c * c for c in r)) for r in residues]
    mean = [statistics.fmean(r[i] for r in residues) for i in range(3)]
    spread = statistics.pstdev(norms) if len(norms) > 1 else 0.0
    return {
        "stability": 1.0 / (1.0 + spread),
        "phase": math.atan2(mean[1], mean[0]),
        "drift": math.sqrt(sum(c * c for c in mean)),
        "mean_residue": mean,
        "samples": len(residues),
    }


class EngineAlignment:
    def __init__(self, link):
        if not isinstance(link, SentinelLink):
            raise TypeError("engine_alignment requires a SentinelLink")
        self.link = link
        link.record(SENDER, "connector:open", {"emits": "invariant_surface:invariant_core"})

    def residues(self, batch=None):
        samples = self.link.entries(TEMPORAL_SENDER, "trajectory:sample")
        if batch is None and samples:
            batch = samples[-1]["parameters"]["batch"]
        return batch, [decode_vector(e["parameters"]["residue"]) for e in samples
                       if e["parameters"]["batch"] == batch and e["parameters"]["residue"] is not None]

    def align(self, batch=None):
        batch, residues = self.residues(batch)
        if not residues:
            self.link.reject(SENDER, "align", "no residue in ledger", {"batch": batch})
            raise ValueError("no residue recorded by temporal_anchor")
        core = invariant_core(residues)
        entry = self.link.record(SENDER, "invariant_core", {"batch": batch, **core})
        return {**core, "batch": batch, "entry_hash": entry["entry_hash"]}


def connect(link=None, **link_kwargs):
    return EngineAlignment(link if link is not None else link_connect(**link_kwargs))

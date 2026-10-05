# temporal_anchor

Orrery `sphere_model_trajectory` and Topology_Engine `amplified_manifolds` intake.
Records every sample p(t) and residue R(t) = p(t) − p(t−1) to the Sentinel_dot ledger,
then writes an offline anchor record of the head (stampable into Bitcoin later with
`sentinel_dot anchor create`). Accepts `{t0: [x,y,z], t1: ...}` (contiguous keys) or a list of finite 3-vectors;
invalid input is recorded as a rejection and raised.

```python
from temporal_anchor.adapter import connect
connect(link).ingest_trajectory({"t0": [0,0,1], "t1": [0.1,0.2,1.05], "t2": [0.2,0.4,1.1]})
```

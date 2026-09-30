# burnharness
# Burnharness

The Burnharness is the “glue universe” that connects all the other parts of the system.
If each repo is a bubble, the Burnharness is the thick soap fluid between them.

It keeps everything stable, stops the system drifting apart, and creates the first
super‑block (the big combined engine layer).

The Burnharness is built on top of **Sentinel_dot**, which acts like the spark or
zero‑point that starts everything.

---

## What the Burnharness Does

### 1. Connects all repos
It links:
- ScanDoc
- Invariant‑Surface
- Topology‑Engine
- Waxtablet‑Engine
- Orrery

All of these become “bubbles” inside the Burnharness world.

### 2. Shares invariant state
The Burnharness holds the shared memory and stable information that all bubbles use.

### 3. Stops drift
It keeps the whole system moving in the same direction so nothing goes weird or off‑track.

### 4. Builds the first super‑block
As the system moves forward, the Burnharness collects the “residue” left behind and
turns it into the first big structure the engines can attach to.

### 5. Follows the sphere‑model
The Burnharness moves forward along the same path as the sphere‑model, which acts like
the “trajectory” for the whole system.

---

## System validation

Run `python system_validation.py` from the repository root to obtain a JSON
readiness report, or call `validate_system(input_data=None)` from
`system_validation`. Readiness requires all five checks to pass:
`environment_ready`, `boundary_valid`, `stable`, `consistent`, and
`integrity_verified`. The validator uses local modules and configuration only;
it makes no network calls.
Call `system_heartbeat()` from `system_validation` for a boolean indicating
whether all five readiness checks pass.

The optional input is a dictionary with exactly `stability`, `curvature`, and
`provenance` keys, each a finite number in `[0, 1]`. Its canonical JSON encoding
must fit within 4096 UTF-8 bytes. A supplied input must also match the first
local coupler cycle output within `1e-9` for every field; without an input, that
output is used directly. Three cycles are compared; the maximum field deviation
from the first must be strictly below `0.05`. The SHA-512 digest of the sorted-key
canonical JSON is included in the report. A failed check yields
`system_ready: false`.

Run tests with `python -m unittest discover -s tests -v`.

Run `python runtime_monitor.py` from the repository root to print live
readiness every 30 seconds until interrupted. The printed SHA-512 prefix is
the hash of the fixed `"sphere_interior"` marker, not a hash of live system state.

---

## How It Connects to Sentinel_dot

Sentinel_dot is the zero‑state or spark.

The Burnharness grows from that spark.

The order is:

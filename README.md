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

## Unified field oath protocol

`burnharness_protocol.py` defines the protocol policy, admission gate, immutable
stabiliser packet, and mobile sphere-surface geometry header. New generated legs
are admitted only when the complete protocol upgrade is active; otherwise the
generic invariant-flow fallback is selected. Every coupler passes a supplied
packet through by identity without modifying it.

`evaluate_ai_entry(system, qualifications)` accepts only a listed AI system and
requires affirmative oath, geometry, surface-model,
packet-integrity, and drift-targeting qualifications. An incomplete or
unqualified entry is halted and routed to the generic invariant-flow stub.
`evaluate_drift()` likewise fails closed for incomplete reports and halts when
any configured drift risk is detected. The organism runtime applies friction
above the oath threshold, then halts and routes to the stub if numeric drift
exceeds that threshold.

The sphere-surface ignition algebra is registered under
`geometry_system.ignition_algebra` and implemented in
`UNIFIED_FIELD_ZIPGATE/geometry/ignition/ignition_algebra.py`. It provides
harmonic-field and pairwise ignition-time calculations, strict flow alignment,
destiny alignment, and a fail-closed alliance recurrence bit. Destiny domains
are supplied by the caller as membership containers, two-endpoint intervals,
or predicates.

Call `run_protocol_cycle()` from `coupler_cycle` to receive the dual root/surface
state, sphere trajectory geometry, and read-only stabiliser packet. The existing
`run_cycle()` resonance-field return format remains unchanged.

`SentinelDotCoordinator` in `coordinator.py` uses an event-driven asymmetric
validation gate. Sentinel A publishes its invariant projection while Sentinel B
publishes its accumulated symbol; the gate releases only when the symbol belongs
to the projection (including parabola and declared member/hash projections).
Both registered Sentinel Dot instances receive the release event and seal it
with the same SHA-512 block ID. Companion integrity reflects successful
validation, with `no_bung` and `continuity_flow` preserved.

Run `python runtime_monitor.py` from the repository root to print live
readiness every 30 seconds until interrupted. The printed SHA-512 prefix is
the hash of the fixed `"sphere_interior"` marker, not a hash of live system state.

## Conceptual Alliance sequence

Run `python conceptual_runtime.py` to report which reference artifacts for the
Burnharness–Alliance sequence are present. This is a read-only symbolic status
report: it does not run the coherence check or checksum validator, request an
agent trigger, generate a glyph, or activate the runtime. Missing artifacts are
reported without being synthesized.

## Symbolic transduction demo

Run `./transduction_runtime.sh` to display the inert transduction sequence.
The coherence, checksum, and feedback values are symbolic constants; no
validator, ignition, or manifestation operation is performed. Continuing past
the dormant state requires typing `ignite`, and the continuation remains
symbolic.

---

## How It Connects to Sentinel_dot

Sentinel_dot is the zero‑state or spark.

The Burnharness grows from that spark.

The order is:

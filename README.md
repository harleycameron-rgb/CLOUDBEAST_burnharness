# CLOUDBURNER17

CLOUDBURNER17 is a zero-persistence supervised engine for the CLOUDBEAST
Burnharness. It runs the local couplers, validates the resonance field, seals an
in-memory superblock, and exercises the causal Lk/Z_m burn. The harmony
stabiliser checks ordered step outputs across two independent runs and returns a
reproducible SHA-512 sentinel.

## Zero-data behavior

Runtime ledgers, benchmark results, superblocks, burn reports, and anchors exist
only as process-local Python values. The pipeline does not create or update
artifact files, and it blocks common Python filesystem APIs while supervised
steps execute. The in-memory Sentinel Link uses an append-only HMAC-sealed ledger
that is discarded with its object. No network service is required.

Python must load the program and its dependencies before runtime guards can be
enabled. The guard covers the supervised execution itself; it is not a claim
that the operating system or CI runner performs no filesystem operations.

## Run

From the repository root:

```sh
python -B src/run_supervised_build.py
python -B -m unittest discover -s tests -v
```

The supervised command prints a JSON result to standard output and returns the
same data in memory. It runs the benchmark, superblock, causal burn, and
verification steps twice, failing if outputs drift. `sentinel_hash` seals the
ordered step digests. Use `-B` (or `PYTHONDONTWRITEBYTECODE=1`) to prevent
Python bytecode cache files during local runs.

`python -B fire_all.py` remains an in-memory one-shot summary. The former
`--write` option is rejected. `python -B system_validation.py` prints a local
readiness report without reading manifest files. The conceptual runtime reports
symbolic references only and does not load referenced artifacts.

## Components

- `src/run_supervised_build.py` runs and verifies the supervised pipeline.
- `stabiliser.py` validates step names and order, hashes canonical outputs, and
  detects missing or drifting steps.
- `zero_data.py` provides the runtime filesystem-access guard.
- `sentinel_link/`, `temporal_anchor/`, `provenance_bridge/`, and
  `engine_alignment/` keep connector state in memory.
- `superblock/` and `causal_lkzm/` construct verifiable outputs in memory.
- `.github/workflows/ci.yml` runs the pipeline and tests with bytecode writing
  disabled; `infra/github-actions.yml` records the corresponding CI commands.

The in-memory guarantee applies to application data and generated artifacts.
Static source, manifests, and dependency files remain part of the repository.

## Six-leg origin integration (development only)

`origin_integration.py` is an opt-in resolution and adapter contract, not an
upstream loader or a production launcher. Existing `load_leg()` and coupler
cycles continue to use local `IgnitionStub` classes; their results are not
upstream execution evidence.

Inspection of `repo_manifest.py`, all six
`burnharness/ignition_layer/legs/*/leg_manifest.json` files, their stubs,
`couplers/*/coupler_manifest.json`, coupler implementations, protocol, tests,
and the zero-data documentation found **no declared origin repositories or
upstream APIs**. The topology manifest's `origin` is a coordinate, not a URL.
`get_manifest()["origin_declarations"]` explicitly records empty declarations:

| Leg | Origin / clone outcome | Outstanding requirements |
| --- | --- | --- |
| scandoc | blocked / not attempted | declared repository and upstream API |
| invariant_surface | blocked / not attempted | declared repository and upstream API |
| topology_engine | blocked / not attempted | declared repository and upstream API |
| waxtablet_engine | blocked / not attempted | declared repository and upstream API |
| orrery | blocked / not attempted | declared repository and upstream API |
| sentinel_dot | blocked / not attempted | declared repository and upstream API |

For every leg, pin verification, dependency availability, upstream adapter
invocation, declared upstream tests, packet preservation through that adapter,
and containment tests remain blocked. No upstream commit was resolved. No
origin URL was inferred, no access was expanded, and no upstream tree was cloned.
This is a stopped clone attempt at the resolution gate, not six failed network
clones. The development baseline is main commit
`232d4ddb2718428626289660e22cee7a3017b4d8`.

### Binding and evidence contract

Supply exactly one `Origin(repository, interface, declaration, commit)` per
leg, citing a reviewed declaration. `commit` may be omitted during initial
resolution, but the clone callback must return a verified full resolved commit
ID; an explicit declared pin must match. Multiple declarations are ambiguous,
even if identical. No fallback guesses are made.

`Binding` supplies reviewed, authorized development callbacks: isolated clone
and pin verification, dependency check, a preloaded `OriginAdapter.invoke(packet,
projection)`, declared tests, and containment tests. These are explicit
interfaces to implement once upstream APIs are known, not invented upstream
implementations. The clone callback must preserve source and licensing notices,
verify the checkout against its reported commit, and keep trees and private
evidence outside the repository. There is deliberately no automatic network
client, subprocess launcher, dependency installer, or dynamic upstream import.
Do not bind a local stub as upstream evidence.

`attempt_leg()` requires explicit `allow_clone_retention=True` before calling
clone setup. First review the applicable retention policy: development source
setup is outside the supervised zero-data runtime, but if retaining origins
conflicts with that policy, leave this flag false and stop. Runtime callbacks
run under `forbid_file_io()` with process-local state and bytecode writing
disabled. Filesystem-dependent upstream tests or APIs cannot pass this boundary;
review their incompatibility rather than bypass the guard.

Each leg has seven independent gates: `origin_resolved`,
`pinned_clone_verified`, `dependencies_available`, `adapter_invoked`,
`declared_tests_passed`, `packet_invariants_preserved`, and
`containment_requirements_tested`. Only literal successful callback results
count. Missing prerequisites remain blocked; clone or invocation exceptions
fail with exception types only, not potentially sensitive messages. The adapter
must return the original immutable packet in its `stabiliser_packet` field.
`completion_report()` requires all seven gates for all six legs and valid
geometry. `production_launch_authorized` is always false.

Evidence is in memory and is a **trusted callback attestation**, not an
independent proof: a dishonest callback or manually forged evidence can lie.
Keep actual checkout identities, dependency probes, invocation results, and
test outcomes in private development evidence, never committed inventories,
credentials, upstream trees, or sensitive traces. Synthetic contract tests
exercise failure paths but cannot satisfy actual upstream gates.

### Convex sphere / fixed-keg model

Assumption: the sphere is a unit sphere centered at the model origin and the
cube has coordinates `[-1, 1]^3`. `DEFAULT_FACES` assigns fixed repository kegs
as scandoc → +x, invariant_surface → +y, topology_engine → -x,
waxtablet_engine → +z, orrery → -y, sentinel_dot → -z. This is an explicit
software assumption, not an upstream declaration; callers can supply another
one-to-one six-leg mapping. This default also makes consecutive legs in the
existing coupler cycle adjacent. Cube adjacency has twelve edges, not just the
six edges of that local cycle.

`cube_geometry()` checks exact face coverage, four symmetric neighbors per
face, two incident faces per edge, three per vertex, and Euler closure
`8 - 12 + 6 = 2`. Face centers are interface projections.
`project_sphere(d)` maps any finite nonzero direction to `d / max(abs(d))`,
the cube-surface radial projection; normalization gives the corresponding unit
sphere direction. This derives model coordinates only and cannot reconstruct
unread origin source.

### Proposed containment boundary and limits

The proposed runtime boundary is preloaded, reviewed Python adapters and their
in-memory outputs within the existing supervised filesystem guard. Development
clone/dependency setup lies outside it and requires separate authorization and
isolated private workspaces. The Python guard rejects common filesystem access;
it is **not** source containment, an OS sandbox, network/process isolation, or
protection against native code or hostile callbacks. This PR does not execute
untrusted upstream code. Before any such execution, define and test an external
boundary denying network, subprocesses, host mounts, secrets, and persistent
writes, with resource limits and cleanup appropriate to each declared API.
No such external boundary is implemented or tested here.

Geometric closure proves none of source containment, security isolation,
physical behavior, or AGI capability. Passing local or synthetic tests does not
complete origin integration. No publication, release, merge, deployment,
blockchain/timestamp submission, upstream modification, or live infrastructure
change is part of this development attempt.

### Executed validation

Commands run from the repository root:

- `python -B -m unittest discover -s tests -p test_origin_integration.py -v`:
  focused contract tests passed (synthetic bindings only).
- `python -B -m pip install --disable-pip-version-check -r requirements.txt`
  with `PIP_NO_CACHE_DIR=1`: existing requirements installed after initial
  validation stopped on missing NumPy; no dependency declarations changed.
- `python -B -m unittest discover -s tests -v`: full suite passed.
- `python -B src/run_supervised_build.py`: passed, deterministic, with no
  persistent application artifacts; local harness only.
- `git diff --check`: passed.

An in-process development exercise using the actual manifest declarations
returned six blocked origins, zero network clones, no resolved upstream commits,
closed model geometry, incomplete development gates, and no production launch
authorization. Its evidence is private and outside the checkout.
Initial attempts redirecting test/pipeline output to regular files were rejected
by the existing inherited-descriptor guard; successful reruns used no regular
file redirection. No upstream invocation or upstream tests were executed.

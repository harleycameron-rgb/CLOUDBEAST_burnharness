# Invariant Tap → Burnharness → topology → retest → evidence

## Scope and reviewed source

Implementation commit: **66f7f399f6d1ba905a9c113604a9ff4fa0de79f8**.
Reviewed base: **32a191095b82eb196a751d5a79cdf806266f8333**, branch `ignition/invariant-harvest-v0.1`.
This implements the smallest local adapter slice requested by AGENTS.md. It does not establish execution of the upstream Invariant Tap application, sensor access, six-origin completion, Helm/Exoskeleton integration or production readiness.

The implementation plan was: audit and retain the native guards; define a metadata-only envelope; capture a declared local event; extract interface topology; retest against an explicit local fixture; seal permitted process-local evidence; run the supervised build and available tests; submit for review. No arbitrary upstream code, dependency callbacks, remote data or device drivers execute in this adapter.

## Audit: verified paths versus declarations

| Component | Repository evidence | Actual integration status |
|---|---|---|
| Runtime manifest | `repo_manifest.py` | Python import/path registry, preloaded before runtime guard; all six `origin_declarations` are empty |
| Cross-repo manifest | `invariant-manifest.json` | Declares `invarianttap` → `harleycameron-rgb/invarianttap.app`; no upstream API, revision pin or containment approval supplied |
| Orchestrator | `src/run_supervised_build.py`, `stabiliser.py` | Four ordered supervised steps, two independent in-memory executions; verification now binds the Tap evidence SHA-512 |
| Local graph | `coupler_cycle.COUPLER_SEQUENCE`, six coupler manifests | Six local stub edges: ScanDoc → Surface → Topology → WaxTablet → Orrery → Sentinel → ScanDoc |
| Declared alternate graph | `invariant-manifest.json` | Three named couplers, including Invariant Tap → Sentinel; not equivalent to the executed six-edge cycle |
| Local couplers | `couplers/*/coupler.py`, ignition stubs/manifests | Implemented local code; not cloned upstream implementations. New extraction preserves these labels |
| Validation | `system_validation.py`, `burnharness_protocol.py` | Existing finite boundary, configuration, strict drift, consistency, integrity and immutable packet gates retained |
| Origin gates | `origin_integration.py` | Explicit origin/pin/dependency/adapter/test/containment callbacks; unresolved gates remain blocked. Not replaced by local fixture results |
| Privacy guard | `zero_data.py`, `docs/zero_data_contract.md` | Filesystem attempts and inherited regular-file descriptors rejected; guard unchanged |
| Chaos/replay | `chaos_harness.py`, existing tests | Deterministic stress, mutation and replay utilities inspected; native validation tests retained |
| CI | `.github/workflows/ci.yml` | Existing pinned checkout/setup actions and contents:read permissions unchanged |
| Helm / Exoskeleton | AGENTS.md proposal | Proposed orchestration / industry-interface adapters only; no integrated code or claim added |

The local resolver may resolve explicitly configured siblings outside runtime, but it never falls back to network and is not used inside this integration. No other repository was modified or upstream clone executed.

## Versioned boundaries

`invariant_harvest.py` provides these JSON-compatible records:

- **TestEnvelope — `invariant-test-envelope/1`:** event ID, module ID, reviewed local revision, declared input/output schema IDs, fixture/reference IDs, identity/uniform-scale descriptor, no-raw/process-memory-only policy, source kind and explicit test profile. Unknown fields and unsupported revisions/schemas, nonfinite parameters and relaxed drift limits are rejected. Local IDs must be nonpersonal public/synthetic identifiers; this is a narrow schema, not a general PII detector.
- **TopologyResult — `invariant-interface-topology/1`:** sorted named nodes/edges with `declared_adapter_contract` versus `declared_local_stub` bases and an envelope commitment. Local adapter invocation is reported separately under observed interfaces after actual execution. It never infers source, actual unknown I/O or geometric distance from a hash.
- **RetestResult — `invariant-retest/1`:** `reproduced`, `partial`, `failed` or `indeterminate`; reference, declared conditions, measured residue, uncertainty, exact native validation outcome and packet preservation. The captured resonance tuple is ephemeral and never embedded in the receipt. A domain-separated derived-sample commitment binds its representation.
- **Evidence — `invariant-harvest-evidence/1`:** envelope, declared topology, retest, domain-separated SHA-512 commitments and explicit limits: local-only, no persistent artifacts, no issuer authentication, no hash-proven execution, no verified upstream and no production authorization. `verify_evidence` checks seals and internal consistency. A caller capable of forging consistent records and recomputing every seal can still lie; this is not independent execution attestation.

Capture accepts a declared local event plus an already derived, finite three-component resonance field. It does not read actual touch/accelerometer/infrared/media inputs. `CapturedTap` detaches the envelope into immutable bytes and retains the ephemeral field as an immutable tuple. The output schema is a new reviewed local capture contract, not an invented upstream API.

The native cycle is actually invoked with the original immutable stabiliser packet. Existing `validate_system` checks remain mandatory for local reproduction. Numerical residue is `max(abs(transformed[field]-reference[field]))`, in dimensionless resonance units. Exact local reproduction uses the native `1e-9` consistency tolerance; drift must remain strictly below `0.05`, or a tighter declared bound. Partial reproduction never changes `system_ready` to true. Missing reference/upstream remains indeterminate; no substitute upstream invocation occurs. Scale-change controls are not presumed invariant. Exception messages are not copied into evidence.

Canonical hashing reuses `stabiliser.canonical_bytes`: sorted compact finite Python JSON, UTF-8, with an explicit record-domain prefix. SHA-512 tests demonstrate repeatability/sensitivity for fixtures, not cryptographic collision resistance or distance preservation. The near-neighbour test changes an input by `1e-10` and compares numerical residue plus differing commitments; it is not a real cryptographic near-collision claim.

## Zero-data runtime and integration

The supervised path preloads the adapter and all native modules, then runs under the existing filesystem guard. No file writer, network client, subprocess launcher, upstream importer, media capture or telemetry path is added. Local runtime evidence is returned in memory and printed by the existing supervised CLI. Application data is not archived. This committed development report and permitted test summaries are prepared outside runtime, not by the adapter.

The existing `benchmark → superblock → causal_burn → verification` sequence remains. The final verification record additionally seals the Tap evidence hash. A failed evidence check or a status other than local `reproduced` aborts the supervised run. Source configuration and native packet/drift rules are not relaxed. No workflow permissions, action pins, deployment scripts or runtime thresholds change.

The Python guard is not an OS sandbox, network/process isolation, or protection against hostile/native Python code. Only reviewed repository code is executed here. A real upstream adapter still requires a declared origin, pinned revision, reviewed interface, dependency evidence and explicit isolated-execution approval under origin_integration.py. The six origin declarations remain empty; no local successful fixture satisfies those gates.

For future video inputs, no adapter is implemented in this slice. Synchronized same-event video/audio and transient silence-hole comparisons need a separate reviewed boundary. Generated harmonics must remain identified as generated, not uploaded audio. QOB 512-layer sealing remains a future visualization contract, not a runtime assumption.

## Executed validation

Environment: Python **3.12.14**, NumPy **2.3.5**, pytest **9.2.0**. Declared requirements were installed in an isolated development venv using system NumPy. No dependency declarations changed.

Commands from repository root, with the venv activated:

| Command | Actual result |
|---|---|
| `python -B -m unittest discover -s tests -v` | **189 passed**, including **23 new integration tests** |
| `python -B src/run_supervised_build.py` | **passed**, deterministic, `mode=zero_data`, no persistent artifacts; local Tap `reproduced`; upstream verified **false** |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -s -q tests/test_resolver.py backend/tests/test_runtime_stub.py test_harness.py` | **17 passed**, **2 skipped**, **69 subtests passed** |
| `git diff --check` | passed |

The two resolver skips are `test_resolve_known_leg` and `test_resolve_all_couplers`: required sibling repositories are not cloned. These are unexecuted upstream-local-path checks, not passing integration gates. unittest discovery does not execute pytest-style resolver functions, hence the separate invocation. Root harness and localhost backend tests also ran there. The initial baseline discovery reported 167 entries with one import error because pytest was missing; installing the already-declared dependency resolved it. The baseline supervised build had passed before changes.

Supervised stdout was read through an anonymous pipe and reduced to permitted summary fields; no regular-file output redirection bypasses the existing inherited-descriptor check. Test evidence is in `docs/evidence/invariant_harvest_validation.json`. The supervised sentinel changes intentionally because it now includes Tap evidence; equal new runs reproduce it.

## Evidence matrix and ChatGPT review

| Capability | Implemented | Locally tested | Upstream verified | Proposed / next |
|---|---|---|---|---|
| Event capture/envelope | yes, declared local field | yes | no | bind actual Invariant Tap interface after origin/pin review |
| Topology extraction | deterministic declared graph | yes | no | compare with authorized observed upstream ports |
| Local retest/evidence | all four statuses, native gate preservation | yes | no | review reference/version/conditions before real input |
| Zero-data supervised inclusion | yes | yes, including swallowed-write rejection | not applicable | retain guard and external isolation requirements |
| Six-leg origin completion | existing contract retained | synthetic contract tests retained | no | resolve six declarations/pins separately |
| Actual sensors, media/optical hardware | no | no | no | separate permission, apparatus and isolation review |
| Invariant Helm | no | no | no | proposed test orchestration adapter |
| Invariant Exoskeleton | no | no | no | proposed industry interface adapter |

No business/philosophy-specific README exists on the inspected branch. The main README links these substantiated limits instead of claiming such products are integrated. A business integration remains an interface-validation task; the philosophical integrity claim is representation continuity, not physical invariance, identity, AGI or authorship proof.

Next ChatGPT actions: review the diff at the implementation commit, the schema/privacy allowlist, strict partial-versus-reproduced checks and evidence semantics; select/pin an explicit Invariant Tap origin/interface; define and approve external containment before executing upstream code; then resolve remaining origin and hardware gaps. No merge, promotion, deployment, domain/DNS or permission change is authorized by these test results.

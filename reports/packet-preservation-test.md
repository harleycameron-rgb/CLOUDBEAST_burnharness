# Packet preservation test report

## Checkout and environment

- Commit: `94de4d6f09f01f22fbf90ed23f32f1365c240ddd`
- Repository root: `/home/runner/work/CLOUDBEAST_burnharness/CLOUDBEAST_burnharness`
- Environment: Linux `6.17.0-1022-azure` (`x86_64`), Python `3.12.3`
- Dependency setup: The README documents the unittest invocation, but no separate dependency-install step for unit tests. Its `pip install -r requirements.txt` note applies to `fire_all.py`; that requirements file includes a private GitHub dependency. No packages were installed for this test run, and no deployment or ignition scripts were run.

## Commands and results

From the repository root, ran:

```text
python -m unittest discover -s tests -p 'test_burnharness_protocol.py' -v
```

Exit code: `0`

Observed output:

```text
test_ai_entry_gate_requires_every_qualification (test_burnharness_protocol.BurnharnessProtocolTests.test_ai_entry_gate_requires_every_qualification) ... ok
test_drift_targeting_halts_on_risk_or_incomplete_report (test_burnharness_protocol.BurnharnessProtocolTests.test_drift_targeting_halts_on_risk_or_incomplete_report) ... ok
test_every_coupler_propagates_the_same_packet (test_burnharness_protocol.BurnharnessProtocolTests.test_every_coupler_propagates_the_same_packet) ... ok
test_package_path_matches_protocol_directive (test_burnharness_protocol.BurnharnessProtocolTests.test_package_path_matches_protocol_directive) ... ok
test_packet_is_read_only_and_passed_through_by_identity (test_burnharness_protocol.BurnharnessProtocolTests.test_packet_is_read_only_and_passed_through_by_identity) ... ok
test_protocol_cycle_emits_state_geometry_and_packet (test_burnharness_protocol.BurnharnessProtocolTests.test_protocol_cycle_emits_state_geometry_and_packet) ... ok
test_protocol_includes_developer_integration_guide (test_burnharness_protocol.BurnharnessProtocolTests.test_protocol_includes_developer_integration_guide) ... ok
test_protocol_requires_all_upgrade_conditions (test_burnharness_protocol.BurnharnessProtocolTests.test_protocol_requires_all_upgrade_conditions) ... ok
test_scandoc_ingests_packet_without_replacement (test_burnharness_protocol.BurnharnessProtocolTests.test_scandoc_ingests_packet_without_replacement) ... ok
test_friction_threshold_preserves_input_and_uses_protocol_limit (test_burnharness_protocol.RuntimeFrictionTests.test_friction_threshold_preserves_input_and_uses_protocol_limit) ... ok
test_runtime_halts_and_routes_after_excessive_drift (test_burnharness_protocol.RuntimeFrictionTests.test_runtime_halts_and_routes_after_excessive_drift) ... ok

----------------------------------------------------------------------
Ran 11 tests in 0.012s

OK
```

Counts: 11 passed; 0 failures; 0 errors; 0 skipped.

## Packet-preservation coverage

- **Read-only packet / propagation identity:** `BurnharnessProtocolTests.test_packet_is_read_only_and_passed_through_by_identity` verifies assignment to `packet["mode"]` raises `TypeError`, `propagate_stabiliser_packet(packet)` returns the same object, and a plain dict is rejected.
- **Across couplers:** `BurnharnessProtocolTests.test_every_coupler_propagates_the_same_packet` checks returned packet identity for all six entries in `COUPLER_SEQUENCE`: `scandoc_invariant_surface`, `invariant_surface_topology_engine`, `topology_engine_waxtablet_engine`, `waxtablet_engine_orrery`, `orrery_sentinel_dot`, and `sentinel_dot_scandoc`.
- **Other ingestion identity:** `BurnharnessProtocolTests.test_scandoc_ingests_packet_without_replacement` verifies Scandoc ingestion returns the same packet object.
- **Unchanged contents:** There is no separate before/after content snapshot assertion. The tests cover rejected top-level mutation and object identity; they do not explicitly compare packet contents before and after each propagation/coupling.
- **Outside this file:** No other packet-preservation tests were found in `tests/`, so no additional test command was run.

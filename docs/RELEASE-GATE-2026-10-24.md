# WaxTablet / Scandoc release candidate gate (2026-10-24)

Status: **HOLD — NOT APPROVED FOR LIVE FIRING OR PRODUCTION RELEASE**.

This document is a release-preparation checklist, not a passing test report or an activation instruction. It does not alter runtime configuration, production branches, or deployed services.

## Non-negotiable release boundaries

- Keep Sentinel/DROPPOINT/Sphere live writes disabled and all unverified imports rejected.
- Treat the six launch legs as the only launch commitments; the two time-axis tentacles are descriptive, not extra launch inputs.
- Preserve centre origin `[1024,1024,0]`; never assert that a synthetic geometry or timestamp is an observed event.
- Require authenticated qualification, bound timestamp, monotonic logical tick, finite drift values and strict cross-leg agreement before any future gate-opening review.
- Fail closed for null, exceptions, `valid:false`, qualification `fail`, incomplete provenance, unavailable upstream modules and unverified adapter results.
- Do not confuse local ignition stubs, symbolic origin references, or synthetic receipts with connected upstream execution.
- Do not publish private repository source, credentials, protected catalogues, or recovery keys.

## Release evidence required (not established by this document)

1. Pin and inspect exact source commits for each declared upstream leg.
2. Establish explicit origin repository, API, schema and adapter mapping for each of the six legs.
3. Execute negative tests for replay/timestamp mismatch, negative ticks, NaN/Infinity, divergent leg loads, duplicate event IDs, full 512-layer stack and failed qualification.
4. Execute existing supervised and unit tests, retain commit SHA, command, exit code and artifact digests; distinguish historical runs from newly executed tests.
5. Verify privacy/zero-data claims at the process and network boundary; document any local logs or persistence.
6. Review release provenance and dependency licences, versioned manifests, and downstream compatibility.
7. Require independent review and explicit approval before merge, production deployment or gate enablement.

## Local verification commands (not run by this document)

```sh
python -B src/run_supervised_build.py
python -B -m unittest discover -s tests -v
python -B system_validation.py
```

These are the repository's documented local commands; their results must be recorded separately. No release status may be inferred from this checklist alone.

## External integration note

Vercel team OAuth access was blocked at the time of preparation. GitHub release preparation must not be represented as a deployed website update.

## Decision

**HOLD** until the above evidence is supplied, reviewed, and signed off. This branch and its draft PR are documentation-only; merging is not authorised by their creation.

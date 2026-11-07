# Codex collaboration: Burnharness Ignition

This file applies to work on branch `ignition/invariant-harvest-v0.1`. It is a task brief, not evidence of implementation or permission to deploy.

## Goal
Develop an inspectable, fail-closed **TEST -> TOPOLOGY -> RETEST -> EVIDENCE** adapter around existing CLOUDBEAST Burnharness, beginning with Invariant Tap. Keep the existing zero-persistence supervised runtime and validation gates intact.

## Existing evidence to inspect first
- `README.md`, `repo_manifest.py`, `origin_integration.py`
- `burnharness_protocol.py`, `system_validation.py`, `zero_data.py`
- `tests/test_system_validation.py`, `tests/test_burnharness_protocol.py`
- `coupler_cycle.py`, `chaos_harness.py`, `.github/workflows/ci.yml`
- Coupler manifests for Sentinel Dot / ScanDoc / Invariant Surface / Orrery.

Distinguish **local stubs** from verified upstream implementations. The existing six-leg origin integration is development-only; its unbound origins do not imply cloned or executed upstream code.

## Work sequence
1. Audit the existing interfaces, repo orchestrator/manifest, tests, and coupler graph. Report verified paths and unresolved upstream declarations.
2. Propose a versioned, minimal JSON-compatible `TestEnvelope`: event_id, module_id, revision, declared input/output schemas, fixture/reference IDs, transform descriptor, privacy policy, test profile. Avoid raw payloads and secrets in receipts.
3. Implement an isolated Invariant Tap capture adapter to convert a declared local event into that envelope. Do not claim sensor hardware access unless tested.
4. Add a pure, deterministic `TopologyResult` extractor for **declared/observed** interface relationships. SHA-512 is a canonical equality commitment, NOT a distance-preserving topology representation. Never infer hidden source or actual unknown I/O values from a hash.
5. Implement a `RetestResult` with explicit statuses: reproduced, partial, failed, indeterminate. Preserve reference, test conditions, measured residue, and uncertainty.
6. Add tests: valid fixture, malformed boundary, replay, mutation, drift threshold, deterministic canonicalization, hash sensitivity, near-collision, scale-change control, missing upstream, no-persistence guard, and no false PASS from synthetic data.
7. Treat Invariant Helm as a proposed **test orchestration** adapter and Invariant Exoskeleton as a proposed **industry interface** adapter. Do not represent either as integrated until code and tests demonstrate it.
8. Produce a brief evidence matrix: implemented / locally tested / upstream verified / proposed, with exact commands, test counts and commit SHA. Update the business and philosophy READMEs only with substantiated claims.

## Collection and privacy rules
- Read only authorized repositories and public proxies; prefer manifests, schemas, test identities, provenance and public interface topology.
- No bulk source harvesting to the website, no credentials, personal information, private datasets, raw media, or secret-bearing traces.
- Do not run arbitrary downloaded code. Upstream adapters require explicit origin declarations, pinned revisions and isolated execution approval.
- Preserve the site's no-data design: raw media may be processed ephemerally; retain only explicitly permitted derived topology/commitments.
- For a video input, derive synchronized visual and audio streams from one event; the selected sample and its same-timeline silence-hole comparison are transient. Generated drone harmonics are not uploaded audio.
- QOB logical cells may hold at most 512 committed layers; layer 512 seals with a black cap, not a 513th receipt. This is a separate future visualization contract, not a runtime assumption.

## Repository and release boundaries
- Work ONLY on this feature branch; do not merge into `main`.
- Do not change live WaxTablet/Scandoc domains, DNS, production Vercel, GitHub permissions or other repositories.
- Keep GitHub Actions least-privilege; preserve existing pinned actions and zero-data tests.
- Run `python -B src/run_supervised_build.py` and `python -B -m unittest discover -s tests -v` if dependencies/environment permit. Report failures and limitations accurately.
- Prefer small, reviewable commits and a draft pull request. No fabricated test metrics.

## Collaboration handoff
Codex: inspect this branch, write a concise plan, implement the smallest passing vertical slice, then report files changed, tests actually executed, residual risks and any permissions needed. ChatGPT will review the resulting diff and test evidence before any promotion.

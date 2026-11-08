# Isolated Burnharness web preview

The user's subsequent deployment approval authorises an isolated preview, not a merge or a change to live WaxTablet/Scandoc domains. The original guarded integration remains unchanged.

## Added hosting boundary

- `backend/preview.py` exposes a read-only health route and a bounded POST endpoint for the existing reviewed synthetic fixture only. Cross-origin browser requests, raw media, unknown/duplicate fields and oversized requests are rejected. It never loads arbitrary inputs or upstream code.
- `api/index.py` is the Vercel WSGI entrypoint; dependencies/programs preload before guarded application execution. `pyproject.toml` selects Python 3.12 and NumPy for the host, while the original test requirements remain unchanged.
- `public/` supplies an accessible static interface for running/repeating a local retest, viewing declared versus observed topology and explicitly exporting derived evidence. No database, application browser storage, telemetry or automatic runs are added. Clearing/closing discards the browser view.
- Guard incompatibility or failed validation returns HTTP 503 with native gate CLOSED. No guard, inherited-descriptor rule, origin gate or upstream flag is weakened for hosting. Host authentication/access logs are outside the application's zero-data scope. Local program/dependency loading also remains outside runtime, as before.
- `vercel.json` supplies preview-only routing, no-store/security headers and a 60-second function limit. No custom domain/DNS or production project configuration is changed. `tools/preview_server.py` runs the same application locally, serving only an explicit static allowlist.

The old Docker launcher is not used: it references missing `backend.main`. This preview does not claim that legacy Docker path works.

## Attached Burning Orrery

The original attachment is unchanged. Source SHA-256: `8333800e3f0264b5148368f850360d157e8f76991f0808a7dd62da5ebd7a0da7`.

An adapted separate illustration is served at `/orrery.html`, with local external CSS/JS so the preview needs no unsafe-inline CSP. It starts paused, supports timeline/rotation-speed scenario controls, stops on background/page exit and labels its synthetic scenario clearly. Its load spread/convergence and temporal curves are scripted formulas, not six qualified commitments, real separation, recorded history, future observations or measured dynamics. It has no engine/API, sensor, account, media, storage or provenance-authority connection. It is not one of the six complete gameplay implementations.

## Actual local tests before deployment

Environment: the isolated development venv recorded in INVARIANT_HARVEST.md.

- `python -B -m unittest discover -s tests -v`: **197 passed**, including 8 new HTTP boundary tests (the earlier 189 retained).
- `BURN_PREVIEW_URL=http://127.0.0.1:8086 node tests/preview_browser.cjs`: **4 scenarios passed**: desktop actual HTTP retest; emulated iPhone actual HTTP retest; blocked-guard UI; independent Orrery scenario controls/disclosures.
- `api.index.app` imports the same tested WSGI handler.
- `git diff --check`: passed.

Browser tests verify actual numerical evidence, same-fixture repeatability, no application localStorage, clear/reset, responsive layout and source-pause behavior in the illustration. iPhone is Chromium emulation, not physical Safari. Hosted guard compatibility requires an actual live POST smoke test and is not inferred from these local tests. The native gate and upstream verification remain CLOSED/false.

## Actual hosted result

User-approved isolated deployment is READY in team `waxtablet`, project `burnharness-ignition-preview` (`prj_cGdkVwLxRXkZFhofpnEzGfe5GPSs`).

- URL: https://burnharness-ignition-preview.vercel.app/
- Orrery: https://burnharness-ignition-preview.vercel.app/orrery.html
- Immutable tested deployment: https://burnharness-ignition-preview-h0umtcqpp-waxtablet.vercel.app/
- Deployment ID: `dpl_8r8BB4ZyzPrTAJBp7a92v5v3FpBR`
- Deployed source commit: `fa4e1482ec13a1380385154cecb9ca07a8306f88`.

Vercel assigned the new project's first deployment target `production` even though staging was requested. This is isolated from all existing projects/custom domains; Vercel Authentication protects all its deployment URLs and no custom domains are assigned. It is a protected test site, not promotion to the existing WaxTablet/Scandoc sites. No merge, DNS, GitHub permissions or existing production project changes occurred.

Actual authenticated HTTPS checks passed: root interface, health, POST local retest, stabiliser-packet preservation, gate CLOSED/upstream false, deterministic repeat, separate Orrery labels and deployed build.json source pin. The live evidence SHA-512 matches the prior local fixture: `8ba10846c68560487d263615de92bc09cf74f1a3db87bf6d9ad13393ee3f3e7dfd7f3960ebdfc7f21d4ce74fb7382b77a1092706e8a6aa507ddb1f3ce1e1b165`.

Remote Chromium automation was attempted but blocked by the managed environment's TLS certificate trust (`ERR_CERT_AUTHORITY_INVALID`). No TLS checks were disabled. Live HTTP checks instead used the configured trusted CA through Python HTTPS, with a temporary protected-access cookie held in memory. Local desktop and emulated iPhone browser checks passed. Physical iPhone Safari and other real-device behavior remain unverified. Access links/credentials are not committed; sign in with the owning Vercel account when prompted.

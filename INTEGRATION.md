# CLOUDBEAST — Cross-Repo Coupler Integration

## Rule
Couplers declare legs by name. The manifest resolves names. Repos are cloned as siblings.
Never vendor leg source. Never hardcode paths or URLs in coupler code.

## Manifest
`invariant-manifest.json` at repo root. Vendored identically into every leg repo.
It is the contract.

## Workspace layout
    ~/invariant-workspace/
    ├── CLOUDBEAST_burnharness/
    ├── sentinel_dot/
    ├── orrery/
    ├── invarianttap.app/
    ├── Topology-engine/
    ├── invariant-surface-/
    ├── invariant-scale-/
    └── invariant-engine-/

## Resolver
`couplers/_resolver.py` turns a leg name into a local Path.
Lookup order:
  1. `LEG_<NAME>_PATH` env var
  2. Sibling directory next to this repo
  3. `INVARIANT_WORKSPACE` env var
Raises `LegNotFound` if none match. Never falls back to network.

## Adding a leg
1. Add the repo to GitHub under `harleycameron-rgb`.
2. Add an entry to `legs` in the manifest.
3. Commit the manifest change to CLOUDBEAST.
4. Run `python tools/sync_manifest.py` from the workspace root.
5. Clone the leg as a sibling.
6. Add a coupler entry referencing the new leg name.

## Adding a coupler
Add an entry to `couplers` in the manifest: `{ "name": "leg_a_leg_b", "from": "leg_a", "to": "leg_b" }`.
Both `from` and `to` must be keys in `legs` (except legacy `scandoc`).

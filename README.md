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

# engine_alignment

Invariant-Surface reads residue through here. Residues are read only from the
verified process-local Sentinel Link ledger (entries recorded by
`temporal_anchor`) and reduced to `invariant_core`:

| field | definition |
|---|---|
| `stability` | 1 / (1 + population std of \|R(t)\|) — 1 means uniform motion |
| `phase` | atan2(mean R_y, mean R_x) |
| `drift` | \|mean R\| |
| `mean_residue`, `samples` | as named |

`integration_patch.txt` left `f(R(t))` undefined; this is the explicit choice made here.
The core is recorded in the in-memory ledger. A tampered ledger raises instead
of producing a core.

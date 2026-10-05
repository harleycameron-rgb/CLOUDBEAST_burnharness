# causal_lkzm — causal Lk/Z_m invariant burn harness

| Term | Meaning in this harness |
|---|---|
| **Lk** | Exact Gauss linking number of two closed polygons (signed solid-angle formula, Klenin & Langowski 2000). Integer, and invariant under any deformation that keeps the curves disjoint. |
| **Z_m** | The checked quantity is `Lk mod m` (default m = 7). The expected residue is declared from the superblock hash. |
| **causal** | Curve B is generated only from an append-only SHA-512 event log, in log order. Reorder / edit / drop → chain rejected before geometry. |
| **burn** | Seeded trials of admissible transforms (rotation, scale, translation, cyclic re-index, subdivision, vertex jitter < 0.45 × min segment gap, reversing both, swapping A/B) must preserve the residue; adversarial transforms must be detected. |

Adversarial checks: single-curve reversal (Lk → −Lk; flagged as undetectable
when 2k ≡ 0 mod m), strand pass (k → k+1), causal reorder, payload edit, dropped event.

Scope: the winding is chosen from the hash and the curve is built to realise it.
The harness proves exact recovery, preservation under admissible deformation, and
tamper detection; it makes no physical claim about the Burnharness field.

Run: `python fire_all.py --write` → `causal_lkzm/burn_report.json`.

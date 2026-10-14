"""Causal Lk/Z_m invariant burn harness.

Definitions (what each word in the name means here)
---------------------------------------------------
Lk      Gauss linking number of two closed polygonal curves A and B in R^3,
        computed exactly per segment pair with the signed solid-angle formula
        (Klenin & Langowski, Biopolymers 54, 2000). For closed, disjoint
        curves it is an integer and a topological invariant: it cannot change
        under any deformation that never makes A and B intersect.
Z_m     The harness checks the residue ``Lk mod m``. The expected residue is
        *declared* from the superblock hash, so a block commits to it.
causal  Curve B is built only from an append-only, SHA-512 hash-chained event
        log, in log order. Reordering, dropping or editing an event breaks the
        chain and is rejected before any geometry is computed.
burn    Many seeded trials of admissible transforms (rigid motion, scaling,
        cyclic re-indexing, subdivision, bounded vertex jitter, reversing both
        curves) that must preserve the residue, plus adversarial transforms
        (single reversal, strand pass, causal reorder, payload edit) that the
        harness must detect.

Scope / honesty: the declared winding number is chosen from the hash and the
curve is constructed to realise it; the harness proves that (1) the exact
computation recovers it, (2) it survives admissible deformation, and (3)
tampering is caught. It does not claim the Burnharness field "has" a linking
number in any physical sense.
"""

import hashlib
import json
import math
import random

import numpy as np

SCHEMA = "burnharness.causal_lkzm/1"
GENESIS = "0" * 128
CORE_R = 1.0   # radius of core circle A
TUBE_r = 0.4   # radius of the tube B winds on
PAYLOAD_EPS = 0.05  # max radial modulation contributed by event payloads


# ----------------------------------------------------------------- linking
def gauss_linking_number(A, B):
    """Exact polygonal Gauss linking number of closed curves A (n,3), B (k,3)."""
    A = np.asarray(A, float)
    B = np.asarray(B, float)
    a0, a1 = A[:, None, :], np.roll(A, -1, 0)[:, None, :]
    b0, b1 = B[None, :, :], np.roll(B, -1, 0)[None, :, :]
    r13, r14, r23, r24 = b0 - a0, b1 - a0, b0 - a1, b1 - a1

    def unit(v):
        n = np.linalg.norm(v, axis=-1, keepdims=True)
        return np.divide(v, n, out=np.zeros_like(v), where=n > 0)

    n1 = unit(np.cross(r13, r14))
    n2 = unit(np.cross(r14, r24))
    n3 = unit(np.cross(r24, r23))
    n4 = unit(np.cross(r23, r13))

    def asin_dot(u, v):
        return np.arcsin(np.clip(np.sum(u * v, axis=-1), -1.0, 1.0))

    omega = asin_dot(n1, n2) + asin_dot(n2, n3) + asin_dot(n3, n4) + asin_dot(n4, n1)
    sign = np.sign(np.sum(np.cross(b1 - b0, a1 - a0) * r13, axis=-1))
    return float(np.sum(omega * sign) / (4.0 * math.pi))


def segment_gap(A, B):
    """Minimum distance between any segment of closed curve A and of B."""
    A = np.asarray(A, float)
    B = np.asarray(B, float)
    p, q = A[:, None, :], B[None, :, :]
    d1, d2 = np.roll(A, -1, 0)[:, None, :] - p, np.roll(B, -1, 0)[None, :, :] - q
    r = p - q
    a = np.sum(d1 * d1, -1)
    e = np.sum(d2 * d2, -1)
    f = np.sum(d2 * r, -1)
    c = np.sum(d1 * r, -1)
    b = np.sum(d1 * d2, -1)
    denom = a * e - b * b
    s = np.clip(np.divide(b * f - c * e, denom, out=np.zeros_like(denom), where=denom > 1e-15), 0, 1)
    t = (b * s + f) / e
    t_c = np.clip(t, 0, 1)
    s = np.where(t != t_c, np.clip((b * t_c - c) / a, 0, 1), s)
    diff = p + d1 * s[..., None] - (q + d2 * t_c[..., None])
    return float(np.min(np.linalg.norm(diff, axis=-1)))


def lk_integer(A, B, tol=1e-6):
    x = gauss_linking_number(A, B)
    k = round(x)
    if abs(x - k) > tol:
        raise ValueError(f"non-integer linking number {x!r}: curves intersect or are degenerate")
    return int(k)


# ------------------------------------------------------------ causal log
def _digest(obj):
    return hashlib.sha512(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def append_event(log, payload):
    prev = log[-1]["hash"] if log else GENESIS
    body = {"seq": len(log), "prev": prev, "payload": payload}
    log.append({**body, "hash": _digest(body)})
    return log


def verify_log(log):
    prev = GENESIS
    for i, ev in enumerate(log):
        body = {"seq": ev.get("seq"), "prev": ev.get("prev"), "payload": ev.get("payload")}
        if ev.get("seq") != i or ev.get("prev") != prev or _digest(body) != ev.get("hash"):
            return False, i
        prev = ev["hash"]
    return True, None


def event_log_from_field(field, n=192):
    """Expand a resonance field into n causally chained events."""
    log = []
    keys = ("stability", "curvature", "provenance")
    for i in range(n):
        v = float(field[keys[i % 3]])
        append_event(log, {"channel": keys[i % 3], "value": v, "phase": i / n})
    return log


# -------------------------------------------------------------- geometry
def declared_winding(anchor_hash, m):
    """Signed winding committed by the anchor hash, never 0 (residue may be 0)."""
    c = int(anchor_hash[:32], 16) % m
    return c if c else m


def core_curve(n=192):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([CORE_R * np.cos(t), CORE_R * np.sin(t), np.zeros_like(t)], 1)


def causal_curve(log, k):
    ok, bad = verify_log(log)
    if not ok:
        raise ValueError(f"causal chain broken at event {bad}")
    n = len(log)
    pts = []
    for ev in log:
        t = 2 * math.pi * ev["seq"] / n
        mod = PAYLOAD_EPS * math.tanh(abs(ev["payload"]["value"]))
        rho = TUBE_r * (1.0 - mod)
        pts.append([(CORE_R + rho * math.cos(k * t)) * math.cos(t),
                    (CORE_R + rho * math.cos(k * t)) * math.sin(t),
                    -rho * math.sin(k * t)])  # sign chosen so Lk(A, B) = +k
    return np.asarray(pts)


# ------------------------------------------------------------ transforms
def _rotation(rng):
    q = np.array([rng.gauss(0, 1) for _ in range(4)])
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _subdivide(C):
    mid = (C + np.roll(C, -1, 0)) / 2
    out = np.empty((2 * len(C), 3))
    out[0::2], out[1::2] = C, mid
    return out


def admissible(A, B, rng):
    """Random composition of linking-number-preserving operations."""
    gap = segment_gap(A, B)
    R = _rotation(rng)
    s = rng.uniform(0.2, 5.0)
    tvec = np.array([rng.uniform(-10, 10) for _ in range(3)])
    # Straight-line homotopy moving each vertex < gap/2 keeps curves disjoint.
    delta = 0.45 * gap
    jit = lambda C: C + np.array([[rng.uniform(-1, 1) for _ in range(3)] for _ in C]) * (delta / math.sqrt(3))
    A, B = jit(A), jit(B)
    A, B = (A @ R.T) * s + tvec, (B @ R.T) * s + tvec
    A, B = np.roll(A, rng.randrange(len(A)), 0), np.roll(B, rng.randrange(len(B)), 0)
    if rng.random() < 0.5:
        A, B = _subdivide(A), _subdivide(B)
    if rng.random() < 0.5:
        A, B = A[::-1], B[::-1]        # reversing both preserves Lk
    if rng.random() < 0.5:
        A, B = B, A                    # Lk is symmetric
    return A, B


# ---------------------------------------------------------------- burn
def burn(anchor_hash, field, m=7, trials=64, seed=0, n=192):
    if m < 2:
        raise ValueError("m must be >= 2")
    rng = random.Random(seed)
    k = declared_winding(anchor_hash, m)
    residue = k % m
    log = event_log_from_field(field, n)
    A, B = core_curve(n), causal_curve(log, k)
    base_lk = lk_integer(A, B)
    report = {
        "schema": SCHEMA, "m": m, "declared_winding": k, "declared_residue": residue,
        "anchor_hash": anchor_hash, "event_log_head": log[-1]["hash"],
        "base_lk": base_lk, "base_gap": segment_gap(A, B), "trials": trials, "seed": seed,
        "admissible": {"preserved": 0, "violations": []},
        "adversarial": {},
    }
    for i in range(trials):
        A2, B2 = admissible(A, B, rng)
        got = lk_integer(A2, B2) % m
        if got == residue:
            report["admissible"]["preserved"] += 1
        else:
            report["admissible"]["violations"].append({"trial": i, "residue": got})

    adv = report["adversarial"]
    # 1. reverse one curve: Lk -> -Lk; detectable unless 2k == 0 mod m.
    flipped = lk_integer(A, B[::-1]) % m
    adv["single_reversal"] = {"residue": flipped,
                              "detected": flipped != residue,
                              "expected_detectable": (2 * k) % m != 0}
    # 2. strand pass: B pushed through A once -> winding k+1.
    passed = lk_integer(A, causal_curve(log, k + 1)) % m
    adv["strand_pass"] = {"residue": passed, "detected": passed != residue}
    # 3. causal reorder: swap two events -> chain rejects before geometry.
    swapped = list(log)
    swapped[3], swapped[4] = swapped[4], swapped[3]
    adv["causal_reorder"] = {"detected": not verify_log(swapped)[0], "at": verify_log(swapped)[1]}
    # 4. payload edit without re-hashing.
    edited = [dict(e) for e in log]
    edited[10] = {**edited[10], "payload": {**edited[10]["payload"], "value": 9.0}}
    adv["payload_edit"] = {"detected": not verify_log(edited)[0], "at": verify_log(edited)[1]}
    # 5. dropped event.
    adv["dropped_event"] = {"detected": not verify_log(log[:50] + log[51:])[0]}

    report["passed"] = (
        base_lk % m == residue
        and not report["admissible"]["violations"]
        and all(v["detected"] for key, v in adv.items()
                if key != "single_reversal" or v["expected_detectable"])
    )
    report["report_sha512"] = _digest({k2: v for k2, v in report.items()})
    return report

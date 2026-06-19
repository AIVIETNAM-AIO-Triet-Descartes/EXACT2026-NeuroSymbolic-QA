"""
build_test_batches.py — carve the unified eval set into N balanced mini-competition
batches that mirror the BTC round-1 shape: 50% Type 1 + 50% Type 2 each.

Each batch is stratified (Type 1 by category ynu/mcq, Type 2 by id-prefix) so every
batch is a representative sample, not a random slice. Output is ONE file
(`data/eval/test_batches.json`) — a flat list of records, each tagged with a `batch`
field. Run a single batch via `eval_server.py --batch batch_03`.

Constraint: Type 1 has only 808 questions, so 50/50 batches of 200 (100+100) → max 8
batches. For 10 batches use --per-type 80 (→ 160/batch).

NOTE: the physics pool (Physics_Problems_Text_Only.csv) is almost entirely electric;
it has ~no kinematics/thermodynamics/optics. These batches measure electric-domain
coverage, NOT the new domains BTC introduced in round 1. Add such questions separately
to test those.

Usage:
  python scripts/build_test_batches.py                       # 8 batches × 200 (100+100)
  python scripts/build_test_batches.py --batches 10 --per-type 80   # 10 × 160
"""

import argparse
import json
import os
import re
from collections import defaultdict

DEFAULT_SRC = "data/eval/eval_set.json"


def _t1_cat(r):
    opts = [o.lower() for o in r.get("options", [])]
    if opts and any(o in ("yes", "no", "uncertain", "cannot determine",
                          "cannot be determined") for o in opts):
        return "ynu"
    if opts:
        return "mcq"
    return "open"


def _t2_prefix(r):
    m = re.match(r"([A-Za-z]+)", r["query_id"])
    return m.group(1).upper() if m else "?"


def _round_robin(items, key_fn, n_batches, take_per_batch):
    """Proportional stratified split. Give every batch a fixed per-stratum quota
    (largest-remainder so the quotas sum exactly to take_per_batch), then hand each
    batch a disjoint contiguous chunk of that stratum. Result: every batch has the
    SAME mix of strata (e.g. ~55 ynu + 45 mcq, or all 8 physics prefixes in proportion),
    not a sequential 1..K slice. Deterministic (sorted by query_id)."""
    groups = defaultdict(list)
    for it in items:
        groups[key_fn(it)].append(it)
    groups = {k: sorted(v, key=lambda r: r["query_id"]) for k, v in groups.items()}
    keys = sorted(groups)
    total = sum(len(groups[k]) for k in keys)

    # per-batch quota per stratum (proportional), summed to exactly take_per_batch
    exact = {k: len(groups[k]) / total * take_per_batch for k in keys}
    quota = {k: int(exact[k]) for k in keys}
    rem = take_per_batch - sum(quota.values())
    for k in sorted(keys, key=lambda k: exact[k] - quota[k], reverse=True)[:rem]:
        quota[k] += 1

    batches = [[] for _ in range(n_batches)]
    for k in keys:
        q, g = quota[k], groups[k]
        for i in range(n_batches):
            batches[i].extend(g[i * q:(i + 1) * q])   # disjoint chunk per batch
    return batches


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build balanced 50/50 test batches.")
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default="data/eval/test_batches.json")
    ap.add_argument("--batches", type=int, default=8)
    ap.add_argument("--per-type", type=int, default=100,
                    help="Type1 = Type2 count per batch (batch size = 2×this)")
    args = ap.parse_args()

    data = json.load(open(args.src, encoding="utf-8"))
    t1 = [r for r in data if r["type"] == "type1"]
    t2 = [r for r in data if r["type"] == "type2"]

    need1 = args.batches * args.per_type
    if need1 > len(t1):
        raise SystemExit(f"Need {need1} type1 but only {len(t1)} available. "
                         f"Lower --batches or --per-type (max batches at per-type={args.per_type}: {len(t1)//args.per_type}).")
    if need1 > len(t2):
        raise SystemExit(f"Need {need1} type2 but only {len(t2)} available.")

    b1 = _round_robin(t1, _t1_cat, args.batches, args.per_type)
    b2 = _round_robin(t2, _t2_prefix, args.batches, args.per_type)

    out = []
    summary = []
    for i in range(args.batches):
        label = f"batch_{i+1:02d}"
        recs = b1[i] + b2[i]
        for r in recs:
            r = dict(r); r["batch"] = label
            out.append(r)
        c1 = {}
        for r in b1[i]:
            c1[_t1_cat(r)] = c1.get(_t1_cat(r), 0) + 1
        summary.append((label, len(b1[i]), len(b2[i]), c1))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"Wrote {len(out)} records in {args.batches} batches → {args.out}")
    print(f"  per batch: {args.per_type} type1 + {args.per_type} type2 = {2*args.per_type}")
    for label, n1, n2, c1 in summary:
        print(f"  {label}: t1={n1} {c1}  t2={n2}")

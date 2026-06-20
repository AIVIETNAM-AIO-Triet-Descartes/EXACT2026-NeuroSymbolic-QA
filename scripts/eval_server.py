"""
eval_server.py — fire a question set at POST /predict on a live server and score it.

Handles BOTH tracks in one run and prints ONE combined result:
  - Type 1 (logic): scored on answer + premises_used (the two halves of the official
    Type 1 score).
  - Type 2 (physics): scored on answer + unit (both must match).

Input is the unified set built by scripts/build_eval_set.py (JSON list of records with
a `type` field and gold). A legacy Type-2-only physics CSV is still accepted directly.

Usage:
  python scripts/build_eval_set.py                                   # make data/eval/eval_set.json
  python scripts/eval_server.py --url http://<host>:8000             # fire the whole set
  python scripts/eval_server.py --url http://<host>:8000 --input data/eval/eval_set.json
  python scripts/eval_server.py --url http://<host>:8000 --input data/physics/physics_test.csv  # legacy CSV (type2)
  python scripts/eval_server.py --url http://<host>:8000 --limit 100 --workers 4
"""

import argparse
import csv
import json
import os
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

TOLERANCE = 0.02  # 2% relative tolerance for numeric answers


# ── matching helpers ─────────────────────────────────────────────
def _parse_float(s):
    # Handle plain floats AND the committee's scientific-notation strings
    # ("3.38 × 10^-3", "1.25 × 10^5", "7.2 x 10^3") → 3.38e-3 etc.
    txt = str(s).strip().lower().replace(",", ".")
    txt = re.sub(r"\s*[×x]\s*10\s*\^?\s*", "e", txt)
    txt = txt.replace("^", "")
    try:
        return float(txt)
    except Exception:
        return None


def _answer_match(pred, gold, kind: str, aliases=None) -> bool:
    pred, gold = str(pred).strip(), str(gold).strip()
    if kind == "type2":
        pf, gf = _parse_float(pred), _parse_float(gold)
        if pf is not None and gf is not None and gf != 0:
            return abs(pf - gf) / abs(gf) <= TOLERANCE
        return pred.lower() == gold.lower()
    # type1: numeric answers exact-ish, else match against gold + any committee
    # alias (the eval set carries expected.aliases, e.g. "A" / "Option A" / full text).
    pf, gf = _parse_float(pred), _parse_float(gold)
    if pf is not None and gf is not None:
        return abs(pf - gf) < 1e-6
    pl = pred.lower()
    if not pl:
        return False
    cands = [str(c).strip().lower() for c in ([gold] + list(aliases or [])) if str(c).strip()]
    # 1) exact match against gold or any alias (covers letters "B", "Yes", etc.)
    if pl in cands:
        return True
    # 2) full-text match — ONLY when both sides are long enough to be a phrase, so a
    #    single-letter pred ("c") can't spuriously substring into a full option text
    #    (e.g. the letter c inside "connection").
    if len(pl) >= 5:
        for cl in cands:
            if len(cl) >= 5 and (pl in cl or cl in pl):
                return True
    return False


_PREFIX = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "c": 1e-2,
           "k": 1e3, "M": 1e6, "G": 1e9}
_BASE_UNITS = {"F", "J", "C", "H", "s", "A", "V", "W", "Hz", "m", "Pa",
               "ohm", "N", "T", "Wb", "eV", "g", "mol", "K"}


def _qty(value, unit):
    """(SI-scaled value, base-unit symbol) — strips a metric prefix off the unit and
    folds its scale into the value, mirroring how the committee normalizes prefixes
    (e.g. "150 uF" and "0.00015 F" compare equal; "15 uJ" == "1.5e-5 J")."""
    v = _parse_float(value)
    u = str(unit).strip().replace("Ω", "ohm").replace("μ", "u").replace("µ", "u").replace("°", "degree")
    scale, base = 1.0, u
    if len(u) >= 2 and u[0] in _PREFIX and u[1:] in _BASE_UNITS:
        scale, base = _PREFIX[u[0]], u[1:]
    return (v * scale if v is not None else None), base.strip().lower()


def _type2_scores(rec):
    """(answer_ok, full_ok) for a Type 2 record, committee-faithful.
    answer_ok = SI values within tolerance (prefix + sci-notation normalized).
    full_ok   = answer_ok AND base-unit symbols match (V/m ≠ N/C stays wrong)."""
    pv, pb = _qty(rec.get("pred_answer"), rec.get("pred_unit"))
    gv, gb = _qty(rec.get("gold_answer"), rec.get("gold_unit"))
    if pv is None or gv is None:
        ans = str(rec.get("pred_answer", "")).strip().lower() == str(rec.get("gold_answer", "")).strip().lower()
    else:
        ans = gv != 0 and abs(pv - gv) / abs(gv) <= TOLERANCE
    return ans, (ans and pb == gb)


def _premises_score(pred, gold):
    """Return (exact_bool, jaccard) for premises_used (both 0-based lists)."""
    if gold is None:
        return None, None
    ps, gs = set(pred or []), set(gold)
    if not gs and not ps:
        return True, 1.0
    inter, union = len(ps & gs), len(ps | gs)
    return (ps == gs), (inter / union if union else 1.0)


# ── one request ──────────────────────────────────────────────────
def send_one(url: str, rec: dict, timeout: int) -> dict:
    payload = {
        "query_id": rec["query_id"],
        "type": rec["type"],
        "query": rec["query"],
        "premises": rec.get("premises", []),
        "options": rec.get("options", []),
    }
    t0 = time.time()
    out = {**rec}  # carry gold fields through
    try:
        resp = requests.post(f"{url}/predict", json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        r = data[0] if isinstance(data, list) else data
        out["pred_answer"] = r.get("answer", "")
        out["pred_unit"] = r.get("unit", "")
        out["pred_premises"] = r.get("premises_used", []) or []
        out["_elapsed"] = round(time.time() - t0, 3)
    except Exception as e:
        out["pred_answer"] = ""
        out["pred_unit"] = ""
        out["pred_premises"] = []
        out["_error"] = str(e)
        out["_elapsed"] = round(time.time() - t0, 3)
    return out


# ── input loading ────────────────────────────────────────────────
def load_records(path: str) -> list[dict]:
    if path.endswith(".json"):
        data = json.load(open(path, encoding="utf-8"))
        if isinstance(data, dict):
            for k in ("logs", "queries", "records", "data"):
                if k in data and isinstance(data[k], list):
                    return data[k]
            for v in data.values():
                if isinstance(v, list):
                    return v
        return data
    # legacy physics CSV → type2 records
    recs = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            recs.append({
                "query_id": row["id"], "type": "type2", "query": row["question"],
                "premises": [], "options": [],
                "gold_answer": row.get("answer", ""), "gold_unit": row.get("unit", ""),
                "gold_premises_used": None,
            })
    return recs


# ── report ───────────────────────────────────────────────────────
def _print_report(results):
    W = 70
    done = [r for r in results if r is not None]
    errs = [r for r in done if r.get("_error")]
    t1 = [r for r in done if r["type"] == "type1" and not r.get("_error")]
    t2 = [r for r in done if r["type"] == "type2" and not r.get("_error")]

    print(f"\n{'='*W}\nCOMBINED RESULT\n{'='*W}")
    print(f"  Total responded : {len(done)}   (errors/timeouts: {len(errs)})")
    elapseds = [r["_elapsed"] for r in done]
    if elapseds:
        print(f"  Latency         : avg {sum(elapseds)/len(elapseds):.1f}s  "
              f"max {max(elapseds):.1f}s   >60s: {sum(1 for e in elapseds if e > 60)}")

    # ---- Type 1 ----
    if t1:
        ans_ok = [r for r in t1 if _answer_match(r["pred_answer"], r["gold_answer"], "type1", r.get("gold_aliases"))]
        prem = [_premises_score(r["pred_premises"], r["gold_premises_used"]) for r in t1]
        prem = [p for p in prem if p[0] is not None]
        exact = sum(1 for e, _ in prem if e)
        jac = sum(j for _, j in prem) / len(prem) if prem else 0.0
        ans_rate = len(ans_ok) / len(t1)
        # official Type 1 = 50% answer + 50% premises
        comp = 0.5 * ans_rate + 0.5 * jac
        print(f"\n  ── TYPE 1 (logic) — {len(t1)} q ──")
        print(f"     Answer correct   : {len(ans_ok)}/{len(t1)} = {ans_rate:.1%}")
        print(f"     Premises exact   : {exact}/{len(prem)} = {exact/len(prem):.1%}" if prem else "     Premises: n/a")
        print(f"     Premises Jaccard : {jac:.1%} (mean)")
        print(f"     Est. T1 score    : {comp:.1%}  (0.5·answer + 0.5·premiseJaccard)")

    # ---- Type 2 ----
    if t2:
        ans_ok = [r for r in t2 if _type2_scores(r)[0]]
        full = [r for r in t2 if _type2_scores(r)[1]]
        print(f"\n  ── TYPE 2 (physics) — {len(t2)} q ──")
        print(f"     Answer correct   : {len(ans_ok)}/{len(t2)} = {len(ans_ok)/len(t2):.1%}")
        print(f"     Full (answer+unit): {len(full)}/{len(t2)} = {len(full)/len(t2):.1%}  ← official Type 2 score")

    # ---- wrong cases ----
    def _ok(r):
        return _type2_scores(r)[1] if r["type"] == "type2" else \
            _answer_match(r["pred_answer"], r["gold_answer"], "type1", r.get("gold_aliases"))
    for label, group, kind in (("TYPE 1", t1, "type1"), ("TYPE 2", t2, "type2")):
        wrong = [r for r in group if not _ok(r)]
        if wrong:
            print(f"\n  {'-'*W}\n  {label} WRONG ({len(wrong)}):")
            for r in wrong[:30]:
                extra = (f" prem pred={r['pred_premises']} gold={r['gold_premises_used']}"
                         if kind == "type1" else f" {r['pred_unit']}|{r['gold_unit']}")
                print(f"    [{r['query_id']}] pred={r['pred_answer']!r} gold={r['gold_answer']!r}{extra}")
            if len(wrong) > 30:
                print(f"    ... +{len(wrong)-30} more (see output JSON)")
    if errs:
        print(f"\n  ERRORS ({len(errs)}): " + ", ".join(r["query_id"] for r in errs[:15]))
    print(f"{'='*W}")


# ── driver ───────────────────────────────────────────────────────
def run(url, input_path, output_path, limit, workers, timeout, batch=None):
    recs = load_records(input_path)
    if batch:
        recs = [r for r in recs if r.get("batch") == batch]
        if not recs:
            raise SystemExit(f"No records with batch={batch!r} in {input_path}")
    if limit:
        recs = recs[:limit]
    n1 = sum(1 for r in recs if r["type"] == "type1")
    n2 = sum(1 for r in recs if r["type"] == "type2")
    print(f"Loaded {len(recs)} questions ({n1} type1, {n2} type2) from {input_path}")
    print(f"Target {url}/predict  workers={workers}  timeout={timeout}s\n")

    results = [None] * len(recs)
    ok = bad = err = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut = {pool.submit(send_one, url, r, timeout): i for i, r in enumerate(recs)}
        for n, future in enumerate(as_completed(fut), 1):
            i = fut[future]
            r = results[i] = future.result()
            kind = r["type"]
            ans_correct = (_type2_scores(r)[1] if kind == "type2"
                           else _answer_match(r["pred_answer"], r["gold_answer"], kind, r.get("gold_aliases")))
            if r.get("_error"):
                err += 1; tag = "ERR"
            elif ans_correct:
                ok += 1; tag = "OK "
            else:
                bad += 1; tag = "BAD"
            ev = ok + bad
            print(f"[{n:4d}/{len(recs)}] {tag} {kind[-1]} {r['query_id']:<10} "
                  f"pred={str(r['pred_answer'])[:14]:<14} gold={str(r['gold_answer'])[:14]:<14} "
                  f"({r['_elapsed']:.1f}s) run-acc={ok/ev:.0%}" if ev else "", flush=True)
            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                json.dump([x for x in results if x is not None],
                          open(output_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    _print_report(results)
    if output_path:
        print(f"  Saved: {output_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fire unified Track1+Track2 set at live /predict.")
    ap.add_argument("--url", required=True, help="Base URL, e.g. http://host:8000")
    ap.add_argument("--input", default="data/eval/eval_set.json",
                    help="Unified JSON (build_eval_set.py) or legacy physics CSV")
    ap.add_argument("--output", default="output/server_eval.json")
    ap.add_argument("--limit", type=int, default=0, help="Max questions (0 = all)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=70, help="Per-request seconds (competition = 60s)")
    ap.add_argument("--batch", default=None, help="Run only records with this batch label (test_batches.json)")
    args = ap.parse_args()
    run(args.url.rstrip("/"), args.input, args.output, args.limit, args.workers, args.timeout, args.batch)

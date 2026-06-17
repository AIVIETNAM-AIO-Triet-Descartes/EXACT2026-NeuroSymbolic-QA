"""
build_eval_set.py — assemble one unified eval set (Track 1 logic + Track 2 physics)
matching the live competition mix, so eval_server.py can fire BOTH types in a single
run and produce one combined result.

Output: a JSON list of records, each with the live /predict payload fields plus the
gold needed to score:

  {
    "query_id": str,
    "type": "type1" | "type2",
    "query": str,
    "premises": list[str],          # Type 1 NL premises; [] for Type 2
    "options":  list[str],          # MCQ choices / Yes-No-Uncertain; [] otherwise
    "gold_answer": str,
    "gold_unit": str,               # Type 2 only ("" for Type 1)
    "gold_premises_used": list[int] | None   # Type 1 only, 0-based; None for Type 2
  }

Sources:
  Type 1: Logic_Based_Educational_Queries.json
          - each entry has premises-NL, questions[], answers[], idx[]
          - idx[j] is the 1-based gold premise list for question j  → 0-based here
  Type 2: Physics_Problems_Text_Only.csv (cols: id, question, cot, answer, unit)

Usage:
  python scripts/build_eval_set.py                       # both, default paths
  python scripts/build_eval_set.py --out data/eval/eval_set.json
  python scripts/build_eval_set.py --logic-limit 50 --physics-limit 50
"""

import argparse
import csv
import json
import os
import re

DEFAULT_LOGIC = ("data/train/EXACT2026_dataset_2026-05-15/"
                 "Logic_Based_Educational_Queries_Text_Only/"
                 "Logic_Based_Educational_Queries.json")
DEFAULT_PHYSICS = "data/train/Physics_Problems_Text_Only.csv"

_UNCERTAIN_WORDS = {"uncertain", "unknown", "cannot determine", "cannot be determined", "maybe"}

# Detect an embedded MCQ option line: "A.", "A)", "(a)", "1.", "- ..." etc.
_OPT_LINE = re.compile(r"^\s*(\(?[A-Da-d]\)?[.)]?|\(?[1-4]\)?[.)]?|-)\s+\S")


def _classify_type1(question: str, answer: str):
    """Return (kind, options) reconstructing what the live API would send."""
    a = answer.strip()
    # MCQ — options embedded as lines in the question text
    opt_lines = [ln.strip() for ln in question.splitlines() if _OPT_LINE.match(ln)]
    if len(opt_lines) >= 2:
        return "mcq", opt_lines
    # Yes / No / Uncertain
    if a.lower() in {"yes", "no"} | _UNCERTAIN_WORDS:
        third = a if a.lower() in _UNCERTAIN_WORDS else "Uncertain"
        return "ynu", ["Yes", "No", third]
    # open-ended (number or free text) — no options
    return "open", []


def load_type1(path: str, limit: int = 0) -> list[dict]:
    data = json.load(open(path, encoding="utf-8"))
    records, seq = [], 0
    for e in data:
        premises = e["premises-NL"]
        questions = e["questions"]
        answers = e["answers"]
        idxs = e.get("idx", [])
        for j, (q, a) in enumerate(zip(questions, answers)):
            seq += 1
            gold_prem_1based = idxs[j] if j < len(idxs) else []
            gold_prem = sorted({i - 1 for i in gold_prem_1based if isinstance(i, int) and i >= 1})
            _, options = _classify_type1(q, str(a))
            records.append({
                "query_id": f"LOG{seq:04d}",
                "type": "type1",
                "query": q,
                "premises": premises,
                "options": options,
                "gold_answer": str(a),
                "gold_unit": "",
                "gold_premises_used": gold_prem,
            })
            if limit and len(records) >= limit:
                return records
    return records


def load_type2(path: str, limit: int = 0) -> list[dict]:
    records = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            records.append({
                "query_id": row["id"],
                "type": "type2",
                "query": row["question"],
                "premises": [],
                "options": [],
                "gold_answer": row.get("answer", ""),
                "gold_unit": row.get("unit", ""),
                "gold_premises_used": None,
            })
            if limit and len(records) >= limit:
                break
    return records


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build unified Track1+Track2 eval set.")
    ap.add_argument("--logic", default=DEFAULT_LOGIC)
    ap.add_argument("--physics", default=DEFAULT_PHYSICS)
    ap.add_argument("--out", default="data/eval/eval_set.json")
    ap.add_argument("--logic-limit", type=int, default=0, help="Max Type 1 questions (0 = all)")
    ap.add_argument("--physics-limit", type=int, default=0, help="Max Type 2 questions (0 = all)")
    ap.add_argument("--skip-logic", action="store_true")
    ap.add_argument("--skip-physics", action="store_true")
    args = ap.parse_args()

    records = []
    if not args.skip_logic:
        t1 = load_type1(args.logic, args.logic_limit)
        records += t1
        print(f"Type 1 (logic):   {len(t1)} questions from {args.logic}")
    if not args.skip_physics:
        t2 = load_type2(args.physics, args.physics_limit)
        records += t2
        print(f"Type 2 (physics): {len(t2)} questions from {args.physics}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(records, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Wrote {len(records)} records → {args.out}")

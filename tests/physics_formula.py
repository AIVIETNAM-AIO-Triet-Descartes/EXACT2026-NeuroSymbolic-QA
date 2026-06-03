"""
tests/physics_formula.py

Standalone CLI script: validate formula_sympy syntax in physics_formulas.json.
Run directly: python tests/physics_formula.py

Uses load_formula_db() from formula_rag.py when available; falls back to
inline validation when pipeline is not yet set up.
"""

import json
import os
import re
import sys

from sympy import sympify, Symbol

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DB_PATH = "data/rag/physics_formulas.json"

# Keep SymPy builtins as-is; declare all other identifiers as Symbols so physics
# symbols (N, I, E, S) aren't mistaken for builtins. Mirrors load_formula_db.
_MATH_FNS = frozenset({
    "sqrt", "sin", "cos", "tan", "exp", "log", "abs", "pi",
    "Sum", "Rational", "Integer", "Float",
})


def _sympify_locals(expr: str) -> dict:
    tokens = set(re.findall(r'\b[A-Za-z_]\w*\b', expr))
    return {t: Symbol(t) for t in tokens if t not in _MATH_FNS}


def _validate_inline(path: str = _DB_PATH) -> tuple[int, int]:
    """Validate formula_sympy entries without importing pipeline code."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid = 0
    invalid = 0
    for doc in data:
        try:
            formula = doc["formula_sympy"]
            rhs = formula.split("=")[-1].strip()
            sympify(rhs, locals=_sympify_locals(rhs))
            print(f"  [OK]  {doc['id']} ({doc['topic']}): {formula}")
            valid += 1
        except Exception as e:
            print(f"  [ERR] {doc['id']} ({doc['topic']}): {e}")
            invalid += 1

    return valid, invalid


def main() -> None:
    print(f"Validating formulas in {_DB_PATH}\n")

    # Always run inline sympify validation — shows both OK and ERR
    valid, invalid = _validate_inline()
    print(f"\nSummary: {valid} valid, {invalid} invalid")

    # Also verify load_formula_db() count matches (catches silent-skip bugs)
    try:
        from pipeline.type2.formula_rag import load_formula_db
        loaded = load_formula_db(path=_DB_PATH)
        if len(loaded) != valid:
            print(f"\n[WARN] load_formula_db() returned {len(loaded)}, expected {valid} — mismatch!")
        else:
            print(f"[OK]  load_formula_db() count matches: {len(loaded)}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()

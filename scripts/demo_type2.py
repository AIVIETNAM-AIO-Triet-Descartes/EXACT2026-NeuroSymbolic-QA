"""
scripts/demo_type2.py

No-LLM demo: test Track 2 SymPy solver on 20 rows from Physics_Problems_Text_Only.csv.

Bypasses physics_parser (uses regex extractor) and explainer (no LLM needed).
Tests the core: formula_rag -> sympy_solver -> cot_builder -> self_verifier

Run:
    python scripts/demo_type2.py
    python scripts/demo_type2.py --limit 50
"""

import argparse
import csv
import math
import os
import re
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.type2.type2_classifier import PhysicsClassifier, PhysicsQuestionType
from pipeline.type2.formula_rag import formula_rag_node
from pipeline.type2.sympy_solver import sympy_solver_node
from pipeline.type2.cot_builder import cot_builder_node
from pipeline.type2.type2_validation import validate_sympy_result

CSV_PATH = "data/train/Physics_Problems_Text_Only.csv"
TOLERANCE = 0.02   # 2% relative tolerance for answer comparison

# Convert expected-answer units to SI base for fair comparison with SymPy output
_EXPECTED_UNIT_SI: dict[str, float] = {
    "pF": 1e-12, "nF": 1e-9, "uF": 1e-6, "μF": 1e-6, "mF": 1e-3, "F": 1.0,
    "mΩ": 1e-3, "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
    "uA": 1e-6, "μA": 1e-6, "mA": 1e-3, "A": 1.0,
    "mV": 1e-3, "V": 1.0, "kV": 1e3,
    "mW": 1e-3, "W": 1.0, "kW": 1e3,
    "uJ": 1e-6, "μJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
    "nC": 1e-9, "uC": 1e-6, "μC": 1e-6, "mC": 1e-3, "C": 1.0,
    "uH": 1e-6, "mH": 1e-3, "H": 1.0,
    "N": 1.0, "N/C": 1.0, "V/m": 1.0,
}


# ══════════════════════════════════════════════════════════════
# Unit conversion table (prefix+base → SI factor)
# ══════════════════════════════════════════════════════════════

_UNIT_FACTORS: dict[str, float] = {
    # Capacitance
    "pF": 1e-12, "nF": 1e-9, "μF": 1e-6, "uF": 1e-6, "mF": 1e-3, "F": 1.0,
    # Resistance
    "mΩ": 1e-3, "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
    # Current
    "μA": 1e-6, "uA": 1e-6, "mA": 1e-3, "A": 1.0, "kA": 1e3,
    # Voltage
    "μV": 1e-6, "mV": 1e-3, "V": 1.0, "kV": 1e3,
    # Power
    "μW": 1e-6, "mW": 1e-3, "W": 1.0, "kW": 1e3, "MW": 1e6,
    # Energy
    "μJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
    # Charge
    "nC": 1e-9, "μC": 1e-6, "uC": 1e-6, "mC": 1e-3, "C": 1.0,
    # Inductance
    "μH": 1e-6, "mH": 1e-3, "H": 1.0,
    # Length (for distance-based formulas)
    "mm": 1e-3, "cm": 1e-2, "m": 1.0, "km": 1e3,
    # Frequency
    "Hz": 1.0, "kHz": 1e3, "MHz": 1e6,
    # Force
    "N": 1.0,
}

# Some formulas use U for voltage, others V. Inject both so either formula works.
_SYM_VOLTAGE_ALIASES = {"U", "u"}


# ══════════════════════════════════════════════════════════════
# Regex-based given-value extractor (replaces LLM physics_parser)
# ══════════════════════════════════════════════════════════════

# Matches: SYM = MANTISSA [× 10^EXP] [UNIT]
# Examples: C = 100 μF   q1 = 6 × 10^-8 C   U = 30 V   k = 9 × 10^9 N
_ASSIGN_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'              # symbol =
    r'([\d.]+)'                               # mantissa
    r'(?:\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'  # × 10^exp (optional, use hex for ×)
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'   # unit prefix+base (optional)
)

# Verb-context target detector: "calculate the energy" → "E"
_VERB_TARGET_MAP = {
    "energy": "E", "resistance": "R", "voltage": "V", "potential difference": "V",
    "current": "I", "power": "P", "charge": "Q", "capacitance": "C",
    "force": "F", "frequency": "f", "inductance": "L",
    "electric field": "E_field", "field strength": "E_field",
    "electric potential": "V", "potential energy": "E",
}
_VERB_PAT = re.compile(
    r'\b(?:calculate|find|determine|compute|what\s+is)\s+(?:the\s+)?'
    r'((?:[a-zA-Z]+\s+){0,2}[a-zA-Z]+)',
    re.IGNORECASE,
)

def detect_find_from_verb(question: str) -> Optional[str]:
    """Extract target variable from verb context ('calculate the force' → 'F')."""
    for m in _VERB_PAT.finditer(question):
        noun = m.group(1).lower().strip()
        for kw, sym in _VERB_TARGET_MAP.items():
            if kw in noun:
                return sym
    return None


def extract_given(question: str) -> dict[str, float]:
    """
    Extract {symbol: SI_value} from question text via regex.
    Handles: C = 100 μF, q1 = 6 × 10^-8 C, k = 9 × 10^9 N m^2/C^2
    """
    given: dict[str, float] = {}

    for m in _ASSIGN_PAT.finditer(question):
        sym = m.group(1)
        mantissa = float(m.group(2))
        exp_str = m.group(3)
        unit_str = m.group(4) or ""

        val = mantissa
        if exp_str:
            val *= 10 ** int(exp_str.replace("−", "-"))

        factor = _UNIT_FACTORS.get(unit_str, 1.0)
        val_si = val * factor

        given[sym] = val_si

        # Voltage aliases: some formulas use V, others U — inject both
        if sym in _SYM_VOLTAGE_ALIASES:
            given["V"] = val_si

    return given


# ══════════════════════════════════════════════════════════════
# Expected answer parser
# ══════════════════════════════════════════════════════════════

def parse_expected(answer_str: str) -> Optional[float]:
    """
    Parse CSV answer column to float.
    Handles: "0.045", "24.45 x 10^-3", "8e-10"
    Returns None for complex LaTeX expressions (those containing backslash).
    """
    s = answer_str.strip()
    if not s:
        return None
    # Skip LaTeX / complex expressions
    if "\\" in s or "sqrt" in s.lower() or "," in s:
        return None

    # Normalize minus signs and multiply signs
    s = s.replace("−", "-").replace("×", "*")
    # "24.45 * 10^-3" → "24.45e-3"
    s = re.sub(r'\s*\*\s*10\^([-]?\d+)', r'e\1', s)
    s = s.replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


# ══════════════════════════════════════════════════════════════
# Demo runner
# ══════════════════════════════════════════════════════════════

def run_demo(limit: int = 20) -> None:
    clf = PhysicsClassifier()

    rows: list[dict] = []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            if len(rows) >= limit:
                break

    correct = wrong = fallback = skipped = 0
    detail_rows: list[tuple] = []

    for row in rows:
        qid = row["id"]
        question = row["question"]
        expected_str = row.get("answer", "")
        expected_unit_str = row.get("unit", "").strip()
        expected_val_raw = parse_expected(expected_str)
        # Convert expected to SI base using its unit column
        if expected_val_raw is not None:
            expected_val = expected_val_raw * _EXPECTED_UNIT_SI.get(expected_unit_str, 1.0)
        else:
            expected_val = None

        # 1. Classify (no LLM)
        classified = clf.classify_physics(question)

        # Verb-context detector overrides classifier (handles "charge" keyword noise)
        find = detect_find_from_verb(question) or classified.target_variable or ""

        # 2. Extract given values via regex (replaces physics_parser LLM call)
        given = extract_given(question)

        parsed_physics = {
            "given": given,
            "find": find,
            "domain": classified.domain,
            "formulas": [],
            "units": {},
            "question_type": classified.question_type.value,
        }

        state: dict = {
            "question": question,
            "parsed_physics": parsed_physics,
            "confidence": 1.0,
        }

        # 3. FormulaRAG
        state = formula_rag_node(state)

        # 4. SymPy solver
        state = sympy_solver_node(state)

        # 5. Self-verifier
        sympy_result = state.get("sympy_result", {})
        got_str = sympy_result.get("answer", "")
        source = sympy_result.get("source", "?")
        confidence = state.get("confidence", 1.0)

        try:
            val = float(got_str) if got_str else None
            vr = validate_sympy_result(val, classified.target_variable)
            if not vr.is_valid:
                confidence = 0.4
        except Exception:
            pass

        # 6. CoT
        state = cot_builder_node(state)

        # 7. Evaluate
        if source == "llm_fallback" or not got_str:
            tag = "FALLBACK"
            fallback += 1
        elif expected_val is None:
            tag = "SKIP"
            skipped += 1
        else:
            try:
                got_val = float(got_str)
                if abs(expected_val) > 1e-15:
                    rel_err = abs(got_val - expected_val) / abs(expected_val)
                else:
                    rel_err = abs(got_val - expected_val)
                if rel_err <= TOLERANCE:
                    tag = "CORRECT"
                    correct += 1
                else:
                    tag = f"WRONG({rel_err:.0%})"
                    wrong += 1
            except ValueError:
                tag = "PARSE_ERR"
                wrong += 1

        formula_used = ""
        if state.get("parsed_physics", {}).get("formulas"):
            formula_used = state["parsed_physics"]["formulas"][0][:25]

        expected_display = f"{expected_val:.6g}" if expected_val is not None else expected_str
        detail_rows.append((
            qid, tag, expected_display, got_str,
            find or "?",
            classified.domain[:6],
            source[:8],
            formula_used,
        ))

    # -- Print table ------------------------------------------
    W = 100
    print(f"\n{'-' * W}")
    print(f"{'ID':<8} {'RESULT':<13} {'EXPECTED':<14} {'GOT':<12} {'FIND':<5} {'DOM':<7} {'SRC':<9} FORMULA")
    print(f"{'-' * W}")
    for r in detail_rows:
        print(f"{r[0]:<8} {r[1]:<13} {r[2]:<14} {r[3]:<12} {r[4]:<5} {r[5]:<7} {r[6]:<9} {r[7]}")
    print(f"{'-' * W}")

    total_eval = correct + wrong
    print(f"\nSummary ({limit} questions):")
    print(f"  CORRECT  : {correct}")
    print(f"  WRONG    : {wrong}")
    print(f"  FALLBACK : {fallback}  (SymPy could not solve — needs LLM or more formulas)")
    print(f"  SKIP     : {skipped}  (complex answer string, could not parse)")
    if total_eval > 0:
        print(f"  Accuracy : {correct}/{total_eval} = {correct / total_eval:.1%}  (SymPy-solvable subset)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run_demo(args.limit)

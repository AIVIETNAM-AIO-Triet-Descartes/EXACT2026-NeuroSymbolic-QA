import re
import math
from typing import Optional, Union, List, Dict, Set
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

# Table mapping prefix -> coefficient to convert units to SI base representation.
# Taken from scripts/demo_type2.py
_EXPECTED_UNIT_SI: Dict[str, float] = {
    "pF": 1e-12, "nF": 1e-9, "uF": 1e-6, "μF": 1e-6, "mF": 1e-3, "F": 1.0,
    "mΩ": 1e-3, "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
    "uA": 1e-6, "μA": 1e-6, "mA": 1e-3, "A": 1.0,
    "mV": 1e-3, "V": 1.0, "kV": 1e3,
    "mW": 1e-3, "W": 1.0, "kW": 1e3,
    "uJ": 1e-6, "μJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
    "nC": 1e-9, "uC": 1e-6, "μC": 1e-6, "mC": 1e-3, "C": 1.0,
    "uH": 1e-6, "mH": 1e-3, "H": 1.0,
    "N": 1.0, "N/C": 1.0, "V/m": 1.0, "kV/m": 1e3, "MV/m": 1e6, "degree": 1.0,
}

def parse_braced(text: str, start_idx: int) -> tuple[str, int]:
    """Find the content inside the brace starting at start_idx."""
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start_idx+1:i], i
    raise ValueError("Unbalanced braces")

def resolve_latex_commands(s: str) -> str:
    """Preprocess LaTeX fraction and square root commands into standard algebraic forms."""
    # Normalize forward slash LaTeX mistakes (e.g. /frac instead of \frac)
    # We target common LaTeX commands to avoid altering standard division (e.g. 1/2, a/b)
    latex_cmds = [
        "frac", "sqrt", "pi", "times", "cdot", "left", "right", "pm", "approx",
        "alpha", "beta", "theta", "mu", "sigma", "omega", "lambda", "delta", "gamma",
        "log", "ln", "sin", "cos", "tan", "cot", "sec", "csc", "deg", "div"
    ]
    pattern = r'/(' + '|'.join(latex_cmds) + r')\b'
    s = re.sub(pattern, r'\\\1', s, flags=re.IGNORECASE)

    # Resolve \frac{A}{B}
    while True:
        idx = s.find(r"\frac{")
        if idx == -1:
            break
        try:
            arg1, end1 = parse_braced(s, idx + 5)
            # Find the second argument: search for '{' after end1
            next_idx = end1 + 1
            while next_idx < len(s) and s[next_idx].isspace():
                next_idx += 1
            if next_idx < len(s) and s[next_idx] == '{':
                arg2, end2 = parse_braced(s, next_idx)
                s = s[:idx] + f"(({arg1})/({arg2}))" + s[end2+1:]
            else:
                break
        except ValueError:
            break

    # Resolve \sqrt{A}
    while True:
        idx = s.find(r"\sqrt{")
        if idx == -1:
            break
        try:
            arg, end = parse_braced(s, idx + 5)
            s = s[:idx] + f"sqrt({arg})" + s[end+1:]
        except ValueError:
            break

    return s

def parse_number(s: str) -> Optional[float]:
    """
    Parse a numeric string to a float.
    Handles basic numbers, scientific notation, LaTeX fractions, and labeled values.
    Returns None if the string is unparseable.
    """
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None

    # Strip percentage signs so "50%" is parsed as "50"
    s = s.replace("%", "")

    # Handle equations/labeled values (e.g. I_D1=1.0)
    if "=" in s:
        parts = s.split("=")
        s = parts[-1].strip()

    # Preprocess LaTeX commands
    s = resolve_latex_commands(s)

    # Normalize mathematical/LaTeX notation
    s = s.replace(r"\pi", "pi")
    s = s.replace(r"\times", "*")
    s = s.replace(r"\cdot", "*")
    s = s.replace("×", "*")
    s = s.replace("·", "*")
    s = s.replace("−", "-")  # unicode minus

    # Convert space-separated dots to * (e.g. 4 . 10^{-9} -> 4 * 10^{-9})
    s = re.sub(r'\s+\.\s+', ' * ', s)

    # Convert Unicode superscript exponents (e.g. 10⁻³, 10⁷)
    superscript_map = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        '⁺': '+', '⁻': '-'
    }
    
    def replace_superscript(match):
        sups = match.group(1)
        normal = "".join(superscript_map.get(c, c) for c in sups)
        return f"**({normal})"
        
    s = re.sub(r'([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)', replace_superscript, s)

    # Convert scientific notation (e.g. 4.5 x 10^-2)
    s = re.sub(r'(\d+)\s*[xX]\s*(10)', r'\1 * \2', s)

    # Convert LaTeX curly brace powers like ^{ -27 } to **( -27 )
    while True:
        idx = s.find("^{")
        if idx == -1:
            break
        try:
            arg, end = parse_braced(s, idx + 1)
            s = s[:idx] + f"**({arg})" + s[end+1:]
        except ValueError:
            break

    # Convert other '^' to '**'
    s = s.replace("^", "**")

    # Use SymPy to parse the normalized mathematical expression safely
    try:
        transformations = standard_transformations + (implicit_multiplication_application,)
        expr = parse_expr(s, transformations=transformations)
        # If expression has free variables/symbols, it's not a numeric value.
        if expr.free_symbols:
            return None
        # Evaluate to float
        val = float(expr.evalf())
        return val
    except Exception:
        return None

def to_si(value: float, unit: str) -> float:
    """
    Convert a given value to its SI base unit representation.
    """
    if not unit:
        return value
    unit_clean = unit.strip()
    if unit_clean in ("", "-", "—"):
        return value
    factor = _EXPECTED_UNIT_SI.get(unit_clean)
    if factor is not None:
        return value * factor
    return value

def split_multi(s: str) -> list[str]:
    """
    Split a multi-answer string by ';' and strip whitespace.
    """
    if not isinstance(s, str):
        return []
    if not s.strip():
        return []
    return [part.strip() for part in s.split(";") if part.strip()]

def normalize_text(text: str) -> Set[str]:
    """Normalize qualitative text by lowercasing, removing punctuation, and splitting into a set of tokens."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return {word for word in text.split() if word}

def compare_answer(pred: str, gold: str, gold_unit: str = "", *, rel_tol: float = 0.05) -> dict:
    """
    Compare a predicted answer to a gold answer.
    Returns a dict with {"correct": bool, "kind": str, "detail": str, "needs_review": bool}.
    """
    if pred is None:
        pred = ""
    if gold is None:
        gold = ""
    
    pred_str = str(pred).strip()
    gold_str = str(gold).strip()

    # 1. Check if it's a multi-answer
    if ";" in gold_str:
        gold_parts = split_multi(gold_str)
        pred_parts = split_multi(pred_str)
        
        # If number of parts mismatch, it's incorrect
        if len(gold_parts) != len(pred_parts):
            return {
                "correct": False,
                "kind": "multi",
                "detail": f"Length mismatch: pred has {len(pred_parts)} parts, gold has {len(gold_parts)} parts.",
                "needs_review": False
            }
        
        unit_parts = split_multi(gold_unit)
        correct = True
        details = []
        for i in range(len(gold_parts)):
            p_part = pred_parts[i]
            g_part = gold_parts[i]
            u_part = unit_parts[i] if i < len(unit_parts) else ""
            res_part = compare_answer(p_part, g_part, u_part, rel_tol=rel_tol)
            if not res_part["correct"]:
                correct = False
            details.append(f"[{i}]: {res_part.get('detail', '')}")
            
        return {
            "correct": correct,
            "kind": "multi",
            "detail": " | ".join(details),
            "needs_review": False
        }

    # 2. Check if yes/no
    if gold_str.lower() in ("yes", "no"):
        correct = (pred_str.lower() == gold_str.lower())
        return {
            "correct": correct,
            "kind": "yes_no",
            "detail": f"Pred: '{pred_str}', Gold: '{gold_str}'",
            "needs_review": False
        }

    # 3. Check if numeric
    val_gold = parse_number(gold_str)
    if val_gold is not None:
        val_pred = parse_number(pred_str)
        if val_pred is None:
            return {
                "correct": False,
                "kind": "unparseable",
                "detail": f"Could not parse prediction '{pred_str}' as a number.",
                "needs_review": False
            }
        
        val_gold_si = to_si(val_gold, gold_unit)
        val_pred_si = val_pred  # pred is already in SI base unit

        if abs(val_gold_si) > 1e-15:
            error = abs(val_pred_si - val_gold_si) / abs(val_gold_si)
        else:
            error = abs(val_pred_si - val_gold_si)

        correct = (error <= rel_tol)
        return {
            "correct": correct,
            "kind": "numeric",
            "detail": f"Pred SI: {val_pred_si}, Gold SI: {val_gold_si}, Error: {error:.4%}",
            "needs_review": False
        }

    # 4. Qualitative comparison
    pred_tokens = normalize_text(pred_str)
    gold_tokens = normalize_text(gold_str)
    
    if not gold_tokens:
        correct = (pred_tokens == gold_tokens)
        overlap = 1.0 if correct else 0.0
    else:
        intersection = gold_tokens.intersection(pred_tokens)
        overlap = len(intersection) / len(gold_tokens)
        correct = (overlap >= 0.75)

    return {
        "correct": correct,
        "kind": "qualitative",
        "detail": f"Token overlap: {overlap:.2%} (Intersection: {intersection}, Gold tokens: {gold_tokens})",
        "needs_review": True
    }

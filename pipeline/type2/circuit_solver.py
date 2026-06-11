"""
pipeline/type2/circuit_solver.py

Parallel-circuit solver for the THCB "circuit" rows (lamps/resistors in parallel)
and any circuits-domain question the scalar `_solve_single` can't express —
multi-branch problems that ask for several quantities at once (per-branch current
+ total), the equivalent resistance, or total/per-lamp power.

Design (PAL-aligned): this module does ONLY the arithmetic from a numeric `given`
dict. The `given` is produced upstream by regex (`SYM = value`) or — for phrasal
inputs like "8Ω lamp", "voltage of 8V" — by the LLM augment in physics_parser.
The solver never calls the LLM and never hallucinates numbers.

Relations (parallel resistor network):
  branch current      I_i      = U / R_i
  equivalent R (∥)    R_p      = 1 / Σ(1/R_i)         (two branches: R1·R2/(R1+R2))
  total current       I_total  = Σ I_i   (= U / R_p)
  power               P        = U · I   ;  P_total = Σ P_i ;  P_each = P_total / n
  KCL                 I_total  = Σ I_branch  (missing branch = I_total − Σ others)

Returns a SolverResult-shaped dict (source="circuit") or None if it can't solve
(caller then falls back to LLM). Multi-answer joins values with "; " (dataset
convention, e.g. "1.0; 1.0; 2.0"); answer_compare strips any gold labels.
"""

import re
from typing import Optional

from loguru import logger

# Subscript digits → ASCII so "R₁"/"R₂"/"I_D₁" normalise to R1/R2/I_D1.
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _norm_key(k: str) -> str:
    return k.translate(_SUB)


def _collect(given: dict) -> dict:
    """Normalise given keys and bucket the circuit quantities."""
    g = {_norm_key(k): v for k, v in given.items()}
    out: dict = {"U": None, "R": [], "I_branch": [], "P_branch": [],
                 "I_total": None, "P_total": None, "n": None}
    for k, v in g.items():
        try:
            val = float(v)
        except (TypeError, ValueError):
            continue
        ku = k.upper()
        if ku in ("U", "V", "U_SOURCE", "V_SOURCE"):
            out["U"] = val
        elif ku in ("I_TOTAL", "ITOTAL", "I_TONG"):
            out["I_total"] = val
        elif ku in ("P_TOTAL", "PTOTAL"):
            out["P_total"] = val
        elif ku == "N":
            out["n"] = val
        elif re.fullmatch(r"R_?(?:TD|P|TOTAL)", ku):
            pass  # equivalent-R target (R_td/R_p/R_total), not an input branch
        elif re.fullmatch(r"R\d*|R_D\d*", ku):       # R, R1, R2, R_D1...
            out["R"].append(val)
        elif re.fullmatch(r"I(_?D)?\d*", ku):         # I, I1, I_D1...
            out["I_branch"].append(val)
        elif re.fullmatch(r"P(_?D)?\d*", ku):         # P, P1, P_D1...
            out["P_branch"].append(val)
    return out


def _wants(question: str) -> dict:
    """Detect which quantities the question asks for."""
    q = question.lower()
    return {
        "each_current": bool(re.search(r"current\s+(?:through|in|of)\s+each|"
                                       r"(?:through|in)\s+each\s+(?:lamp|bulb|resistor|branch)|"
                                       r"current\s+through\s+each", q)),
        "total_current": bool(re.search(r"total\s+current|current\s+.*\btotal", q)),
        "equiv_r": bool(re.search(r"equivalent\s+resistance|total\s+resistance|"
                                  r"\br_?td\b|combined\s+resistance", q)),
        "total_power": bool(re.search(r"total\s+power|power\s+consumption|total\s+.*power", q)),
        "each_power": bool(re.search(r"power\s+of\s+each|each\s+(?:lamp|bulb)('?s)?\s+\w*\s*power", q)),
        "current": bool(re.search(r"\bcurrent\b", q)),
        "power": bool(re.search(r"\bpower\b", q)),
    }


def _fmt(x: float) -> str:
    return f"{x:.4g}"


def solve_circuit(parsed: dict, question: str = "") -> Optional[dict]:
    """Solve a parallel-circuit question. Returns SolverResult dict or None."""
    try:
        # Guard: only fire on parallel DC lamp/resistor networks. Without this,
        # series AC-RLC questions misclassified as domain="circuits" (e.g. CH "circuit
        # AB with R1, R2 + inductor, LCω²=1") get hijacked and produce wrong answers
        # instead of falling back. Every THCB circuit row says parallel/lamp/bulb.
        if not re.search(r"parallel|lamp|bulb", question, re.IGNORECASE):
            return None
        given = parsed.get("given", {}) or {}
        c = _collect(given)
        w = _wants(question)
        U, Rs = c["U"], c["R"]
        steps: list[str] = []

        # Number of (identical) lamps, e.g. "Two lamps", "both bulbs".
        _NMAP = {"two": 2, "three": 3, "four": 4, "both": 2, "2": 2, "3": 3, "4": 4}
        mn = re.search(r"\b(two|three|four|both|2|3|4)\b\s+(?:identical\s+)?"
                       r"(?:lamps?|bulbs?|resistors?|branches|branch|lights?)",
                       question.lower())
        n_lamps = int(c["n"]) if c["n"] else (_NMAP.get(mn.group(1)) if mn else None)

        # Branch currents from U and each R (parallel → same U across branches).
        branch_I = [U / r for r in Rs if r] if (U is not None and Rs) else []
        # Identical lamps given a single R: replicate to n branches ONLY when the
        # total is also asked (069 asks "each" only → one value; 066 asks "each AND
        # total" → n branch values + their sum).
        if len(branch_I) == 1 and n_lamps and n_lamps > 1 and w["total_current"]:
            branch_I = branch_I * n_lamps

        # ── equivalent resistance (R_p) ───────────────────────────────────────
        if w["equiv_r"] and len(Rs) >= 2:
            inv = sum(1.0 / r for r in Rs if r)
            if inv:
                Rp = 1.0 / inv
                steps.append(f"Parallel: 1/R_td = Σ(1/Rᵢ) = {_fmt(inv)} → R_td = {_fmt(Rp)} Ω")
                return {"answer": _fmt(Rp), "unit": "Ω", "steps": steps, "source": "circuit"}

        # ── per-branch current (+ optional total) — multi-answer ──────────────
        if w["each_current"] and branch_I:
            parts = [_fmt(i) for i in branch_I]
            units = ["A"] * len(branch_I)
            steps.append("Each branch (parallel, same U): Iᵢ = U/Rᵢ = "
                         + ", ".join(parts) + " A")
            if w["total_current"]:
                it = sum(branch_I)
                parts.append(_fmt(it))
                units.append("A")
                steps.append(f"Total: I_total = ΣIᵢ = {_fmt(it)} A")
            return {"answer": "; ".join(parts), "unit": "; ".join(units),
                    "steps": steps, "source": "circuit"}

        # ── total current ─────────────────────────────────────────────────────
        if w["total_current"]:
            it = None
            if c["I_branch"]:                       # KCL: sum given branch currents
                it = sum(c["I_branch"])
                steps.append(f"KCL: I_total = ΣI_branch = {_fmt(it)} A")
            elif branch_I:                          # from U and parallel R's
                it = sum(branch_I)
                steps.append(f"I_total = Σ U/Rᵢ = {_fmt(it)} A")
            if it is not None:
                return {"answer": _fmt(it), "unit": "A", "steps": steps, "source": "circuit"}

        # ── total power ───────────────────────────────────────────────────────
        if w["total_power"]:
            p = None
            if c["P_branch"]:
                p = sum(c["P_branch"])
                steps.append(f"P_total = ΣPᵢ = {_fmt(p)} W")
            elif U is not None and c["I_total"] is not None:
                p = U * c["I_total"]
                steps.append(f"P_total = U·I_total = {_fmt(p)} W")
            elif U is not None and branch_I:
                p = U * sum(branch_I)
                steps.append(f"P_total = U·ΣIᵢ = {_fmt(p)} W")
            if p is not None:
                return {"answer": _fmt(p), "unit": "W", "steps": steps, "source": "circuit"}

        # ── per-lamp power of n identical lamps (P_total / n) ─────────────────
        if w["each_power"] and c["P_total"] is not None:
            n = n_lamps or 2
            pe = c["P_total"] / n
            steps.append(f"Identical lamps: P_each = P_total/{n} = {_fmt(pe)} W")
            return {"answer": _fmt(pe), "unit": "W", "steps": steps, "source": "circuit"}

        # ── single branch current from U,R or P,U ─────────────────────────────
        if w["current"] and not w["each_current"]:
            if branch_I and len(branch_I) == 1:
                return {"answer": _fmt(branch_I[0]), "unit": "A",
                        "steps": [f"I = U/R = {_fmt(branch_I[0])} A"], "source": "circuit"}
            if c["P_branch"] and U:                 # I = P/U
                i = c["P_branch"][0] / U
                return {"answer": _fmt(i), "unit": "A",
                        "steps": [f"I = P/U = {_fmt(i)} A"], "source": "circuit"}

        logger.debug(f"[CIRCUIT] no rule matched (collected={c}, wants={w})")
        return None
    except Exception as e:
        logger.warning(f"[CIRCUIT] failed: {e}")
        return None

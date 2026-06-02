"""
pipeline/type2/resonance_solver.py

Dedicated Yes/No resonance solver for the CHLT prefix (T2-14, impl_plan §3.7).

CHLT asks "does the circuit experience resonance?" — no equation to solve, no
formula to retrieve. Compute the resonant frequency f0 = 1/(2π√(LC)) and compare
it to the driving frequency f with a relative tolerance. Deterministic → the
sympy_solver_node confidence map treats source="resonance" like "sympy" (1.0).

Note on R: every CHLT row carries an R value, but R plays no part in the Yes/No
check — f0 depends only on L and C (at resonance X_L = X_C → Z = R). R is
extracted by the parser and intentionally ignored here.

Dispatch (sympy_solver_node, T2-16): only when q_type == YES_NO AND
domain == "ac_circuits" AND given has L, C, f — guard against qualitative
questions misrouted into YES_NO (weakness #7 over-routing risk).
"""

import math
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Relative tolerance for f ≈ f0. CHLT ground truths resolve cleanly at 2%:
#   CHLT001: f=40 Hz vs f0≈50.3 Hz  → rel 0.20  → No
#   CHLT002: f=35.6 Hz vs f0≈35.59 → rel 0.0003 → Yes
_REL_TOL = 0.02

# Phrasal frequency fallback — regex_extract only catches "f = 40 Hz" assignments.
# CHLT wording also uses "at a frequency of 79.6 Hz" / "at 50 Hz".
_FREQ_PHRASE_PAT = re.compile(
    r'(?:frequency\s+(?:of\s+)?|at\s+)([\d.]+)\s*(k|M)?Hz',
    re.IGNORECASE,
)
_FREQ_FACTOR = {"k": 1e3, "m": 1e6, "": 1.0}


def _extract_frequency_phrasal(question: str) -> Optional[float]:
    """Fallback: pull driving frequency from phrasal forms regex_extract misses."""
    m = _FREQ_PHRASE_PAT.search(question)
    if not m:
        return None
    prefix = (m.group(2) or "").lower()
    try:
        return float(m.group(1)) * _FREQ_FACTOR.get(prefix, 1.0)
    except ValueError:
        return None


def solve_resonance(parsed: dict, question: str = "") -> dict:
    """
    Yes/No resonance check for CHLT problems.

    Input  : parsed["given"] with L (H), C (F), f (Hz) in SI.
             R may be present — intentionally ignored.
             f falls back to phrasal extraction from `question` when missing.
    Output : {"answer": "Yes"|"No", "unit": "", "steps": [...], "source": "resonance"}
             On missing/invalid data: source="llm_fallback" (LLM CoT takes over).
    Never raises.
    """
    fallback = {"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}

    try:
        given = parsed.get("given", {}) or {}
        L = given.get("L")
        C = given.get("C")
        f = given.get("f")
        if f is None and question:
            f = _extract_frequency_phrasal(question)

        # All three must be present, numeric, positive
        try:
            L, C, f = float(L), float(C), float(f)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            logger.warning(
                f"[RESONANCE] missing/non-numeric L/C/f (L={L}, C={C}, f={f}) — fallback"
            )
            return fallback
        if L <= 0 or C <= 0 or f <= 0:
            logger.warning(f"[RESONANCE] non-positive L/C/f (L={L}, C={C}, f={f}) — fallback")
            return fallback

        f0 = 1.0 / (2.0 * math.pi * math.sqrt(L * C))
        rel = abs(f - f0) / f0
        answer = "Yes" if rel < _REL_TOL else "No"

        steps = [
            f"Given: L = {L:.6g} H, C = {C:.6g} F, f = {f:.6g} Hz"
            + (f", R = {given['R']:.6g} Ω (not used for resonance check)" if "R" in given else ""),
            f"Resonant frequency: f0 = 1/(2π√(LC)) = 1/(2π√({L:.6g}×{C:.6g})) ≈ {f0:.6g} Hz",
            f"Compare: |f − f0|/f0 = |{f:.6g} − {f0:.6g}|/{f0:.6g} = {rel:.4g} "
            f"{'<' if rel < _REL_TOL else '≥'} {_REL_TOL} → "
            f"{'resonance occurs' if answer == 'Yes' else 'not resonant'}",
        ]
        logger.info(f"[RESONANCE] f={f:.6g} f0={f0:.6g} rel={rel:.4g} → {answer}")
        return {"answer": answer, "unit": "", "steps": steps, "source": "resonance"}

    except Exception as e:
        logger.error(f"[RESONANCE] unexpected failure: {e}")
        return fallback

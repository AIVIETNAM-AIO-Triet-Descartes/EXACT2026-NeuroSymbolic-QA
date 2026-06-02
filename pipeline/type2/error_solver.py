"""
pipeline/type2/error_solver.py

Dedicated measurement-error solver for the THCB prefix (T2-15, impl_plan §3.8).

Explicit formula computation — no sympy.solve(). Handles BOTH question types:
  ERROR_CALC   — single quantity  → answer "3.571", unit "%"
  MULTI_ANSWER — ≥2 quantities    → answer "0.6; 1.2", unit "cm; %"
(MULTI_ANSWER is currently emitted by the classifier only for domain
"measurement"/THCB, so the multi branch lives here, not in sympy_solver.)

THCB values are phrasal ("least count 0.2 V", "reads 5.6 V", "12.0 ± 0.2 Ω") —
regex_extract's `sym = value` patterns miss them (weakness #3 residual), so this
module owns its own THCB parser. Values are kept in their ORIGINAL units (the
dataset expects "0.6 cm", not 0.006 m) — no SI conversion here.

Ground-truth calibration (track2_data_info.md / dataset):
  THCB001  least count 0.1 A → absolute error 0.1 A   ⇒ Δx = least_count (NOT /2)
  THCB002  lc 0.2 V, reads 5.6 V → 3.57 %             ⇒ δ = lc/reading×100
  THCB087  true 50.0, measured 49.4 → "0.6; 1.2"      ⇒ δ uses TRUE value as denominator

Sub-cases implemented: plus-minus notation, true-vs-measured, instrument least
count (+reading), mean + mean-absolute random error of repeated measurements.
Error propagation (F-045/F-046 — δZ=δA+δB) is NOT implemented yet → falls back
to LLM (source="llm_fallback"); Member 3 extension point.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_NUM = r'([\d.]+)'
_UNIT = r'([a-zA-ZΩμµ°%]+)?'

# "12.0 ± 0.2 Ω" / "12.0 +/- 0.2 ohm"
_PLUSMINUS_PAT = re.compile(
    _NUM + r'\s*(?:±|\+/-|\+-)\s*' + _NUM + r'\s*' + _UNIT
)
# "least count of 0.2 V" / "least count = 0.1 A"
_LEAST_COUNT_PAT = re.compile(
    r'least\s+count\s*(?:of|is|=|:)?\s*' + _NUM + r'\s*' + _UNIT, re.IGNORECASE
)
# "0.2 V least count" (reversed order, THCB002 wording)
_LEAST_COUNT_REV_PAT = re.compile(
    _NUM + r'\s*' + _UNIT + r'\s+least\s+count', re.IGNORECASE
)
# "reads 5.6 V" / "reading of 5.6" / "shows 5.6 V"
_READS_PAT = re.compile(
    r'(?:reads?|reading|shows?|displays?|indicates?)\s*(?:of|is|=|:)?\s*'
    + _NUM + r'\s*' + _UNIT, re.IGNORECASE
)
# "true value = 50.0 cm"
_TRUE_PAT = re.compile(
    r'true\s+value\s*(?:of|is|=|:)?\s*' + _NUM + r'\s*' + _UNIT, re.IGNORECASE
)
# "measured = 49.4 cm" / "measured value is 49.4"
_MEASURED_PAT = re.compile(
    r'measured(?:\s+value)?\s*(?:of|is|=|:)?\s*' + _NUM + r'\s*' + _UNIT, re.IGNORECASE
)
# Repeated measurements list: "2.04, 2.06, 2.05 s" (≥3 values)
_LIST_PAT = re.compile(r'((?:[\d.]+\s*[,;]\s*){2,}[\d.]+)\s*' + _UNIT)


def _fmt(x: float) -> str:
    return f"{x:.4g}"


def _parse_values(question: str) -> dict:
    """Extract THCB phrasal values. Returns {} keys: x, delta, x_true, x_measured,
    least_count, reading, values(list), unit."""
    out: dict = {}

    m = _PLUSMINUS_PAT.search(question)
    if m:
        out["x"] = float(m.group(1))
        out["delta"] = float(m.group(2))
        out["unit"] = m.group(3) or ""

    m = _TRUE_PAT.search(question)
    if m:
        out["x_true"] = float(m.group(1))
        out.setdefault("unit", m.group(2) or "")
    m = _MEASURED_PAT.search(question)
    if m:
        out["x_measured"] = float(m.group(1))
        out.setdefault("unit", m.group(2) or "")

    m = _LEAST_COUNT_PAT.search(question) or _LEAST_COUNT_REV_PAT.search(question)
    if m:
        out["least_count"] = float(m.group(1))
        out.setdefault("unit", m.group(2) or "")
    m = _READS_PAT.search(question)
    if m:
        out["reading"] = float(m.group(1))
        out.setdefault("unit", m.group(2) or "")

    m = _LIST_PAT.search(question)
    if m:
        try:
            out["values"] = [float(v) for v in re.split(r'[,;]\s*', m.group(1))]
            out.setdefault("unit", m.group(2) or "")
        except ValueError:
            pass

    return out


def solve_error(parsed: dict, question: str = "") -> dict:
    """
    Measurement-error computation for THCB problems.

    Output (single): {"answer": "3.571", "unit": "%", "steps": [...], "source": "error_calc"}
    Output (multi) : {"answer": "0.6; 1.2", "unit": "cm; %", "steps": [...], "source": "error_calc"}
    On unrecognized sub-case / missing data: source="llm_fallback". Never raises.
    """
    fallback = {"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}

    try:
        q_lower = question.lower()
        vals = _parse_values(question)
        unit = vals.get("unit", "") or ""
        steps: list[str] = []

        wants_abs = "absolute error" in q_lower or "absolute uncertainty" in q_lower
        wants_rel = bool(re.search(
            r'relative\s+(?:error|uncertainty)|percentage|percent\s+error', q_lower))
        wants_mean = bool(re.search(r'\bmean\b|\baverage\b', q_lower))

        delta: Optional[float] = None
        x_ref: Optional[float] = None  # denominator for relative error

        # ── Sub-case: mean + random error of repeated measurements ────────────
        if vals.get("values") and (wants_mean or wants_abs or wants_rel):
            xs = vals["values"]
            x_mean = sum(xs) / len(xs)
            delta_mean = sum(abs(x - x_mean) for x in xs) / len(xs)
            steps.append(f"Measurements: {xs} {unit}")
            steps.append(f"Mean: x̄ = Σxᵢ/n = {_fmt(x_mean)} {unit}")
            steps.append(f"Mean absolute error: Δx̄ = Σ|xᵢ−x̄|/n = {_fmt(delta_mean)} {unit}")
            delta, x_ref = delta_mean, x_mean
            if wants_mean and not (wants_abs or wants_rel):
                return {"answer": _fmt(x_mean), "unit": unit, "steps": steps,
                        "source": "error_calc"}

        # ── Sub-case: explicit ± notation ──────────────────────────────────────
        elif "delta" in vals and "x" in vals:
            delta, x_ref = vals["delta"], vals["x"]
            steps.append(f"Given: x = {_fmt(x_ref)} ± {_fmt(delta)} {unit}")

        # ── Sub-case: true vs measured value ──────────────────────────────────
        elif "x_true" in vals and "x_measured" in vals:
            delta = abs(vals["x_measured"] - vals["x_true"])
            x_ref = vals["x_true"]  # dataset convention (THCB087): denominator = true value
            steps.append(
                f"Given: true value = {_fmt(vals['x_true'])} {unit}, "
                f"measured = {_fmt(vals['x_measured'])} {unit}")
            steps.append(f"Absolute error: Δx = |measured − true| = {_fmt(delta)} {unit}")

        # ── Sub-case: instrument least count (+ optional reading) ─────────────
        elif "least_count" in vals:
            # Dataset convention (THCB001/002): Δx = least_count (not /2)
            delta = vals["least_count"]
            x_ref = vals.get("reading")
            steps.append(f"Instrument least count = {_fmt(delta)} {unit}")
            steps.append(f"Absolute (instrument) error: Δx = least count = {_fmt(delta)} {unit}")
            if x_ref is not None:
                steps.append(f"Reading: x = {_fmt(x_ref)} {unit}")

        if delta is None:
            logger.warning("[ERROR_SOLVER] no recognized sub-case — fallback "
                           f"(parsed keys: {list(vals)})")
            return fallback

        # ── Assemble requested quantities ──────────────────────────────────────
        rel: Optional[float] = None
        if wants_rel:
            if x_ref is None or x_ref == 0:
                logger.warning("[ERROR_SOLVER] relative error requested but no base value")
                return fallback
            rel = delta / x_ref * 100.0
            steps.append(f"Relative error: δ = Δx/x × 100 = {_fmt(delta)}/{_fmt(x_ref)} × 100 "
                         f"= {_fmt(rel)} %")

        # Multi-answer: join in question order (dataset convention "0.6; 1.2 | cm; %")
        if wants_abs and rel is not None:
            abs_first = q_lower.find("absolute") <= q_lower.find("relative") \
                if "relative" in q_lower else True
            pairs = [(_fmt(delta), unit), (_fmt(rel), "%")]
            if not abs_first:
                pairs.reverse()
            answer = "; ".join(p[0] for p in pairs)
            unit_out = "; ".join(p[1] for p in pairs)
            logger.info(f"[ERROR_SOLVER] multi-answer: {answer} | {unit_out}")
            return {"answer": answer, "unit": unit_out, "steps": steps,
                    "source": "error_calc"}

        if rel is not None:
            return {"answer": _fmt(rel), "unit": "%", "steps": steps, "source": "error_calc"}

        return {"answer": _fmt(delta), "unit": unit, "steps": steps, "source": "error_calc"}

    except Exception as e:
        logger.error(f"[ERROR_SOLVER] unexpected failure: {e}")
        return fallback

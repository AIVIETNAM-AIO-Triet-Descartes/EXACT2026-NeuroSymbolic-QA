"""
pipeline/type2/vector_solver.py

Handles multi-charge Coulomb vector problems that the scalar SymPy solver cannot.

Three strategies:
  A. FORCE+ANGLE  — two force magnitudes + angle in text → parallelogram law
  B. GEOMETRY     — charges at vertices/points → coordinate-based vector sum
  C. CENTER       — one charge at centroid of equilateral triangle

Integration: called from sympy_solver_node() before falling back to llm_fallback.
"""

import math
import re
from typing import Optional

import logging
logger = logging.getLogger(__name__)

K_E = 8.99e9  # N·m²/C²


# ── Helpers ───────────────────────────────────────────────────────────────────

def _coulomb_mag(q1: float, q2: float, r: float) -> float:
    return K_E * abs(q1) * abs(q2) / r ** 2


def _parallelogram(f1: float, f2: float, theta_deg: float) -> float:
    return math.sqrt(f1 ** 2 + f2 ** 2 + 2 * f1 * f2 * math.cos(math.radians(theta_deg)))


# Point-label → charge-index convention used across the dataset: A=q1, B=q2,
# C=q3, M=q0 (M is the test/probe charge). Used to map _place_three_points output
# (A,B,C positions) onto the right charges instead of sorted q_syms order.
_LETTER_IDX = {"A": 1, "B": 2, "C": 3, "M": 0}


def _charge_suffix(sym: str) -> Optional[int]:
    """Numeric index of a charge symbol (q1→1, q0→0); None if no digits."""
    m = re.search(r'\d+', sym)
    return int(m.group()) if m else None


def _place_three_points(r_ab: float, r_ac: float, r_bc: float) -> Optional[tuple]:
    """
    Place A at origin, B at (r_ab, 0), C computed from distances r_ac (A→C) and r_bc (B→C).
    Returns (A, B, C) as (x,y) tuples, or None if geometry is impossible.
    """
    A = (0.0, 0.0)
    B = (r_ab, 0.0)
    # Law of cosines for x: x²+y²=r_ac², (x-r_ab)²+y²=r_bc²
    # Subtract: x = (r_ac²+r_ab²-r_bc²) / (2*r_ab)
    x = (r_ac ** 2 + r_ab ** 2 - r_bc ** 2) / (2 * r_ab)
    y2 = r_ac ** 2 - x ** 2
    if y2 < -1e-12:
        return None
    C = (x, max(y2, 0.0) ** 0.5)
    return A, B, C


def _net_force_at_target(
    charges: list[tuple[str, float]],
    positions: dict[str, tuple[float, float]],
    target: str,
    k_val: float,
) -> tuple[float, list[str]]:
    """
    Compute net Coulomb force on `target` charge from all others.
    Returns (magnitude, steps).
    """
    q_target = dict(charges)[target]
    tx, ty = positions[target]
    fx = fy = 0.0
    steps = [f"Target: {target}={q_target:.3e} C at ({tx:.4f}, {ty:.4f}) m"]

    for sym, q_src in charges:
        if sym == target:
            continue
        sx, sy = positions[sym]
        dx, dy = tx - sx, ty - sy
        r = math.sqrt(dx ** 2 + dy ** 2)
        if r < 1e-15:
            logger.warning(f"[VECTOR_SOLVER] Charges {sym} and {target} at same position, skipping")
            continue

        f_mag = k_val * abs(q_src) * abs(q_target) / r ** 2
        same_sign = (q_src * q_target) > 0
        # Repulsion: force on target away from source (dx,dy direction)
        # Attraction: force on target toward source (−dx,−dy direction)
        sign = 1.0 if same_sign else -1.0
        fx += sign * f_mag * dx / r
        fy += sign * f_mag * dy / r
        steps.append(
            f"F({sym}→{target}): |F|={f_mag:.4e} N "
            f"({'repulsion' if same_sign else 'attraction'}), "
            f"dir=({sign*dx/r:.3f}, {sign*dy/r:.3f})"
        )

    net = math.sqrt(fx ** 2 + fy ** 2)
    steps.append(f"Sum: Fx={fx:.4e} N, Fy={fy:.4e} N")
    steps.append(f"Result: |F| = {net:.6g} N")
    return net, steps


# ── Strategy A: Force + Angle ─────────────────────────────────────────────────

_FORCE_N_PAT = re.compile(r'([\d]+(?:\.[\d]+)?)\s*N\b')
_ANGLE_DEG_PAT = re.compile(
    r'angle\s+of\s+([\d.]+)\s*°?|'
    r'at\s+(?:an\s+)?angle\s+of\s+([\d.]+)|'
    r'at\s+([\d.]+)\s*°?\s+to\s+each',
    re.IGNORECASE,
)


def _detect_angle(question: str) -> Optional[float]:
    q = question.lower()
    if "same direction" in q:
        return 0.0
    if "opposite direction" in q:
        return 180.0
    if "perpendicular" in q:
        return 90.0
    m = _ANGLE_DEG_PAT.search(question)
    if m:
        val = next(g for g in m.groups() if g is not None)
        return float(val)
    return None


def solve_force_angle(question: str, given: dict) -> Optional[dict]:
    """Two force magnitudes + angle → resultant via parallelogram law."""
    theta = _detect_angle(question)
    if theta is None:
        return None

    # Extract force magnitudes (N) from question text
    force_matches = _FORCE_N_PAT.findall(question)
    forces = [float(v) for v in force_matches]

    if len(forces) == 1:
        # "each with a magnitude of 5 N" → both forces equal
        if re.search(r'\beach\b', question, re.IGNORECASE):
            forces = [forces[0], forces[0]]

    if len(forces) < 2:
        # Fallback: check given dict for F1, F2
        f1 = given.get("F1") or given.get("F_1")
        f2 = given.get("F2") or given.get("F_2")
        if f1 and f2:
            forces = [float(f1), float(f2)]
        else:
            return None

    f1, f2 = forces[0], forces[1]
    result = _parallelogram(f1, f2, theta)
    steps = [
        f"Given: F1={f1} N, F2={f2} N, angle={theta}°",
        "Formula: F = sqrt(F1²+F2²+2·F1·F2·cos(θ))",
        f"F = sqrt({f1}²+{f2}²+2·{f1}·{f2}·cos({theta}°))",
        f"Result: F = {result:.6g} N",
    ]
    logger.info(f"[VECTOR_SOLVER] force+angle: F1={f1}, F2={f2}, θ={theta}° → {result:.6g} N")
    return {"answer": f"{result:.6g}", "unit": "N", "steps": steps, "source": "vector_solver"}


# ── Strategy B: General geometry (triangle / collinear) ───────────────────────

_TARGET_CHARGE_PAT = re.compile(
    r'(?:force\s+(?:acting\s+)?on|force\s+exerted\s+on|acting\s+on)\s+'
    r'(?:(?:the|an?|electric|electrostatic|resultant)\s+)*'  # optional adjectives
    r'(?:charge\s+(?:at\s+)?)?'
    r'(q[A-Za-z0-9_]*|charge\s+at\s+[A-Z])',
    re.IGNORECASE,
)


def _detect_target_charge(question: str, charge_syms: list[str]) -> Optional[str]:
    """Find which charge is the target ('force on q3' → 'q3')."""
    m = _TARGET_CHARGE_PAT.search(question)
    if m:
        raw = m.group(1).strip()
        # "charge at A" → look for qA
        at_m = re.match(r'charge\s+at\s+([A-Z])', raw, re.IGNORECASE)
        if at_m:
            letter = at_m.group(1).upper()
            for sym in charge_syms:
                if sym.upper().endswith(letter):
                    return sym
        # Direct match like q3, qC
        for sym in charge_syms:
            if sym.lower() == raw.lower():
                return sym
    # Heuristic: last charge in list
    return charge_syms[-1] if charge_syms else None


def _num(val) -> Optional[float]:
    """Coerce to float; None on failure (given may carry non-numeric LLM strings)."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _extract_charge_dict(given: dict) -> dict[str, float]:
    """Extract {sym: val} for all charge symbols in given dict. Skips non-numeric."""
    charges = {}
    for sym, val in given.items():
        is_charge = (re.match(r'q[A-Za-z0-9_]*$', sym, re.IGNORECASE) and sym != 'q') \
            or sym.lower() == 'q'
        if is_charge:
            fv = _num(val)
            if fv is not None:
                charges[sym] = fv
    return charges


def _extract_distances(given: dict, question: str) -> dict[str, float]:
    """
    Extract distance values from given dict (e.g. AB=0.08, CA=0.05) and question text.
    """
    dists = {}
    # From given dict — keys like AB, CA, CB, MA, MB, r, a, d, l
    for sym, val in given.items():
        is_dist = bool(re.match(r'[A-Z]{2}$', sym)) or bool(re.match(r'r\d*$', sym)) \
            or sym in ('a', 'b', 'c', 'd', 'l')
        if is_dist:
            fv = _num(val)
            if fv is not None:
                dists[sym] = fv

    # Also scan question for "XY = N cm/m" not caught by given extractor
    for m in re.finditer(
        r'\b([A-Z]{2})\s*=\s*([\d.]+)\s*(cm|m)\b', question
    ):
        key, val, unit = m.group(1), float(m.group(2)), m.group(3)
        factor = 0.01 if unit == "cm" else 1.0
        if key not in dists:
            dists[key] = val * factor

    return dists


def _build_triangle_positions(
    charges: dict[str, float],
    dists: dict[str, float],
    question: str,
    q_syms_sorted: Optional[list[str]] = None,
) -> Optional[dict[str, tuple[float, float]]]:
    """
    Try to assign 2D positions to each charge using available distances.
    Returns {sym: (x,y)} or None if unable.
    q_syms_sorted: pre-sorted list (q1→A, q2→B, q3→C); falls back to dict insertion order.
    """
    q_syms = q_syms_sorted if q_syms_sorted else list(charges.keys())
    n = len(q_syms)

    if n < 2:
        return None

    # ── Equilateral triangle (side = a or l) ───────────────────────────────
    a_side = dists.get("a") or dists.get("l")
    q_lower = question.lower()

    if a_side and n >= 3 and "equilateral" in q_lower:
        a = a_side
        pos: dict[str, tuple[float, float]] = {
            q_syms[0]: (0.0, 0.0),
            q_syms[1]: (a, 0.0),
            q_syms[2]: (a / 2, a * math.sqrt(3) / 2),
        }
        # center charge (q0 or q4)
        if n == 4:
            cx = (0.0 + a + a / 2) / 3
            cy = (0.0 + 0.0 + a * math.sqrt(3) / 2) / 3
            pos[q_syms[3]] = (cx, cy)
        return pos

    # ── Square (side = a) ──────────────────────────────────────────────────
    if a_side and n >= 4 and "square" in q_lower:
        a = a_side
        pos = {
            q_syms[0]: (0.0, 0.0),
            q_syms[1]: (a, 0.0),
            q_syms[2]: (a, a),
            q_syms[3]: (0.0, a),
        }
        # center charge (q5th)
        if n == 5:
            pos[q_syms[4]] = (a / 2, a / 2)
        return pos

    # ── Isosceles right triangle (legs = a) ────────────────────────────────
    if a_side and n >= 3 and ("isosceles right" in q_lower or "right" in q_lower):
        a = a_side
        # Heuristic: q3 at right angle vertex
        if "right angle vertex" in q_lower or "right-angle" in q_lower:
            pos = {
                q_syms[0]: (0.0, a),
                q_syms[1]: (a, 0.0),
                q_syms[2]: (0.0, 0.0),   # right angle at origin
            }
        else:
            pos = {
                q_syms[0]: (0.0, 0.0),
                q_syms[1]: (a, 0.0),
                q_syms[2]: (0.0, a),
            }
        return pos

    # ── General triangle from pairwise distances ───────────────────────────
    # Try distance keys: AB, CA, CB or MA, MB, AB
    pairs_to_try = [
        ("AB", "CA", "CB"),  # q1@A, q2@B, q3@C
        ("AB", "MA", "MB"),  # q1@A, q2@B, q3@M
        ("AB", "AC", "BC"),
    ]
    for r_ab_key, r_ac_key, r_bc_key in pairs_to_try:
        if r_ab_key in dists and r_ac_key in dists and r_bc_key in dists:
            pts = _place_three_points(dists[r_ab_key], dists[r_ac_key], dists[r_bc_key])
            if pts is not None and n >= 3:
                A_pos, B_pos, C_pos = pts
                # Map point LABELS to charges by index convention (A=q1, B=q2,
                # C=q3, M=q0) — NOT by sorted q_syms order. The third point's
                # label is whichever of the AC/BC keys is not A or B (C or M).
                # Bug fixed: q0 sorts first but sits at M (the third point), so the
                # old sorted [0]→A,[1]→B,[2]→C mis-placed every charge (LD004).
                third = next((c for c in (r_ac_key + r_bc_key) if c not in "AB"), "C")

                def _chg(letter: str) -> Optional[str]:
                    idx = _LETTER_IDX.get(letter)
                    return next((s for s in q_syms if _charge_suffix(s) == idx), None)

                qa, qb, qc = _chg("A"), _chg("B"), _chg(third)
                if qa and qb and qc and len({qa, qb, qc}) == 3:
                    return {qa: A_pos, qb: B_pos, qc: C_pos}
                # Fallback: original sorted assignment (convention didn't resolve)
                return {q_syms[0]: A_pos, q_syms[1]: B_pos, q_syms[2]: C_pos}

    # ── Right triangle from AB and BC with implicit AC via Pythagoras ──────
    if n >= 3:
        ab = dists.get("AB") or dists.get("c")
        bc = dists.get("BC") or dists.get("a")
        ac = dists.get("AC") or dists.get("b")
        # Fill missing side via Pythagoras if right triangle
        if "right" in q_lower:
            if ab and bc and not ac:
                ac2 = abs(bc ** 2 - ab ** 2)
                ac = math.sqrt(ac2) if ac2 > 0 else None
            elif ab and ac and not bc:
                bc2 = abs(ac ** 2 - ab ** 2 + ab ** 2)  # hyp check
                bc = None  # can't infer without knowing right angle vertex
        if ab and ac and bc:
            pts = _place_three_points(ab, ac, bc)
            if pts:
                return {q_syms[0]: pts[0], q_syms[1]: pts[1], q_syms[2]: pts[2]}

    # ── Collinear midpoint: 3 charges, one at midpoint of AB ──────────────
    if n == 3 and re.search(r'midpoint|mid-point', question, re.IGNORECASE):
        ab_dist = dists.get("AB") or dists.get("r")
        if ab_dist:
            # The charge at midpoint: prefer q0/qH, else last in sorted q_syms
            mid_sym = next(
                (s for s in q_syms if re.search(r'[0Hh]', s[1:])),
                q_syms[-1]
            )
            others = [s for s in q_syms if s != mid_sym]
            return {
                others[0]: (0.0, 0.0),
                others[1]: (ab_dist, 0.0),
                mid_sym: (ab_dist / 2, 0.0),
            }

    # ── Two charges only ────────────────────────────────────────────────────
    if n == 2:
        r = (dists.get("AB") or dists.get("r") or
             dists.get("a") or dists.get("d"))
        if r:
            return {q_syms[0]: (0.0, 0.0), q_syms[1]: (r, 0.0)}

    return None


# ── Strategy C: Charge at center of equilateral triangle ─────────────────────

_CENTER_PAT = re.compile(
    r'charge\s+(q\w+)\s+placed\s+at\s+the\s+cent|'
    r'(q\w+)\s+(?:is\s+)?placed\s+at\s+(?:the\s+)?cent|'
    r'(?:at\s+(?:the\s+)?cent\w+\s+O.*?)(q\w+)',
    re.IGNORECASE,
)


def _solve_center(
    charges: dict[str, float],
    q_syms: list[str],
    a_side: float,
    k_val: float,
    question: str,
) -> Optional[dict]:
    """
    One charge at centroid of equilateral triangle formed by others.
    R = a/sqrt(3) (distance from centroid to vertex).
    """
    if len(q_syms) < 4:
        return None

    # Detect which charge is at the center from question text
    center_sym = None
    m = _CENTER_PAT.search(question)
    if m:
        center_sym = next(g for g in m.groups() if g is not None)
        center_sym = center_sym.strip()
    if center_sym not in charges:
        # Fallback: charge not in main list (q1,q2,q3) is the center
        main_chars = {'q1', 'q2', 'q3'}
        for sym in q_syms:
            if sym not in main_chars:
                center_sym = sym
                break
    if not center_sym:
        center_sym = q_syms[-1]

    # Vertex charges: everything except center
    v_syms = [s for s in q_syms if s != center_sym][:3]
    R = a_side / math.sqrt(3)  # centroid to vertex

    # Place vertices
    angle_offset = math.pi / 2  # first vertex at top
    positions: dict[str, tuple[float, float]] = {}
    for i, sym in enumerate(v_syms):
        ang = angle_offset + i * 2 * math.pi / 3
        positions[sym] = (R * math.cos(ang), R * math.sin(ang))
    positions[center_sym] = (0.0, 0.0)

    charge_list = [(sym, charges[sym]) for sym in q_syms]
    net, steps = _net_force_at_target(charge_list, positions, center_sym, k_val)
    return {"answer": f"{net:.6g}", "unit": "N", "steps": steps, "source": "vector_solver"}


# ── Electric field (E-field) helpers ─────────────────────────────────────────

def _net_efield_at_point(
    source_charges: list[tuple[str, float]],
    positions: dict[str, tuple[float, float]],
    target_pos: tuple[float, float],
    k_val: float,
) -> tuple[float, list[str]]:
    """
    Compute net E-field at target_pos from all source charges.
    E_i = k*q_i/r_i² in direction (target - source_i)/r_i (signed q_i handles direction).
    """
    tx, ty = target_pos
    ex = ey = 0.0
    steps: list[str] = []

    for sym, q_src in source_charges:
        sx, sy = positions[sym]
        dx, dy = tx - sx, ty - sy
        r = math.sqrt(dx ** 2 + dy ** 2)
        if r < 1e-15:
            continue
        e_signed = k_val * q_src / r ** 2
        ex += e_signed * dx / r
        ey += e_signed * dy / r
        steps.append(
            f"E({sym}→P): |E|={abs(e_signed):.4e} N/C "
            f"({'away' if q_src > 0 else 'toward'} {sym})"
        )

    net = math.sqrt(ex ** 2 + ey ** 2)
    steps.append(f"Sum: Ex={ex:.4e} N/C, Ey={ey:.4e} N/C")
    steps.append(f"Result: |E| = {net:.6g} N/C")
    return net, steps


_TARGET_POINT_PAT = re.compile(
    r'at\s+(?:point\s+)?([A-Z])\b|'   # "at point N", "at M"
    r'at\s+the\s+midpoint\s+([A-Z])',  # "at the midpoint M"
    re.IGNORECASE,
)


def _find_target_point_name(question: str) -> Optional[str]:
    """Extract the name of the target evaluation point (N, C, M, etc.)."""
    # Look for "at point X" after field-related keywords
    for m in re.finditer(
        r'(?:field|intensity|strength)\s+(?:at|caused by|produced by).*?at\s+point\s+([A-Z])',
        question, re.IGNORECASE | re.DOTALL,
    ):
        return m.group(1).upper()
    # "at point X, where" pattern
    for m in re.finditer(r'at\s+point\s+([A-Z])[,\s]', question, re.IGNORECASE):
        return m.group(1).upper()
    # "at the midpoint" → M
    if re.search(r'midpoint|mid\s+point', question, re.IGNORECASE):
        return "M"
    return None


def _build_target_pos(
    target_name: Optional[str],
    dists: dict[str, float],
    given: dict,
    ab: float,
    question: str,
) -> Optional[tuple[float, float]]:
    """
    Compute (x, y) of target evaluation point relative to A=(0,0), B=(AB,0).
    """
    # Midpoint of AB
    if re.search(r'midpoint(?:\s+M)?\s+of\s+AB|at\s+the\s+midpoint', question, re.IGNORECASE):
        return (ab / 2, 0.0)

    # Perpendicular bisector offset
    d_perp = given.get("d_perp")
    if d_perp and re.search(r'perpendicular\s+bisector', question, re.IGNORECASE):
        return (ab / 2, d_perp)

    if target_name:
        n = target_name
        na = dists.get(f"{n}A") or dists.get(f"A{n}")
        nb = dists.get(f"{n}B") or dists.get(f"B{n}")

        # Verbal fallback: "X cm from A", "Y cm from B"
        if not na:
            for m in re.finditer(r'([\d.]+)\s*(cm|m)\s+from\s+A\b', question, re.IGNORECASE):
                na = float(m.group(1)) * (0.01 if m.group(2).lower() == "cm" else 1.0)
        if not nb:
            for m in re.finditer(r'([\d.]+)\s*(cm|m)\s+from\s+B\b', question, re.IGNORECASE):
                nb = float(m.group(1)) * (0.01 if m.group(2).lower() == "cm" else 1.0)

        if na and nb:
            # Law of cosines: handles collinear (y=0) and off-axis cases
            x = (na ** 2 + ab ** 2 - nb ** 2) / (2 * ab)
            y2 = na ** 2 - x ** 2
            if y2 < -1e-10:
                return None
            return (x, max(y2, 0.0) ** 0.5)

        # Equilateral triangle: target at apex, NA = NB = AB (implied)
        if re.search(r'equilateral', question, re.IGNORECASE):
            return (ab / 2, ab * math.sqrt(3) / 2)

        # Collinear: single NA distance
        if na:
            return (na, 0.0)

    return None


def _solve_efield_geometry(
    charges: dict[str, float],
    q_syms: list[str],
    dists: dict[str, float],
    given: dict,
    k_val: float,
    question: str,
) -> Optional[dict]:
    """
    Compute electric field at a target evaluation point (Strategy F).
    Source charges at known positions; target is a point (no charge there).
    """
    ab = dists.get("AB") or given.get("AB")
    q_lower = question.lower()
    a_side = dists.get("a") or dists.get("l")

    # Filter bare 'q' (value alias, not a positional charge)
    source_syms = [s for s in q_syms if s != "q"]
    if not source_syms:
        source_syms = q_syms

    target_name = _find_target_point_name(question)
    source_positions: dict[str, tuple[float, float]] = {}

    # Square 4th vertex: 3 charges at consecutive vertices, target at 4th
    # Does not require AB — uses a_side as the reference length
    if "square" in q_lower and a_side and len(source_syms) >= 3:
        a = a_side
        source_positions[source_syms[0]] = (0.0, 0.0)
        source_positions[source_syms[1]] = (a, 0.0)
        source_positions[source_syms[2]] = (a, a)
        target_pos: Optional[tuple[float, float]] = (0.0, a)

    else:
        if not ab:
            return None
        target_pos = _build_target_pos(target_name, dists, given, ab, question)
        if target_pos is None:
            return None

        # Place source charges at A and B; optional 3rd at equilateral apex or pairwise dists
        if len(source_syms) >= 2:
            source_positions[source_syms[0]] = (0.0, 0.0)
            source_positions[source_syms[1]] = (ab, 0.0)
            if len(source_syms) >= 3:
                s2 = source_syms[2]
                # Pairwise distances for 3rd charge
                s2a = dists.get(f"{s2}A") or dists.get(f"A{s2}")
                s2b = dists.get(f"{s2}B") or dists.get(f"B{s2}")
                if s2a and s2b:
                    x3 = (s2a ** 2 + ab ** 2 - s2b ** 2) / (2 * ab)
                    y3 = max(s2a ** 2 - x3 ** 2, 0.0) ** 0.5
                    source_positions[s2] = (x3, y3)
                elif a_side and "equilateral" in q_lower:
                    source_positions[s2] = (ab / 2, ab * math.sqrt(3) / 2)
                # If neither known, skip 3rd charge (2-charge computation only)
        elif len(source_syms) == 1:
            source_positions[source_syms[0]] = (0.0, 0.0)
        else:
            return None

    charge_list = [(sym, charges[sym]) for sym in source_syms if sym in source_positions]
    if len(charge_list) < 1:
        return None

    net, steps = _net_efield_at_point(charge_list, source_positions, target_pos, k_val)
    b_x = source_positions.get(source_syms[1], (0.0, 0.0))[0] if len(source_syms) > 1 else (ab or 0.0)
    steps.insert(0, f"E-field at ({target_pos[0]:.4f}, {target_pos[1]:.4f}) m, "
                    f"A=(0,0), B=({b_x:.4f},0)")
    # E-field unit: ground truth uses V/m (171) far more than the dimensionally
    # identical N/C (15); the question text gives no signal to tell them apart
    # (0/15 N/C-answer questions mention "N/C"). Default to the majority V/m —
    # net +156 on the dataset. 1 N/C ≡ 1 V/m, so the numeric answer is unchanged.
    logger.info(f"[VECTOR_SOLVER] efield strategy: target={target_name} → {net:.6g} V/m")
    return {"answer": f"{net:.6g}", "unit": "V/m", "steps": steps, "source": "vector_solver"}


# ── Strategy D: Perpendicular bisector ───────────────────────────────────────

def _solve_bisector(
    charges: dict[str, float],
    q_syms: list[str],
    ab: float,
    d_perp: float,
    k_val: float,
    question: str,
) -> Optional[dict]:
    """
    q at perpendicular bisector of AB, d_perp above midpoint.
    q1 at A=(0,0), q2 at B=(AB,0), target at M=(AB/2, d_perp).
    """
    if len(q_syms) < 3:
        return None

    # Identify which charge is on bisector (not q1, not q2; or explicitly detected)
    target_sym = None
    for sym in q_syms:
        if sym not in ('q1', 'q2'):
            target_sym = sym
            break
    if target_sym is None:
        target_sym = q_syms[-1]

    positions: dict[str, tuple[float, float]] = {
        'q1': (0.0, 0.0),
        'q2': (ab, 0.0),
        target_sym: (ab / 2, d_perp),
    }
    # Handle renamed q1/q2 (e.g. q instead of q)
    if 'q1' not in charges:
        syms_no_target = [s for s in q_syms if s != target_sym]
        if len(syms_no_target) >= 2:
            positions = {
                syms_no_target[0]: (0.0, 0.0),
                syms_no_target[1]: (ab, 0.0),
                target_sym: (ab / 2, d_perp),
            }

    charge_list = [(sym, charges[sym]) for sym in q_syms if sym in positions]
    if len(charge_list) < 2:
        return None

    net, steps = _net_force_at_target(charge_list, positions, target_sym, k_val)
    steps.insert(0, f"Bisector geometry: AB={ab:.4f} m, d_perp={d_perp:.4f} m")
    logger.info(f"[VECTOR_SOLVER] bisector strategy: target={target_sym} → {net:.6g} N")
    return {"answer": f"{net:.6g}", "unit": "N", "steps": steps, "source": "vector_solver"}


# ── Strategy E: Inverse angle (find angle given resultant) ────────────────────

_RESULTANT_N_PAT = re.compile(
    r'resultant\s+(?:force\s+)?(?:is\s+)?(?:also\s+)?([\d.]+)\s*N',
    re.IGNORECASE,
)


def _solve_inverse_angle(question: str, given: dict) -> Optional[dict]:
    """Find angle between two forces given F1, F2, and resultant magnitude."""
    # Extract force magnitudes from question text
    force_matches = _FORCE_N_PAT.findall(question)
    forces = [float(v) for v in force_matches]

    if len(forces) == 1 and re.search(r'\beach\b', question, re.IGNORECASE):
        forces = [forces[0], forces[0]]

    # Extract resultant magnitude
    rm = _RESULTANT_N_PAT.search(question)
    if not rm:
        return None
    f_net = float(rm.group(1))

    if len(forces) < 2:
        f1 = given.get("F1") or given.get("F_1")
        f2 = given.get("F2") or given.get("F_2")
        if f1 and f2:
            forces = [float(f1), float(f2)]
        else:
            return None

    f1, f2 = forces[0], forces[1]
    denom = 2 * f1 * f2
    if abs(denom) < 1e-15:
        return None
    cos_theta = (f_net ** 2 - f1 ** 2 - f2 ** 2) / denom
    cos_theta = max(-1.0, min(1.0, cos_theta))
    theta_deg = math.degrees(math.acos(cos_theta))

    steps = [
        f"Given: F1={f1} N, F2={f2} N, F_net={f_net} N",
        "Formula: F_net² = F1²+F2²+2·F1·F2·cos(θ)  →  cos(θ) = (F_net²-F1²-F2²)/(2·F1·F2)",
        f"cos(θ) = ({f_net}²-{f1}²-{f2}²)/(2·{f1}·{f2}) = {cos_theta:.6g}",
        f"Result: θ = {theta_deg:.6g}°",
    ]
    logger.info(f"[VECTOR_SOLVER] inverse_angle: F1={f1}, F2={f2}, F_net={f_net} → θ={theta_deg:.4g}°")
    return {"answer": f"{theta_deg:.6g}", "unit": "degree", "steps": steps, "source": "vector_solver"}


# ── Main dispatcher ───────────────────────────────────────────────────────────

def solve_vector_problem(state: dict) -> Optional[dict]:
    """
    Try vector solving strategies in order. Returns result dict or None.
    Called from sympy_solver_node() as a fallback before llm_fallback.
    """
    question = state.get("question", "")
    parsed = state.get("parsed_physics", {})
    given = parsed.get("given", {})

    k_val = given.get("k", K_E)
    q_lower = question.lower()
    find = parsed.get("find", "")

    # Strategy E: inverse angle — "find angle between forces given resultant"
    if re.search(r'find\s+the\s+angle|angle\s+between\s+the\s+two\s+force', question, re.IGNORECASE):
        result = _solve_inverse_angle(question, given)
        if result:
            return result

    # Strategy A: force magnitude + angle → resultant
    if "force" in q_lower and any(
        kw in q_lower for kw in ["angle", "direction", "perpendicular", "resultant"]
    ) and find != "E_field":
        result = solve_force_angle(question, given)
        if result:
            return result

    # Extract charges and distances for geometry strategies
    charges = _extract_charge_dict(given)
    if not charges:
        return None

    dists = _extract_distances(given, question)
    # Sort by numeric suffix so q1→A, q2→B, q3→C (consistent position assignment)
    q_syms = sorted(
        charges.keys(),
        key=lambda s: (int(re.sub(r'\D', '', s)) if re.search(r'\d', s) else 999, s)
    )

    # Strategy F: E-field at evaluation point (find == "E_field").
    # An E-field question must NEVER fall through to the force strategies below —
    # computing a Coulomb FORCE for a field question is always physically wrong
    # (it produced confident-wrong answers, e.g. LD296 → 33.8 instead of 7.05e6).
    # If Strategy F can't build the geometry, return None → defer to the LLM/PAL
    # fallback rather than emit a wrong number that would block it.
    if find == "E_field":
        return _solve_efield_geometry(charges, q_syms, dists, given, k_val, question)

    # Strategy D: perpendicular bisector geometry (force on charge at bisector)
    d_perp = given.get("d_perp")
    ab = dists.get("AB") or given.get("AB")
    if d_perp and ab and "perpendicular bisector" in q_lower:
        result = _solve_bisector(charges, q_syms, ab, d_perp, k_val, question)
        if result:
            return result

    # Strategy C: center of equilateral triangle (4 charges: 3 vertices + 1 center)
    a_side = dists.get("a") or dists.get("l")
    if (a_side and len(q_syms) == 4 and "equilateral" in q_lower
            and "center" in q_lower):
        result = _solve_center(charges, q_syms, a_side, k_val, question)
        if result:
            logger.info(f"[VECTOR_SOLVER] center strategy → {result['answer']} N")
            return result

    # Strategy B: general geometry
    positions = _build_triangle_positions(charges, dists, question, q_syms_sorted=q_syms)
    if positions is None:
        logger.debug("[VECTOR_SOLVER] Could not build geometry positions")
        return None

    target = _detect_target_charge(question, q_syms)
    if target is None or target not in positions:
        logger.debug(f"[VECTOR_SOLVER] Target charge not found: {target}")
        return None

    charge_list = [(sym, charges[sym]) for sym in q_syms if sym in positions]
    net, steps = _net_force_at_target(charge_list, positions, target, k_val)

    if net == 0.0 and len(charge_list) < 2:
        return None

    logger.info(f"[VECTOR_SOLVER] geometry strategy: target={target} → {net:.6g} N")
    return {"answer": f"{net:.6g}", "unit": "N", "steps": steps, "source": "vector_solver"}

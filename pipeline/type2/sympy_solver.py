"""
pipeline/type2/sympy_solver.py

LangGraph node [5b]: Symbolic physics solver.
Dispatches by PhysicsQuestionType — zero arithmetic hallucination.
Timeout via ThreadPoolExecutor (works on Windows; signal.SIGALRM is Linux-only).
"""

import logging
import re as _re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

from sympy import symbols, Eq, solve, sympify

from pipeline.type2.type2_classifier import PhysicsQuestionType

# SymPy builtins that should NOT be overridden by symbol declarations
_MATH_FNS = frozenset({
    'sqrt', 'sin', 'cos', 'tan', 'exp', 'log', 'abs', 'pi',
    'Sum', 'Rational', 'Integer', 'Float',
})

logger = logging.getLogger(__name__)

# Display units for common physics symbols
_UNIT_MAP: dict[str, str] = {
    "V": "V", "I": "A", "R": "Ω", "P": "W",
    "E": "J", "C": "F", "Q": "C", "F": "N",
    "f": "Hz", "L": "H", "B": "T",
    "R_total": "Ω", "R1": "Ω", "R2": "Ω", "R3": "Ω",
}


# ══════════════════════════════════════════════════════════════
# Core solvers (run inside ThreadPoolExecutor)
# ══════════════════════════════════════════════════════════════

def _make_sym_dict(formula_str: str) -> dict:
    """
    Extract all identifier tokens from formula_str and declare each as a fresh
    SymPy Symbol. This prevents SymPy from interpreting physics symbols as
    built-in constants (I = imaginary unit, E = Euler's number, S = singleton).
    """
    tokens = set(_re.findall(r'\b[A-Za-z_]\w*\b', formula_str))
    return {t: symbols(t) for t in tokens if t not in _MATH_FNS}


def _parse_formula(formula_str: str) -> Optional[tuple]:
    """
    Parse 'LHS = RHS' string into (SymPy Eq, symbol_name_set, sym_dict).
    Returns None on parse failure.
    """
    if "=" not in formula_str:
        return None
    lhs_str, rhs_str = formula_str.split("=", 1)
    try:
        sym_dict = _make_sym_dict(formula_str)
        lhs = sympify(lhs_str.strip(), locals=sym_dict)
        rhs = sympify(rhs_str.strip(), locals=sym_dict)
        sym_names = {str(s) for s in lhs.free_symbols | rhs.free_symbols}
        sym_names.add(lhs_str.strip())
        return Eq(lhs, rhs), sym_names, sym_dict
    except Exception as e:
        logger.warning(f"[SYMPY_SOLVER] Cannot parse formula '{formula_str}': {e}")
        return None


def _solve_single(formula_str: str, given: dict, find: str) -> Optional[dict]:
    """Solve one formula with known values; returns result dict or None."""
    parsed = _parse_formula(formula_str)
    if not parsed:
        return None
    eq, sym_names, sym_dict = parsed

    find_sym = sym_dict.get(find) or symbols(find)

    # Substitute all known values using declared symbols (avoids I/E conflicts)
    eq_sub = eq
    for var, val in given.items():
        sym = sym_dict.get(var)
        if sym is not None:
            eq_sub = eq_sub.subs(sym, float(val))

    solutions = solve(eq_sub, find_sym)
    if not solutions:
        return None

    try:
        answer_float = float(solutions[0])
    except Exception:
        return None

    unit = _UNIT_MAP.get(find, "")
    steps = [
        f"Given: {', '.join(f'{k}={v}' for k, v in given.items())}",
        f"Formula: {formula_str}",
        f"Substitute: {eq_sub}",
        f"Solve for {find}: {find} = {solutions[0]}",
        f"Result: {find} = {answer_float:.6g} {unit}".strip(),
    ]
    return {
        "answer": f"{answer_float:.6g}",
        "unit": unit,
        "steps": steps,
        "raw_expr": str(solutions[0]),
        "source": "sympy",
    }


def _solve_multi_step(formulas: list[str], given: dict, find: str) -> Optional[dict]:
    """
    Chain formulas sequentially — step N output feeds step N+1 as known.
    First formula that yields `find` wins.
    """
    accumulated = dict(given)
    all_steps = [f"Given: {', '.join(f'{k}={v}' for k, v in given.items())}"]

    for i, formula_str in enumerate(formulas):
        parsed = _parse_formula(formula_str)
        if not parsed:
            continue
        eq, sym_names, sym_dict = parsed

        eq_sub = eq
        for var, val in accumulated.items():
            sym = sym_dict.get(var)
            if sym is not None:
                eq_sub = eq_sub.subs(sym, float(val))

        remaining = eq_sub.free_symbols
        if len(remaining) != 1:
            continue

        unknown = list(remaining)[0]
        solutions = solve(eq_sub, unknown)
        if not solutions:
            continue

        try:
            val = float(solutions[0])
        except Exception:
            continue

        accumulated[str(unknown)] = val
        all_steps.append(f"Step {i+1} — {formula_str}: {unknown} = {val:.6g}")

        if str(unknown) == find:
            unit = _UNIT_MAP.get(find, "")
            all_steps.append(f"Result: {find} = {val:.6g} {unit}".strip())
            return {
                "answer": f"{val:.6g}",
                "unit": unit,
                "steps": all_steps,
                "raw_expr": str(solutions[0]),
                "source": "sympy",
            }

    # Check if find accumulated from intermediate steps
    if find in accumulated:
        val = accumulated[find]
        unit = _UNIT_MAP.get(find, "")
        return {
            "answer": f"{val:.6g}",
            "unit": unit,
            "steps": all_steps + [f"Result: {find} = {val:.6g} {unit}".strip()],
            "raw_expr": str(val),
            "source": "sympy",
        }

    return None


def _run_with_timeout(fn, args: tuple, timeout: int) -> Optional[dict]:
    """Execute fn(*args) with timeout; returns None on timeout or exception."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.warning(f"[SYMPY_SOLVER] Timeout after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"[SYMPY_SOLVER] Exception in solver: {e}")
            return None


# ══════════════════════════════════════════════════════════════
# Main dispatch
# ══════════════════════════════════════════════════════════════

def solve_physics(
    parsed: dict,
    q_type: PhysicsQuestionType,
    timeout: int = 10,
) -> dict:
    """
    Dispatch by PhysicsQuestionType and try formulas until one succeeds.

    SINGLE_FORMULA / ELECTROSTATIC → _solve_single for each formula
    MULTI_STEP                      → _solve_multi_step, fallback to _solve_single
    CIRCUIT                         → _solve_single per formula (KVL/KCL as given)

    Returns sympy_result dict. Never raises.
    """
    given = parsed.get("given", {})
    find = parsed.get("find", "")
    formulas = parsed.get("formulas", [])

    if not find or not formulas:
        logger.warning(f"[SYMPY_SOLVER] Missing find='{find}' or formulas={formulas}")
        return {"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}

    result = None

    if q_type in (
        PhysicsQuestionType.SINGLE_FORMULA,
        PhysicsQuestionType.CIRCUIT,
        PhysicsQuestionType.ELECTROSTATIC,
    ):
        for formula_str in formulas:
            result = _run_with_timeout(_solve_single, (formula_str, given, find), timeout)
            if result:
                logger.info(f"[SYMPY_SOLVER] Solved via {q_type.value}: {formula_str}")
                break

    elif q_type == PhysicsQuestionType.MULTI_STEP:
        result = _run_with_timeout(_solve_multi_step, (formulas, given, find), timeout)
        if not result:
            # Fallback: single-formula attempt
            for formula_str in formulas:
                result = _run_with_timeout(_solve_single, (formula_str, given, find), timeout)
                if result:
                    break

    if not result:
        logger.warning(f"[SYMPY_SOLVER] All strategies failed for find={find}")
        return {"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}

    return result


# ══════════════════════════════════════════════════════════════
# LangGraph node
# ══════════════════════════════════════════════════════════════

def sympy_solver_node(state: dict) -> dict:
    """Node 5b: Solve physics problem symbolically, populate solver_result."""
    from pipeline.state import SolverResult

    parsed = state.get("parsed_physics", {})
    q_type_str = parsed.get("question_type", PhysicsQuestionType.SINGLE_FORMULA.value)

    try:
        q_type = PhysicsQuestionType(q_type_str)
    except ValueError:
        q_type = PhysicsQuestionType.SINGLE_FORMULA

    sympy_result = solve_physics(parsed, q_type)

    confidence = state.get("confidence", 1.0)
    if sympy_result.get("source") == "llm_fallback":
        confidence = min(confidence, 0.5)

    solver_result: SolverResult = {
        "answer": sympy_result.get("answer", ""),
        "unit": sympy_result.get("unit"),
        "steps": sympy_result.get("steps", []),
        "fol": None,
        "source": sympy_result.get("source", "llm_fallback"),
        "confidence": confidence,
    }

    logger.info(
        f"[SYMPY_SOLVER] answer={solver_result['answer']} "
        f"source={solver_result['source']} confidence={confidence}"
    )

    return {
        **state,
        "sympy_result": sympy_result,
        "solver_result": solver_result,
        "answer": sympy_result.get("answer", ""),
        "confidence": confidence,
    }

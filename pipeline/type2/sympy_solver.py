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
    # E_field is produced by vector_solver (Strategy F), not this scalar path,
    # but map it too for safety so any future SymPy route emits a consistent unit.
    "E_field": "V/m",
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
        logger.warning("Cannot parse formula", extra={"extra": {
            "parsed_input": formula_str,
            "error": str(e)
        }})
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
            logger.warning("SymPy solver timeout", extra={"extra": {
                "error": f"Timeout after {timeout}s"
            }})
            return None
        except Exception as e:
            logger.error("Exception in solver", extra={"extra": {
                "error": str(e)
            }})
            return None


# ══════════════════════════════════════════════════════════════
# PAL (Program-Aided LM) sandbox — LLM writes code, the MACHINE computes
# ══════════════════════════════════════════════════════════════
# The LLM (generate_sympy_code) emits sympy/math Python; we run it here so the
# arithmetic is deterministic (zero arithmetic hallucination — docs/docs_vytriet/
# proposals.md §2). Defense in depth: (1) deny-list scan, (2) whitelisted imports,
# (3) stripped builtins, (4) thread timeout via _run_with_timeout.

_PAL_FORBIDDEN = (
    "import os", "import sys", "import subprocess", "import socket",
    "import shutil", "import requests", "import urllib", "import pickle",
    "import marshal", "from os", "from sys", "from subprocess",
    "__import__", "open(", "eval(", "exec(", "compile(", "input(",
    "getattr(", "setattr(", "delattr(", "globals(", "locals(",
    "__subclasses__", "__bases__", "__globals__", "__builtins__",
)
_PAL_ALLOWED_MODULES = {"math", "cmath", "sympy", "numpy", "fractions", "decimal"}


def _pal_safe_import(name, *args, **kwargs):
    """Whitelisted __import__ for the PAL sandbox."""
    if name.split(".")[0] not in _PAL_ALLOWED_MODULES:
        raise ImportError(f"PAL sandbox: import '{name}' not allowed")
    return __import__(name, *args, **kwargs)


def _run_pal_code(code: str) -> Optional[dict]:
    """Exec whitelisted PAL code; read {answer, unit} from its globals. No timeout
    here — execute_generated_code wraps this in _run_with_timeout."""
    import math
    import sympy

    safe_builtins = {
        "abs": abs, "min": min, "max": max, "round": round, "sum": sum,
        "pow": pow, "len": len, "range": range, "float": float, "int": int,
        "str": str, "bool": bool, "list": list, "dict": dict, "tuple": tuple,
        "set": set, "enumerate": enumerate, "zip": zip, "sorted": sorted,
        "map": map, "filter": filter, "print": print, "complex": complex,
        "ValueError": ValueError, "ZeroDivisionError": ZeroDivisionError,
        "__import__": _pal_safe_import,
    }
    g = {"__builtins__": safe_builtins, "math": math, "sympy": sympy, "sp": sympy}
    exec(code, g)  # noqa: S102 — sandboxed: deny-list + whitelist imports + timeout

    ans = g.get("answer")
    if ans is None and callable(g.get("solve")):
        ans = g["solve"]()
    if ans is None:
        return None

    try:
        ans_val = float(ans)
        answer_str = f"{ans_val:.6g}"
    except (TypeError, ValueError):
        try:  # sympy expression → evalf
            ans_val = float(sympy.sympify(ans).evalf())
            answer_str = f"{ans_val:.6g}"
        except Exception:
            answer_str = str(ans)  # non-numeric (e.g. "Yes")
    return {"answer": answer_str, "unit": str(g.get("unit") or "")}


def execute_generated_code(code: str, timeout: int = 5) -> Optional[dict]:
    """Run LLM-generated PAL code in a sandbox. Returns {answer, unit} or None on
    rejected/failed/timed-out code. NEVER raises."""
    if not code or len(code) > 4000:
        return None
    low = code.lower()
    if any(tok in low for tok in _PAL_FORBIDDEN):
        logger.warning("[PAL] rejected generated code (forbidden token)")
        return None
    return _run_with_timeout(_run_pal_code, (code,), timeout)


def _llm_fallback_chain(state: dict, parsed: dict) -> Optional[dict]:
    """LLM fallback when every symbolic solver fails: PAL code-gen+exec FIRST
    (machine does the arithmetic → no hallucination), CoT as last resort. Returns
    None when the LLM server is down — preserving the no-LLM floor + offline tests."""
    try:
        from llm import llm_server_available
        if not llm_server_available():
            return None
        from llm import get_shared_reasoner

        reasoner = get_shared_reasoner()
        question = state.get("question", "")
        given = parsed.get("given", {}) or {}
        find = parsed.get("find", "") or ""
        formulas = parsed.get("formulas", []) or []

        # 1. PAL — LLM writes code, sandbox executes (preferred).
        code = reasoner.generate_sympy_code(question, given, find, formulas)
        pal = execute_generated_code(code, timeout=5)
        if pal and pal.get("answer") not in (None, ""):
            logger.info("[PAL] solved via generated code")
            return {"answer": pal["answer"], "unit": pal.get("unit", ""),
                    "steps": [code], "source": "llm_pal"}

        # 2. CoT — last resort (LLM does the arithmetic itself).
        cot = reasoner.solve_physics_cot(question, given, find, formulas)
        if cot and cot.get("answer"):
            return cot
    except Exception as e:
        logger.warning(f"[PAL] LLM fallback chain failed: {e}")
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
    MULTI_STEP / ELECTROMAGNETIC    → _solve_multi_step, fallback to _solve_single
                                      (DDT: EMF/W_L/Phi chains — weakness #8a alias)
    CIRCUIT                         → _solve_single per formula (KVL/KCL as given)

    Returns sympy_result dict. Never raises.
    """
    given = parsed.get("given", {})
    find = parsed.get("find", "")
    formulas = parsed.get("formulas", [])

    if not find or not formulas:
        logger.warning(f"[SYMPY_SOLVER] Missing find='{find}' or formulas={formulas}")
        return {"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}

    # Dependency chain injected by formula_rag (len > 1) → chain-solve first,
    # regardless of q_type (RLC, solenoid…). _solve_multi_step walks deps→target.
    if len(formulas) > 1:
        chain_res = _run_with_timeout(_solve_multi_step, (formulas, given, find), timeout)
        if chain_res:
            logger.info(f"[SYMPY_SOLVER] Solved via chain ({len(formulas)} formulas) for {find}")
            return chain_res

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

    elif q_type in (PhysicsQuestionType.MULTI_STEP, PhysicsQuestionType.ELECTROMAGNETIC):
        result = _run_with_timeout(_solve_multi_step, (formulas, given, find), timeout)
        if not result:
            # Fallback: single-formula attempt
            for formula_str in formulas:
                result = _run_with_timeout(_solve_single, (formula_str, given, find), timeout)
                if result:
                    break

    if not result:
        logger.warning("SymPy solve failed — switching to llm_fallback", extra={"extra": {
            "parsed_input": parsed,
            "error": f"All strategies failed for find={find}"
        }})
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

    # Dedicated-solver dispatch (T2-16) — before the generic sympy path.
    # YES_NO guard: domain + given-key check chặn câu qualitative bị classifier
    # nhầm vào YES_NO (weakness #7 over-routing) — thiếu L/C/f thì đi đường thường.
    given = parsed.get("given", {}) or {}
    if (q_type == PhysicsQuestionType.YES_NO
            and parsed.get("domain") == "ac_circuits"
            and all(k in given for k in ("L", "C", "f"))):
        from pipeline.type2.resonance_solver import solve_resonance
        sympy_result = solve_resonance(parsed, state.get("question", ""))
    elif q_type in (PhysicsQuestionType.ERROR_CALC, PhysicsQuestionType.MULTI_ANSWER):
        from pipeline.type2.error_solver import solve_error
        sympy_result = solve_error(parsed, state.get("question", ""))
    else:
        # A YES_NO that missed the resonance gate (wrong domain / missing L,C,f) is
        # likely a non-resonance question the classifier mislabelled (over-broad
        # "does it"/"will it" cues — weakness #2a). Downgrade to the generic symbolic
        # path so it ATTEMPTS sympy before dropping to the LLM fallback. Safe: a
        # genuine yes/no has no "find the X" verb → find="" → solve_physics returns
        # llm_fallback anyway (0 regression); a misclassified compute question now
        # gets a real symbolic shot.
        if q_type == PhysicsQuestionType.YES_NO:
            q_type = PhysicsQuestionType.SINGLE_FORMULA
        if parsed.get("domain") == "circuits":
            # DC parallel-resistor networks (THCB lamps + basic circuits). circuit_solver
            # handles multi-branch / multi-answer (per-branch I + total, R_p, P) that the
            # scalar path can't; returns None for plain single-formula → solve_physics.
            from pipeline.type2.circuit_solver import solve_circuit
            sympy_result = solve_circuit(parsed, state.get("question", "")) \
                or solve_physics(parsed, q_type)
        else:
            sympy_result = solve_physics(parsed, q_type)

    # Vector solver fallback: handles multi-charge Coulomb + force+angle problems
    if sympy_result.get("source") == "llm_fallback":
        from pipeline.type2.vector_solver import solve_vector_problem
        vec_result = solve_vector_problem(state)
        if vec_result:
            sympy_result = vec_result

    # LLM fallback chain (PAL code-gen → CoT) when all symbolic solvers fail.
    # Gated by llm_server_available() inside the helper → no-LLM floor unchanged.
    if sympy_result.get("source") == "llm_fallback":
        llm_res = _llm_fallback_chain(state, parsed)
        if llm_res:
            sympy_result = llm_res

    # Phrasal-derived symbolic answer + FAILS self-validation → don't trust it;
    # defer to PAL/LLM instead of blocking the fallback. Prose extraction can feed
    # a wrong-formula match (a confident-but-wrong number). The no-LLM floor is
    # untouched (helper returns None when the server is down → keep sympy answer).
    elif (parsed.get("_phrasal_used")
          and sympy_result.get("source") in ("sympy", "circuit")):
        from pipeline.type2.type2_validation import validate_sympy_result
        try:
            v = validate_sympy_result(sympy_result.get("answer") or None,
                                      parsed.get("find"))
            suspect = v is not None and not v.is_valid
        except Exception:
            suspect = False
        if suspect:
            llm_res = _llm_fallback_chain(state, parsed)
            if llm_res:
                logger.info("[SYMPY_SOLVER] phrasal answer failed verify → PAL/LLM")
                sympy_result = llm_res

    confidence = state.get("confidence", 1.0)
    _src = sympy_result.get("source")
    if _src in ("llm_fallback", "llm_cot"):
        confidence = min(confidence, 0.5)
    elif _src == "llm_pal":
        # PAL = machine-computed (deterministic arithmetic) > LLM-only CoT.
        confidence = min(confidence, 0.6)

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

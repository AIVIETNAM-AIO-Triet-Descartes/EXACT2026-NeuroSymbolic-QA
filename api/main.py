"""
API Server - EXACT 2026 Neuro-Symbolic QA System.

FastAPI app expose:
    POST /predict    — official endpoint, both types (route by `type`), List[UnifiedResponse]
    GET  /v1/models  — proxy to internal vLLM (committee model verification)
    GET  /health     — health check

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import re
import httpx
from fastapi import FastAPI, HTTPException
from api.schemas import UnifiedRequest, UnifiedResponse
from api.logger import get_logger, log_pipeline_request
from api.response_builder import build_response

logger = get_logger(__name__)
app = FastAPI(title="EXACT 2026 QA API", version="0.1.0")

# vLLM listens on 127.0.0.1:8001 (internal only). The committee reaches its model
# list through the public FastAPI port via the /v1/models proxy below.
VLLM_BASE = os.getenv("VLLM_BASE", "http://127.0.0.1:8001")


# ══════════════════════════════════════════════════════════════
# Track 2 pipeline
# ══════════════════════════════════════════════════════════════

# Unit inference map: variable name → default SI unit
_FIND_TO_UNIT = {
    "E": "J", "W": "J", "KE": "J", "PE": "J", "U": "J",
    "X_L": "ohm", "X_C": "ohm", "Z": "ohm", "R": "ohm",
    "R_total": "ohm", "R_eq": "ohm", "Z_L": "ohm", "Z_C": "ohm", "Z_eq": "ohm", "Z_total": "ohm",
    "v": "m/s", "u": "m/s", "a": "m/s^2",
    "s": "m", "d": "m", "h": "m", "x": "m", "d_i": "m", "d_o": "m",
    "t": "s", "T": "s",
    "f": "Hz", "F": "N",
    "P": "W", "I": "A", "V": "V", "Q": "C",
    "C": "F", "L": "H", "B": "T",
    "image_distance": "m", "object_distance": "m", "focal_length": "m",
    "distance": "m", "radius": "m", "diameter": "m", "length": "m",
    "width": "m", "height": "m", "wavelength": "m",
    "E_field": "V/m", "electric_field": "V/m",
    "angle": "degree",
    "resistance": "ohm", "resistivity": "ohm*m", "rho": "ohm*m",
}

# Equivalent unit pairs: (from, to) — bidirectional
_EQUIVALENT_UNITS = {
    "V/m": "N/C", "N/C": "V/m",
    "J/C": "V", "V": "J/C",
    "kg*m/s^2": "N", "N": "kg*m/s^2",
    "A*s": "C", "C": "A*s",
}

# Unit scale conversions: (si_unit, question_keyword) → (target_unit, scale_factor)
_UNIT_SCALES = [
    # Length
    ("m", "cm", "cm", 100.0),
    ("m", "mm", "mm", 1000.0),
    ("m", "km", "km", 0.001),
    # Charge
    ("C", "uC", "uC", 1e6),
    ("C", "μC", "uC", 1e6),
    ("C", "nC", "nC", 1e9),
    ("C", "mC", "mC", 1e3),
    # Capacitance
    ("F", "uF", "uF", 1e6),
    ("F", "μF", "uF", 1e6),
    ("F", "nF", "nF", 1e9),
    ("F", "pF", "pF", 1e12),
    # Energy
    ("J", "kJ", "kJ", 0.001),
    ("J", "mJ", "mJ", 1e3),
    ("J", "eV", "eV", 6.242e18),
    # Resistance
    ("ohm", "kohm", "kohm", 0.001),
    ("ohm", "Mohm", "Mohm", 1e-6),
    # Frequency
    ("Hz", "kHz", "kHz", 0.001),
    ("Hz", "MHz", "MHz", 1e-6),
    # Voltage
    ("V", "kV", "kV", 0.001),
    ("V", "mV", "mV", 1e3),
    # Time
    ("s", "ms", "ms", 1e3),
    ("s", "us", "us", 1e6),
]


def _snap_and_convert(answer, unit: str, question: str, find_var: str):
    """
    Post-process physics answer: infer missing unit, convert equivalent
    units, and snap SI values to the unit system used in the question.

    Returns (answer, unit) tuple.
    """
    try:
        val = float(answer)
    except (ValueError, TypeError):
        return answer, unit

    q_lower = question.lower()

    # 1. Infer missing unit from find_var
    if not unit and find_var:
        # Clean find_var: remove trailing underscores, numbers
        clean_find = re.sub(r'_?\d+$', '', find_var).strip()
        # Optics focal length override: in optics, 'f' is focal length (meters), not frequency (Hz)
        if clean_find == "f" and any(w in q_lower for w in ["lens", "mirror", "optics", "focal"]):
            inferred = "m"
        else:
            inferred = _FIND_TO_UNIT.get(clean_find) or _FIND_TO_UNIT.get(find_var)
        if inferred:
            unit = inferred
            logger.info(f"[UNIT_SNAP] Inferred unit '{unit}' from find_var='{find_var}'")

    # 2. Check for equivalent unit preference in question text
    if unit in _EQUIVALENT_UNITS:
        target = _EQUIVALENT_UNITS[unit]
        # Check if the question explicitly uses the target unit
        target_lower = target.lower().replace("^", "")
        if target_lower in q_lower or target in question:
            logger.info(f"[UNIT_SNAP] Equivalent unit swap: '{unit}' -> '{target}'")
            unit = target
        else:
            # Special equivalent snapping for electric field: V/m <-> N/C based on charge vs voltage keywords
            if unit == "V/m" and any(c in q_lower for c in ["coulomb", "nc", "uc", "μc", "mc", " c"]) and not any(v in q_lower for v in ["potential", "voltage", "battery", " v"]):
                logger.info(f"[UNIT_SNAP] Special electric field swap: 'V/m' -> 'N/C' (charge-based)")
                unit = "N/C"
            elif unit == "N/C" and any(v in q_lower for v in ["potential", "voltage", "battery", " v"]) and not any(c in q_lower for c in ["coulomb", "nc", "uc", "μc", "mc", " c"]):
                logger.info(f"[UNIT_SNAP] Special electric field swap: 'N/C' -> 'V/m' (voltage-based)")
                unit = "V/m"

    # 3. Scale SI value to question-expected unit
    for si_unit, keyword, target_unit, scale in _UNIT_SCALES:
        if unit != si_unit:
            continue
        # Check if question mentions the target unit scale
        if keyword.lower() in q_lower or keyword in question:
            new_val = val * scale
            # Format nicely: avoid unnecessary decimals
            if new_val == int(new_val):
                answer = str(int(new_val))
            else:
                answer = f"{new_val:g}"
            logger.info(
                f"[UNIT_SNAP] Scaled {val} {unit} -> {answer} {target_unit}"
            )
            unit = target_unit
            return answer, unit

    return answer, unit


def _run_type2_pipeline(request: UnifiedRequest) -> UnifiedResponse:
    """
    Sequential execution of Type 2 nodes (physics pipeline).
    Equivalent to LangGraph StateGraph without the orchestration overhead.
    Node order: physics_parser → formula_rag → sympy_solver →
                self_verifier → cot_builder → explainer
    """
    from pipeline.state import PipelineState
    from pipeline.type2.physics_parser import physics_parser_node
    from pipeline.type2.formula_rag import formula_rag_node
    from pipeline.type2.sympy_solver import sympy_solver_node
    from pipeline.type2.cot_builder import cot_builder_node
    from pipeline.type2.explainer import explainer_node_type2
    from pipeline.type2.type2_validation import validate_sympy_result

    # Initial state
    state: PipelineState = {
        "question": request.query,
        "query_id": request.query_id,
        "options": request.options or [],
        "premises": request.premises or [],
        "query_type": "type2",
        "fol_translation": None,
        "fol_valid": None,
        "z3_result": None,
        "parsed_physics": None,
        "sympy_result": None,
        "cot": None,
        "answer": None,
        "explanation": None,
        "confidence": 1.0,
        "solver_result": None,
        "fol_retries": 0,
    }

    # Node 3b: PhysicsParser
    state = physics_parser_node(state)

    # Node 4b: FormulaRAG
    state = formula_rag_node(state)

    # Node 5b: SympySolver
    state = sympy_solver_node(state)

    # Node 6b: SelfVerifier (inline — wraps type2_validation)
    try:
        sympy_result = state.get("sympy_result", {})
        parsed = state.get("parsed_physics", {})
        # Yes/No (resonance) và multi-answer (error_calc) là chuỗi non-numeric —
        # validate_sympy_result sẽ fail float() oan. Bỏ qua numeric validation
        # cho 2 source deterministic này (impl_plan §4).
        if sympy_result.get("source") in ("resonance", "error_calc"):
            logger.info(
                f"[SELF_VERIFIER] Skipped numeric validation for "
                f"source={sympy_result.get('source')}"
            )
            val = None
        else:
            val = validate_sympy_result(
                value=sympy_result.get("answer") or None,
                target_variable=parsed.get("find"),
            )
        if val is not None and not val.is_valid:
            state = {**state, "confidence": 0.4}
            logger.warning("Self-verification failed", extra={"extra": {
                "self_verify_failed": True,
                "answer": sympy_result.get("answer"),
                "errors": val.errors
            }})
        for w in (val.warnings if val is not None else []):
            logger.info(f"[SELF_VERIFIER] Warning: {w}")

        # Update confidence in solver_result too
        if state.get("solver_result"):
            sr = dict(state["solver_result"])
            sr["confidence"] = state["confidence"]
            state = {**state, "solver_result": sr}
    except Exception as e:
        logger.warning(f"[SELF_VERIFIER] Skipped: {e}")

    # Node 6c: CotBuilder
    state = cot_builder_node(state)

    # Node 7: ExplainerAgent
    state = explainer_node_type2(state)

    answer = state.get("answer") or ""
    explanation = state.get("explanation") or f"The answer is {answer}."
    cot = state.get("cot") or []
    confidence = state.get("confidence", 1.0)
    solver_result = state.get("solver_result", {})
    solver_source = solver_result.get("source", "llm_fallback") if solver_result else "llm_fallback"
    raw_unit = solver_result.get("unit") or ""

    # ── Unit Snapping ──
    # Fix missing units, convert equivalent units, and snap SI values to
    # the unit system expected by the question text.
    parsed = state.get("parsed_physics", {}) or {}
    find_var = parsed.get("find", "")
    answer, raw_unit = _snap_and_convert(
        answer, raw_unit, request.query, find_var
    )

    log_pipeline_request(
        question=request.query,
        query_type="type2",
        answer=str(answer),
        confidence=confidence,
        has_fol=False,
        has_cot=bool(cot),
        fol_retries=0,
        fallback_triggered=(solver_source == "llm_fallback"),
        z3_timeout=False,
        solver_source=solver_source
    )

    return build_response(
        query_id=request.query_id,
        query_type="type2",
        answer=answer,
        explanation=explanation,
        raw_unit=raw_unit,
        steps=cot,
        premises_used=[]
    )


# ══════════════════════════════════════════════════════════════
# Track 1 pipeline (Logic) — single-query
# ══════════════════════════════════════════════════════════════

def _run_type1_pipeline(request: UnifiedRequest) -> UnifiedResponse:
    """
    Single-query Type 1 solve via LLM Chain-of-Thought over the NL premises.
    Verified and augmented by Z3 logic solver when possible to get precise premises_used.
    """
    from pipeline.type1.question_classifier import QuestionClassifier, QuestionType
    classifier = QuestionClassifier()
    classified_q = classifier.classify(request.query)
    
    # Detect Yes/No/Uncertain options — treat as yes_no, NOT mcq, to avoid
    # fragile letter-mapping chains (A→Yes→A→Yes) that break easily.
    is_ynu_options = False
    if request.options:
        opt_vals = {o.strip().lower() for o in request.options}
        if opt_vals <= {'yes', 'no', 'uncertain', 'unknown', 'true', 'false', 'maybe', 'cannot determine', 'cannot be determined', 'none of the above'}:
            is_ynu_options = True
    
    if is_ynu_options:
        q_type = "yes_no"
    elif request.options or classified_q.question_type == QuestionType.MCQ:
        q_type = "mcq"
    else:
        # Check if the query is an open-ended logic question (who, what, how, how many, which, etc.)
        is_yes_no = True
        query_clean = request.query.strip().lower()
        if re.match(r'^(who|what|which|how|where|when|whose|whom|find|calculate|determine|identify|list|give|state)\b', query_clean):
            is_yes_no = False
        q_type = "yes_no" if is_yes_no else "open"

    full_q = request.query
    if request.options:
        formatted_options = []
        for i, opt in enumerate(request.options):
            opt_str = opt.strip()
            if re.match(r'^[\(\[\s]*[A-D][\.\)\s\]]', opt_str, re.IGNORECASE):
                formatted_options.append(opt_str)
            else:
                letters = ['A', 'B', 'C', 'D']
                prefix = f"{letters[i]}. " if i < len(letters) else ""
                formatted_options.append(f"{prefix}{opt_str}")
        full_q = full_q + "\n" + "\n".join(formatted_options)

    answer, explanation, steps = "", "", []
    premises_used = []
    from llm import llm_server_available
    if llm_server_available():
        try:
            from llm import get_shared_reasoner
            reasoner = get_shared_reasoner()
            
            # 1. Run LLM CoT
            res = reasoner.solve_with_cot(
                request.premises or [], [], full_q, q_type, None,
            ) or {}
            answer = (res.get("answer") or "").strip()
            explanation = (res.get("explanation") or "").strip()
            steps = [explanation] if explanation else []
            premises_used = res.get("premises_used") or []
            
            # 2. Try Z3 Verification & Tie-break for short questions
            if q_type != "open" and len(request.premises or []) <= 12:
                try:
                    from pipeline.type1.z3_solver import execute_z3_code
                    
                    class MockClassified:
                        def __init__(self, original, q_type_str):
                            self.original = original
                            from pipeline.type1.question_classifier import QuestionType
                            self.question_type = QuestionType.MCQ if q_type_str == "mcq" else QuestionType.YES_NO
                    
                    classified = MockClassified(full_q, q_type)
                    
                    # Filter out meta-premises about missing information
                    filtered_premises = []
                    z3_to_orig_index = {}
                    for i, p in enumerate(request.premises or []):
                        p_lower = p.lower()
                        if any(phrase in p_lower for phrase in ["no premise states", "no information", "unknown whether", "not specified", "not mentioned", "no statement"]):
                            continue
                        z3_to_orig_index[len(filtered_premises)] = i
                        filtered_premises.append(p)

                    code = reasoner.generate_z3_code(
                        filtered_premises, filtered_premises, full_q
                    )
                    if code:
                        output = execute_z3_code(code)
                        if output is None:
                            code2 = reasoner.refine_z3_code(
                                code, "Execution returned no output", filtered_premises
                            )
                            output = execute_z3_code(code2) if code2 else None
                        
                        if output:
                            # Parse Z3 output
                            raw = output.strip()
                            lines = [l.strip().lower() for l in raw.split('\n') if l.strip()]
                            
                            z3_ans = None
                            # Direct MCQ letter
                            for line in lines:
                                for ch in ('a', 'b', 'c', 'd'):
                                    if line == ch or line.startswith(f"{ch}.") or line.startswith(f"{ch})"):
                                        z3_ans = ch.upper()
                                        break
                                if z3_ans:
                                    break
                                    
                            # Multi-line MCQ
                            if q_type == "mcq" and len(lines) >= 2 and not z3_ans:
                                option_letters = ['A', 'B', 'C', 'D']
                                for i, line in enumerate(lines):
                                    if i < len(option_letters) and line in ('yes', 'true'):
                                        z3_ans = option_letters[i]
                                        break
                                        
                            # Yes/No
                            if not z3_ans:
                                ans_match = re.search(r'\bANSWER:\s*(\w+)', raw, re.IGNORECASE)
                                if ans_match:
                                    ans_val = ans_match.group(1).strip().capitalize()
                                    if ans_val in ('Yes', 'No', 'Unknown', 'Uncertain'):
                                        z3_ans = ans_val
                                if not z3_ans:
                                    full_lower = raw.lower()
                                    if re.search(r'\byes\b', full_lower):
                                        z3_ans = 'Yes'
                                    elif re.search(r'\bno\b', full_lower):
                                        z3_ans = 'No'
                                    elif re.search(r'\bunknown\b', full_lower) or re.search(r'\buncertain\b', full_lower):
                                        z3_ans = 'Unknown'
                                    
                            # Parse premises used from Z3
                            p_match = re.search(r'PREMISES USED:\s*\[([^\]]*)\]', output)
                            z3_premises_used = []
                            if p_match:
                                try:
                                    parsed_indices = [int(x.strip()) - 1 for x in p_match.group(1).split(',') if x.strip()]
                                    # Map back to original indices
                                    z3_premises_used = [z3_to_orig_index[idx] for idx in parsed_indices if idx in z3_to_orig_index]
                                    z3_premises_used = [idx for idx in z3_premises_used if 0 <= idx < len(request.premises or [])]
                                except Exception:
                                    pass
                                    
                            if q_type == "mcq" and p_match is None and z3_ans in ('A', 'B', 'C', 'D'):
                                logger.info(
                                    f"[TYPE1] Z3 MCQ answer '{z3_ans}' was a fallback (no proof) — treating as Unknown"
                                )
                                z3_ans = "Unknown"

                            if z3_ans and z3_ans in ('Yes', 'No', 'A', 'B', 'C', 'D', 'Unknown'):
                                # If it's a yes_no question but Z3 generated and solved it as MCQ
                                if q_type == "yes_no" and z3_ans in ('A', 'B', 'C'):
                                    mapped_ans = {'A': 'Yes', 'B': 'No', 'C': 'Unknown'}[z3_ans]
                                    logger.info(f"[TYPE1] Mapped Z3 MCQ output '{z3_ans}' to yes_no '{mapped_ans}'")
                                    z3_ans = mapped_ans

                                # Type-safety guard: for yes_no questions, only accept
                                # Yes/No/Unknown from Z3 (not MCQ letters A/B/C/D which
                                # indicate the Z3 code misinterpreted the question type).
                                z3_type_valid = True
                                if q_type == "yes_no" and z3_ans in ('A', 'B', 'C', 'D'):
                                    logger.warning(
                                        f"[TYPE1] Z3 returned MCQ letter '{z3_ans}' for yes_no question — ignoring"
                                    )
                                    z3_type_valid = False
                                elif q_type == "mcq" and z3_ans in ('Yes', 'No'):
                                    logger.warning(
                                        f"[TYPE1] Z3 returned Yes/No '{z3_ans}' for MCQ question — ignoring"
                                    )
                                    z3_type_valid = False

                                cot_confident = bool(answer and answer.strip())
                                z3_agrees = (z3_ans == answer)

                                # Determine if Z3 gives a CONCRETE (non-Unknown) answer
                                z3_is_concrete = z3_ans in ('A', 'B', 'C', 'D', 'Yes', 'No')

                                if not z3_type_valid:
                                    # Z3 returned wrong answer type for this question — skip
                                    logger.warning(f"[TYPE1] Z3 type mismatch (IGNORED): CoT={answer}, Z3={z3_ans}")
                                elif z3_agrees:
                                    # Z3 confirms CoT — use Z3's premises (minimal unsat core)
                                    # instead of merging, because Z3 premises are more precise.
                                    explanation = f"[Formal Verification] Formally verified by Z3. \n{explanation}"
                                    if z3_premises_used:
                                        premises_used = z3_premises_used
                                elif z3_is_concrete and cot_confident:
                                    # Z3 gives a CONCRETE answer that DISAGREES with CoT.
                                    # Trust Z3: formal verification is more reliable than
                                    # CoT's pattern-matching for deductive logic tasks.
                                    # (Round 1 evidence: T1_0025 CoT=B/Z3=C✓, T1_0035
                                    #  CoT=B/Z3=D✓, T1_0007 CoT=C/Z3=B✓)
                                    logger.warning(f"[TYPE1] Z3 OVERRIDES CoT: CoT={answer} -> Z3={z3_ans}")
                                    answer = z3_ans
                                    explanation = f"[Formal Verification] Z3 override: {explanation}"
                                    if z3_premises_used:
                                        premises_used = z3_premises_used
                                elif not cot_confident:
                                    # CoT had no answer — accept Z3 (even Unknown)
                                    logger.info(f"[TYPE1] Z3 filled empty CoT: CoT={answer} -> Z3={z3_ans}")
                                    answer = z3_ans
                                    explanation = f"[Formal Verification] Formally verified by Z3. \n{explanation}"
                                    if z3_premises_used:
                                        premises_used = z3_premises_used
                                else:
                                    # Z3=Unknown with confident CoT.
                                    # If the question asks about provability/guarantee/satisfying requirements,
                                    # CoT is prone to hallucinate "Yes" by ignoring missing conditions.
                                    # Trust Z3's inability to prove: override to "No".
                                    q_lower = request.query.lower()
                                    if q_type == "yes_no" and any(w in q_lower for w in ["prove", "guarantee", "establish", "satisfy every", "ensure"]):
                                        logger.warning(f"[TYPE1] Z3 logical insufficiency detected. Overriding CoT '{answer}' with 'No'")
                                        answer = "No"
                                        if z3_premises_used:
                                            premises_used = z3_premises_used
                                    else:
                                        # Z3 "Unknown" usually reflects broken codegen, not
                                        # genuine proof of insufficiency.
                                        logger.warning(f"[TYPE1] Z3=Unknown, keeping CoT: CoT={answer}")
                except Exception as z3_err:
                    logger.error(f"[TYPE1] Z3 verification failed: {z3_err}")
                    
        except Exception as e:
            logger.error(f"[TYPE1] CoT failed: {e}")
    else:
        logger.debug("[TYPE1] LLM server DOWN — returning Unknown")

    if not answer:
        answer = "Unknown"
        explanation = explanation or "Type 1 reasoning unavailable (LLM server down)."

    # Sanitize and snap answer to expected options or Yes/No/Unknown format
    options_dict = None
    if request.options and not is_ynu_options:
        # Build options_dict only for true MCQ (not for Yes/No/Uncertain options)
        options_dict = {}
        for opt in request.options:
            opt_str = opt.strip()
            # Match "A. Option Text" or similar
            match = re.match(r'^([A-D])[.\)\s]\s*(.*)$', opt_str, re.DOTALL | re.IGNORECASE)
            if match:
                options_dict[match.group(1).upper()] = match.group(2).strip()
            else:
                # Fallback if no dot/parenthesis
                if len(opt_str) > 0 and opt_str[0].upper() in ('A', 'B', 'C', 'D'):
                    options_dict[opt_str[0].upper()] = opt_str[1:].strip()
        if not options_dict:
            # Fallback by index
            letters = ['A', 'B', 'C', 'D']
            options_dict = {letters[i]: opt for i, opt in enumerate(request.options) if i < len(letters)}

    from pipeline.type1.question_classifier import sanitize_and_snap_answer
    
    # For Yes/No/Uncertain options, map letter answers (A/B/C) back to values first
    if is_ynu_options and answer in ('A', 'B', 'C', 'D'):
        letters = ['A', 'B', 'C', 'D']
        idx = letters.index(answer)
        if idx < len(request.options):
            answer = request.options[idx].strip()
    
    answer = sanitize_and_snap_answer(
        answer=answer,
        question_type=q_type,
        options=options_dict,
        explanation=explanation,
        query=request.query
    )

    # For Yes/No/Uncertain options, map canonical answer to exact option string
    # (e.g., "Unknown" → "Uncertain" if "Uncertain" is in options)
    if is_ynu_options and request.options:
        opt_lower_map = {o.strip().lower(): o.strip() for o in request.options}
        ans_lower = answer.strip().lower()
        if ans_lower in opt_lower_map:
            answer = opt_lower_map[ans_lower]
        elif ans_lower in ('unknown', 'uncertain'):
            # Try to map to other uncertainty variants
            mapped = False
            for var in ('uncertain', 'unknown', 'cannot determine', 'cannot be determined', 'maybe', 'none of the above'):
                if var in opt_lower_map:
                    answer = opt_lower_map[var]
                    mapped = True
                    break

    # Map key ('A', 'B', 'C', 'D') back to the original option string to satisfy exactly-one-of-the-options rule
    if request.options and not is_ynu_options and answer in ('A', 'B', 'C', 'D'):
        mapped_answer = None
        for opt in request.options:
            opt_str = opt.strip()
            match = re.match(r'^([A-D])[.\)\s]\s*(.*)$', opt_str, re.DOTALL | re.IGNORECASE)
            if match and match.group(1).upper() == answer:
                mapped_answer = opt
                break
            elif len(opt_str) > 0 and opt_str[0].upper() == answer:
                mapped_answer = opt
                break
        if mapped_answer:
            answer = mapped_answer
        else:
            letters = ['A', 'B', 'C', 'D']
            if answer in letters:
                idx = letters.index(answer)
                if idx < len(request.options):
                    answer = request.options[idx]

    # Proactive Missing Information / Uncertainty Override
    # Skip for MCQ — MCQ always has a definite answer from options
    if q_type != "mcq":
        missing_phrases = ["no premise states", "no information", "unknown whether", "not specified", "not mentioned", "no statement", "is unknown"]
        # Use only the question line (not MCQ option text) for keyword extraction
        query_first_line = request.query.split('\n')[0]
        q_words_proactive = set(re.findall(r'\w+', query_first_line.lower()))
        stop_words_proactive = {
            'does', 'do', 'did', 'is', 'are', 'was', 'were', 'have', 'has', 'had',
            'whether', 'about', 'a', 'an', 'the', 'can', 'could', 'should', 'would',
            'be', 'been', 'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'who',
            'what', 'which', 'how', 'where', 'when', 'whose', 'whom', 'page', 'user'
        }
        q_keywords_proactive = {w for w in q_words_proactive if w not in stop_words_proactive and len(w) >= 3}
        # Exclude entity names (capitalized words like Asha, Alpha) — matching only on
        # entity names causes false positives when the question is about a different property
        entity_names = {w.lower() for w in re.findall(r'\b[A-Z][a-z]*\b', query_first_line)}
        q_keywords_proactive = q_keywords_proactive - entity_names
        
        missing_info_premise_idx = None
        for i, p in enumerate(request.premises or []):
            p_lower = p.lower()
            if any(phrase in p_lower for phrase in missing_phrases):
                p_words = set(re.findall(r'\w+', p_lower))
                # Also strip entity names from premise words for the comparison
                overlap = q_keywords_proactive.intersection(p_words)
                if overlap:
                    missing_info_premise_idx = i
                    break
                    
        if missing_info_premise_idx is not None:
            uncertain_ans = "Uncertain"
            if request.options:
                for opt in request.options:
                    opt_clean = opt.strip().lower()
                    if any(u in opt_clean for u in ['uncertain', 'cannot determine', 'cannot be determined', 'unknown', 'maybe', 'none of the above']):
                        uncertain_ans = opt
                        break
            answer = uncertain_ans
            premises_used = [missing_info_premise_idx]

    # 1. Direct fact lookup for open-ended questions (when model is uncertain or has no digits for numeric questions)
    if not request.options:
        ans_lower_temp = str(answer).lower()
        is_uncertain_temp = ans_lower_temp in ("unknown", "uncertain", "cannot determine", "cannot be determined", "maybe", "none of the above")
        is_numeric_q = any(q in request.query.lower() for q in ["how many", "how much", "total number", "count of", "number of"])
        has_digits_temp = bool(re.search(r'\d+', str(answer)))
        
        if is_uncertain_temp or (is_numeric_q and not has_digits_temp):
            # Try direct lookup
            query_lower = request.query.lower()
            q_words = set(re.findall(r'\w+', query_lower))
            stop_words_lookup = {
                'if', 'then', 'else', 'every', 'each', 'all', 'any', 'some', 'a', 'an', 'the',
                'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had', 'do', 'does', 'did',
                'who', 'which', 'that', 'this', 'these', 'those', 'to', 'of', 'in', 'on', 'at', 'by',
                'for', 'with', 'about', 'and', 'or', 'not', 'no', 'can', 'could', 'should', 'would',
                'researcher', 'person', 'someone', 'individual', 'member', 'user', 'does', 'how', 'many',
                'much', 'total', 'count', 'number', 'have', 'has', 'had'
            }
            q_keywords_lookup = {w for w in q_words if w not in stop_words_lookup and len(w) >= 3}
            
            best_idx = None
            best_overlap = 0
            best_match_val = None
            
            for idx, p in enumerate(request.premises or []):
                p_lower = p.lower()
                if any(phrase in p_lower for phrase in ["no premise states", "no information", "unknown whether", "not specified", "not mentioned", "no statement", "is unknown"]):
                    continue
                p_words = set(re.findall(r'\w+', p_lower))
                overlap = len(q_keywords_lookup.intersection(p_words))
                if overlap > best_overlap:
                    if is_numeric_q:
                        num_match = re.search(r'\b\d+\b', p_lower)
                        if num_match:
                            best_overlap = overlap
                            best_idx = idx
                            best_match_val = num_match.group(0)
                        else:
                            word_to_num = {
                                "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                                "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"
                            }
                            for word, val in word_to_num.items():
                                if re.search(r'\b' + word + r'\b', p_lower):
                                    best_overlap = overlap
                                    best_idx = idx
                                    best_match_val = val
                                    break
            
            if best_idx is not None and best_overlap >= max(1, int(len(q_keywords_lookup) * 0.5)):
                answer = best_match_val
                premises_used = [best_idx]
                logger.info(f"[TYPE1] Direct fact lookup overrode answer to: {answer} (premise {best_idx})")

    # Post-process for Unknown/Uncertain premise extraction
    ans_lower = answer.strip().lower()
    is_uncertain_ans = ans_lower in ("unknown", "uncertain", "cannot determine", "cannot be determined", "maybe", "none of the above")
    if not is_uncertain_ans and options_dict and answer in options_dict:
        is_uncertain_ans = options_dict[answer].strip().lower() in ("unknown", "uncertain", "cannot determine", "cannot be determined", "maybe", "none of the above")
        
    if is_uncertain_ans:
        unknown_indices = []
        for i, p in enumerate(request.premises or []):
            p_lower = p.lower()
            if any(phrase in p_lower for phrase in ["no premise states", "no information", "unknown whether", "not specified", "not mentioned", "no statement", "is unknown", "not provided"]):
                unknown_indices.append(i)
        # For Uncertain/Unknown answers, the premises_used should strictly be the uncertainty/absence premises if they exist
        if unknown_indices:
            premises_used = sorted(list(set(unknown_indices)))
        else:
            premises_used = list(range(len(request.premises or [])))

    # Coreference pronoun detector and sibling distractor exclusion for open-ended questions
    if not request.options and answer and not is_uncertain_ans:
        ans_clean = str(answer).strip().lower()
        if len(ans_clean) >= 2 and ans_clean not in ('yes', 'no', 'unknown', 'uncertain'):
            # Find the premise index containing the answer
            ans_idx = None
            for i, p in enumerate(request.premises or []):
                p_lower = p.lower()
                if ans_clean in p_lower or any(part in p_lower for part in ans_clean.split() if len(part) >= 3 and part not in ('professor', 'dr', 'mr', 'ms', 'study', 'project', 'department', 'office', 'team', 'room')):
                    ans_idx = i
                    break
            
            if ans_idx is not None:
                # 1. Check pronoun coreferences
                q_words = set(re.findall(r'\w+', request.query.lower()))
                stop_words = {
                    'who', 'what', 'where', 'when', 'why', 'how', 'which', 'whom',
                    'is', 'are', 'was', 'were', 'do', 'does', 'did', 'have', 'has', 'had',
                    'a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
                    'about', 'many', 'much', 'total', 'across', 'both', 'all', 'any', 'each',
                    'does', 'do', 'can', 'could', 'should', 'would', 'be', 'been', 'get', 'gets'
                }
                q_keywords = {w for w in q_words if w not in stop_words and len(w) >= 3}
                
                for i, p in enumerate(request.premises or []):
                    if i == ans_idx:
                        continue
                    p_lower = p.lower()
                    words_in_p = set(re.findall(r'\w+', p_lower))
                    has_pronoun = bool(words_in_p.intersection({'she', 'he', 'it', 'they'}))
                    has_q_keywords = bool(q_keywords.intersection(words_in_p))
                    
                    if has_pronoun and has_q_keywords:
                        if ans_idx not in premises_used:
                            premises_used.append(ans_idx)
                        if i not in premises_used:
                            premises_used.append(i)
                premises_used = sorted(list(set(premises_used)))

                # 2. Sibling distractor exclusion
                if len(premises_used) > 1:
                    has_single_source = False
                    single_source_idx = None
                    for idx in premises_used:
                        p_lower = request.premises[idx].lower()
                        has_ans = (ans_clean in p_lower) or any(part in p_lower for part in ans_clean.split() if len(part) >= 3 and part not in ('professor', 'dr', 'mr', 'ms', 'project', 'department', 'office', 'team', 'room'))
                        has_q = bool(q_keywords.intersection(set(re.findall(r'\w+', p_lower))))
                        if has_ans and has_q:
                            others_dont_have = True
                            for other_idx in premises_used:
                                if other_idx == idx:
                                    continue
                                p_other_lower = request.premises[other_idx].lower()
                                if (ans_clean in p_other_lower) or any(part in p_other_lower for part in ans_clean.split() if len(part) >= 3 and part not in ('professor', 'dr', 'mr', 'ms', 'project', 'department', 'office', 'team', 'room')):
                                    others_dont_have = False
                                    break
                            if others_dont_have:
                                has_single_source = True
                                single_source_idx = idx
                                break

                    if has_single_source and single_source_idx is not None:
                        is_pure_distractor = True
                        for other_idx in premises_used:
                            if other_idx == single_source_idx:
                                continue
                            p_other = request.premises[other_idx]
                            p_other_lower = p_other.lower()
                            p_other_word_set = set(re.findall(r'\w+', p_other_lower))
                            # If the other premise contains a pronoun, it's a coreference, not a distractor
                            if p_other_word_set.intersection({'she', 'he', 'it', 'they'}):
                                is_pure_distractor = False
                                break
                            p_other_words = re.findall(r'\b[A-Z][a-z]*\b', p_other)
                            q_cap_words = set(re.findall(r'\b[A-Z][a-z]*\b', request.query))
                            other_cap = [w for w in p_other_words if w not in q_cap_words]
                            if not other_cap:
                                is_pure_distractor = False
                                break
                            
                            # Linking premise check (check for any common non-stop capitalized word shared with the single source)
                            generic_prefixes = {
                                'Project', 'Server', 'Team', 'Study', 'Lab', 'File', 'Device',
                                'Task', 'User', 'Router', 'Department', 'The', 'A', 'An', 'If',
                                'Every', 'Whether', 'Only', 'Either', 'All', 'Each', 'No', 'Not',
                                'But', 'Or', 'And', 'So', 'It', 'Is', 'Are', 'Was', 'Were',
                                'Has', 'Have', 'Had', 'Do', 'Does', 'Did'
                            }
                            p_source = request.premises[single_source_idx]
                            source_cap = set(re.findall(r'\b[A-Z][a-z]*\b', p_source))
                            shared_cap = set(other_cap).intersection(source_cap) - generic_prefixes
                            if shared_cap:
                                is_pure_distractor = False
                                break

                        if is_pure_distractor:
                            premises_used = [single_source_idx]

    # 3. Backward Reachability Filter to prune unnecessary premises
    if not is_uncertain_ans and premises_used and len(premises_used) > 1:
        reachability_stop = {
            'if', 'then', 'else', 'every', 'each', 'all', 'any', 'some', 'a', 'an', 'the',
            'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had', 'do', 'does', 'did',
            'who', 'which', 'that', 'this', 'these', 'those', 'to', 'of', 'in', 'on', 'at', 'by',
            'for', 'with', 'about', 'and', 'or', 'not', 'no', 'can', 'could', 'should', 'would',
            'researcher', 'person', 'someone', 'individual', 'member', 'user', 'study', 'project',
            'team', 'office', 'department', 'room'
        }
        
        def split_premise_internal(text: str):
            text_lower = text.lower()
            def get_clean_set(s: str):
                return {w for w in re.findall(r'\w+', s) if w not in reachability_stop and len(w) >= 3}
            if "if" in text_lower:
                if "then" in text_lower:
                    parts = text_lower.split("then", 1)
                    return get_clean_set(parts[0]), get_clean_set(parts[1])
                else:
                    parts = text_lower.split(",", 1)
                    if len(parts) > 1:
                        return get_clean_set(parts[0]), get_clean_set(parts[1])
            if ("every" in text_lower or "each" in text_lower) and "is" in text_lower:
                parts = text_lower.split("is", 1)
                return get_clean_set(parts[0]), get_clean_set(parts[1])
            return set(), get_clean_set(text_lower)

        q_words = set(re.findall(r'\w+', request.query.lower()))
        target_set = {w for w in q_words if w not in reachability_stop and len(w) >= 3}
        ans_clean_words = {w for w in re.findall(r'\w+', str(answer).lower()) if w not in reachability_stop and len(w) >= 3}
        target_set.update(ans_clean_words)
        
        reachable_indices = set()
        added = True
        while added:
            added = False
            for idx in list(premises_used):
                if idx in reachable_indices:
                    continue
                ant_words, cons_words = split_premise_internal(request.premises[idx])
                if ant_words:
                    if cons_words.intersection(target_set):
                        reachable_indices.add(idx)
                        target_set.update(ant_words)
                        added = True
                        
        for idx in list(premises_used):
            if idx in reachable_indices:
                continue
            ant_words, cons_words = split_premise_internal(request.premises[idx])
            if not ant_words:
                if cons_words.intersection(target_set):
                    reachable_indices.add(idx)
                    
        if reachable_indices:
            ans_clean = str(answer).strip().lower()
            for i, p in enumerate(request.premises or []):
                if ans_clean in p.lower() and i in premises_used:
                    reachable_indices.add(i)
            premises_used = sorted(list(reachable_indices.intersection(set(premises_used))))

    log_pipeline_request(
        question=request.query, query_type="type1", answer=str(answer),
        confidence=0.0, has_fol=False, has_cot=bool(steps), fol_retries=0,
        fallback_triggered=(answer == "Unknown"), z3_timeout=False,
        solver_source="llm_cot",
    )

    return build_response(
        query_id=request.query_id,
        query_type="type1",
        answer=answer,
        explanation=explanation,
        raw_unit="",
        steps=steps,
        premises_used=premises_used,
    )


# ══════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════

@app.post("/predict", response_model=list[UnifiedResponse])
async def handle_predict(request: UnifiedRequest):
    collect_logs = (request.logs is True)
    token = None
    if collect_logs:
        from api.logger import request_logs
        token = request_logs.set([])
        
    try:
        query_type = request.type

        if query_type == "type2":
            responses = [_run_type2_pipeline(request)]
        else:
            responses = [_run_type1_pipeline(request)]

        if collect_logs:
            from api.logger import request_logs
            logs_captured = request_logs.get()
            for res in responses:
                res.logs = logs_captured

        return responses

    except Exception as e:
        # Never 500 on a pipeline error — return a format-valid response so a single
        # failing query can't break committee parsing or the run; it is simply scored
        # wrong. query_id is echoed and explanation is non-empty (spec §4.2 / §9).
        logger.error(f"Pipeline error: {e}", exc_info=True)
        fallback_res = build_response(
            query_id=request.query_id,
            query_type=request.type,
            answer="Unknown",
            explanation="The system was unable to process this query.",
            premises_used=[],
        )
        if collect_logs:
            from api.logger import request_logs
            fallback_res.logs = request_logs.get()
        return [fallback_res]
        
    finally:
        if token is not None:
            from api.logger import request_logs
            request_logs.reset(token)


@app.get("/v1/models")
async def proxy_models():
    """Forward vLLM's model list so the committee can verify the served model
    (≤8B rule) without exposing the internal vLLM port to the Internet. The
    returned `id` comes from the model's real config.json — verifiable."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{VLLM_BASE}/v1/models")
        return resp.json()
    except Exception as e:
        logger.error(f"/v1/models proxy failed: {e}")
        raise HTTPException(status_code=503, detail=f"vLLM unreachable: {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}

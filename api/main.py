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
    q_type = "mcq" if request.options else "yes_no"
    full_q = request.query
    if request.options:
        full_q = full_q + "\n" + "\n".join(request.options)

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
            if len(request.premises or []) <= 7:
                try:
                    from pipeline.type1.z3_solver import execute_z3_code
                    
                    class MockClassified:
                        def __init__(self, original, q_type_str):
                            self.original = original
                            from pipeline.type1.question_classifier import QuestionType
                            self.question_type = QuestionType.MCQ if q_type_str == "mcq" else QuestionType.YES_NO
                    
                    classified = MockClassified(full_q, q_type)
                    code = reasoner.generate_z3_code(
                        request.premises or [], request.premises or [], full_q
                    )
                    if code:
                        output = execute_z3_code(code)
                        if output is None:
                            code2 = reasoner.refine_z3_code(
                                code, "Execution returned no output", request.premises or []
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
                            if q_type != "mcq" and not z3_ans:
                                full_lower = raw.lower()
                                if 'yes' in full_lower:
                                    z3_ans = 'Yes'
                                elif 'no' in full_lower:
                                    z3_ans = 'No'
                                elif 'unknown' in full_lower:
                                    z3_ans = 'Unknown'
                                    
                            # Parse premises used from Z3
                            import re
                            p_match = re.search(r'PREMISES USED:\s*\[([^\]]*)\]', output)
                            z3_premises_used = []
                            if p_match:
                                try:
                                    z3_premises_used = [int(x.strip()) - 1 for x in p_match.group(1).split(',') if x.strip()]
                                    z3_premises_used = [idx for idx in z3_premises_used if 0 <= idx < len(request.premises or [])]
                                except Exception:
                                    pass
                                    
                            if z3_ans and z3_ans in ('Yes', 'No', 'A', 'B', 'C', 'D', 'Unknown'):
                                if z3_ans != answer:
                                    logger.info(f"[TYPE1] Z3 overrode answer: CoT={answer} -> Z3={z3_ans}")
                                    answer = z3_ans
                                    explanation = f"[Formal Verification] Formally verified by Z3. \n{explanation}"
                                if z3_premises_used:
                                    premises_used = z3_premises_used
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
    if request.options:
        options_dict = {}
        for opt in request.options:
            opt_str = opt.strip()
            # Match "A. Option Text" or similar
            match = re.match(r'^([A-D])[\.\)\s]\s*(.*)$', opt_str, re.DOTALL | re.IGNORECASE)
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
    answer = sanitize_and_snap_answer(
        answer=answer,
        question_type=q_type,
        options=options_dict,
        explanation=explanation
    )

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
    try:
        query_type = request.type

        if query_type == "type2":
            return [_run_type2_pipeline(request)]

        return [_run_type1_pipeline(request)]

    except Exception as e:
        # Never 500 on a pipeline error — return a format-valid response so a single
        # failing query can't break committee parsing or the run; it is simply scored
        # wrong. query_id is echoed and explanation is non-empty (spec §4.2 / §9).
        logger.error(f"Pipeline error: {e}", exc_info=True)
        return [build_response(
            query_id=request.query_id,
            query_type=request.type,
            answer="Unknown",
            explanation="The system was unable to process this query.",
            premises_used=[],
        )]


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

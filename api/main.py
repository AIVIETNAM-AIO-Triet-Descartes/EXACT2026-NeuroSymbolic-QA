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

    The live request carries only NL premises (no premises-FOL — see docs/SYSTEM.md),
    so the symbolic LogicTree/Z3 path (which needs FOL) is unavailable here; we run
    `solve_with_cot` on the NL premises. `premises_used` is left empty for now —
    TODO #2: have the CoT report the used premise indices (or add an NL→FOL step to
    recover them from the proof trace) so the 50%-weighted premises_used scores.
    Never raises — falls back to "Unknown" when the LLM server is down.
    """
    q_type = "mcq" if request.options else "yes_no"
    full_q = request.query
    if request.options:
        full_q = full_q + "\n" + "\n".join(request.options)

    answer, explanation, steps = "", "", []
    from llm import llm_server_available
    if llm_server_available():
        try:
            from llm import get_shared_reasoner
            res = get_shared_reasoner().solve_with_cot(
                request.premises or [], [], full_q, q_type, None,
            ) or {}
            answer = (res.get("answer") or "").strip()
            explanation = (res.get("explanation") or "").strip()
            steps = [explanation] if explanation else []
        except Exception as e:
            logger.error(f"[TYPE1] CoT failed: {e}")
    else:
        logger.debug("[TYPE1] LLM server DOWN — returning Unknown")

    if not answer:
        answer = "Unknown"
        explanation = explanation or "Type 1 reasoning unavailable (LLM server down)."

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
        premises_used=[],   # TODO #2: real premise indices used in the proof
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

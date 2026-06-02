"""
API Server - EXACT 2026 Neuro-Symbolic QA System.

FastAPI app expose 2 endpoints:
    POST /query  — nhận question + premises, trả answer + explanation
    GET  /health — health check

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from api.router import classify_query
from api.schemas import QueryRequest, QueryResponse
from api.logger import get_logger

logger = get_logger(__name__)
app = FastAPI(title="EXACT 2026 QA API", version="0.1.0")


# ══════════════════════════════════════════════════════════════
# Track 2 pipeline
# ══════════════════════════════════════════════════════════════

def _run_type2_pipeline(request: QueryRequest) -> QueryResponse:
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
        "question": request.question,
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
            logger.warning(f"[SELF_VERIFIER] Validation failed: {val.errors}")
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

    logger.info(
        f"[TYPE2] done answer={answer!r} confidence={confidence} "
        f"formula_rag_failed={state.get('_formula_rag_failed', False)}"
    )

    return QueryResponse(
        answer=answer,
        explanation=explanation,
        cot=cot,
        confidence=confidence,
    )


# ══════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════

@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    try:
        query_type = classify_query(request.question, request.premises)

        if query_type == "type2":
            return _run_type2_pipeline(request)

        # Type 1 — TODO: wire after Track 1 nodes are complete
        return QueryResponse(
            answer="A",
            explanation=f"[TYPE1 MOCK] Pipeline not yet connected.",
        )

    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}

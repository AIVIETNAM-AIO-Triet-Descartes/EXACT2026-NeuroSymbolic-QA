"""
pipeline/type2/explainer.py

LangGraph node [7] for Track 2: Generate NL explanation for physics solution.
Thin wrapper — LLM logic lives in llm/llm_reasoner.py::explain_physics().
"""

from loguru import logger

from pipeline.state import PipelineState


def explainer_node_type2(state: PipelineState) -> PipelineState:
    """
    Node 7 (Track 2): Call LLMReasoner.explain_physics() with SolverResult data.
    Falls back to hardcoded string if LLM call fails (never raises).
    """
    from llm import get_shared_reasoner

    try:
        reasoner = get_shared_reasoner()
        sr = state.get("solver_result") or {}

        explanation = reasoner.explain_physics(
            question=state["question"],
            answer=sr.get("answer", ""),
            unit=sr.get("unit", "") or "",
            steps=sr.get("steps", []),
        )
        return {**state, "explanation": explanation}

    except Exception as e:
        logger.error(f"[EXPLAINER_T2] Failed: {e}")
        answer = state.get("answer", "")
        unit = (state.get("solver_result") or {}).get("unit", "") or ""
        return {**state, "explanation": f"The answer is {answer} {unit}".strip() + "."}

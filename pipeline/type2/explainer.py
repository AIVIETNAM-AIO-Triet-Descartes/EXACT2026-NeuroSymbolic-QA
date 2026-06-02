"""
pipeline/type2/explainer.py

LangGraph node [7] for Track 2: Generate NL explanation for physics solution.
Thin wrapper — LLM logic lives in llm/llm_reasoner.py::explain_physics().
"""

from loguru import logger

from pipeline.state import PipelineState
from llm import llm_server_available


def explainer_node_type2(state: PipelineState) -> PipelineState:
    """
    Node 7 (Track 2): Call LLMReasoner.explain_physics() with SolverResult data.
    Falls back to hardcoded string if LLM call fails or server is DOWN.
    Never raises.
    """
    answer = state.get("answer", "")
    sr = state.get("solver_result") or {}
    unit = sr.get("unit", "") or ""
    fallback_explanation = f"The answer is {answer} {unit}".strip() + "."

    if not llm_server_available():
        logger.debug("[EXPLAINER_T2] LLM skipped (server DOWN, cached); using fallback")
        return {**state, "explanation": fallback_explanation}

    try:
        from llm import get_shared_reasoner
        reasoner = get_shared_reasoner()

        explanation = reasoner.explain_physics(
            question=state["question"],
            answer=answer,
            unit=unit,
            steps=sr.get("steps", []),
        )
        return {**state, "explanation": explanation}

    except Exception as e:
        logger.error(f"[EXPLAINER_T2] Failed: {e}")
        return {**state, "explanation": fallback_explanation}

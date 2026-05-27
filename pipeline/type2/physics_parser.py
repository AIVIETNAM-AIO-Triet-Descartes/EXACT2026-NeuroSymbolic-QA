"""
pipeline/type2/physics_parser.py

LangGraph node [3b]: Extract structured physics data from raw question text.
Thin wrapper — LLM logic lives in llm/llm_reasoner.py.
"""

from loguru import logger

from pipeline.state import PipelineState
from pipeline.type2.type2_classifier import PhysicsClassifier


def physics_parser_node(state: PipelineState) -> PipelineState:
    """
    Node 3b: Parse physics question into structured dict.

    Calls PhysicsClassifier first for domain/target priors, then delegates
    variable extraction to LLMReasoner.parse_physics_question(). Classifier
    overrides LLM output when LLM misses domain or target variable.
    """
    from llm import get_shared_reasoner

    try:
        classified = PhysicsClassifier().classify_physics(state["question"])
        reasoner = get_shared_reasoner()
        parsed = reasoner.parse_physics_question(state["question"])

        # Classifier overrides: fill gaps left by LLM
        if not parsed.get("find") and classified.target_variable:
            parsed["find"] = classified.target_variable
        if parsed.get("domain") == "general":
            parsed["domain"] = classified.domain

        # Attach question_type for sympy_solver dispatch
        parsed["question_type"] = classified.question_type.value

        confidence = state.get("confidence", 1.0)
        if not parsed.get("find"):
            confidence = 0.3
            logger.warning("[PHYSICS_PARSER] target variable not detected, confidence=0.3")

        logger.info(
            f"[PHYSICS_PARSER] domain={parsed['domain']} "
            f"find={parsed.get('find')} type={parsed['question_type']}"
        )
        return {**state, "parsed_physics": parsed, "confidence": confidence}

    except Exception as e:
        logger.error(f"[PHYSICS_PARSER] Failed: {e}")
        return {
            **state,
            "parsed_physics": {
                "given": {}, "find": "", "domain": "general",
                "formulas": [], "units": {}, "question_type": "single_formula",
            },
            "confidence": 0.3,
        }

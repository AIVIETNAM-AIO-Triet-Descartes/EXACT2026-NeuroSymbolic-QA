"""
pipeline/type2/physics_parser.py

LangGraph node [3b]: Extract structured physics data from raw question text.

Two-stage extraction (addresses weakness #3 — LLM-only extraction was fragile):
  1. Deterministic regex pre-pass (pipeline/type2/regex_extract.py) — no LLM.
     Extracts obvious `symbol = value unit` assignments with SI conversion.
  2. LLM augment (best-effort) — fills gaps regex can't catch ("charged to 3V",
     implicit values, formula hints). Tolerates a down vLLM server.

Merge precedence: regex `given`/`find` win (deterministic), LLM fills the rest.

Fix B (2026-06-02): health-check via llm.llm_server_available() — singleton
  cached at llm/__init__.py level so all pipeline nodes share one probe result.
"""

from loguru import logger

from pipeline.state import PipelineState
from pipeline.type2.type2_classifier import PhysicsClassifier
from pipeline.type2.regex_extract import extract_given, detect_find_from_verb
from llm import llm_server_available


# ── Main node ─────────────────────────────────────────────────────────────────

def physics_parser_node(state: PipelineState) -> PipelineState:
    """
    Node 3b: Parse physics question into structured dict.

    Stage 1 regex pre-pass is deterministic and runs even if the LLM server is
    down. Stage 2 LLM augment is best-effort. Classifier supplies domain/type
    priors. Never raises — always returns a parsed_physics dict.
    """
    question = state.get("question", "")
    confidence = state.get("confidence", 1.0)

    # Classifier priors (domain / question_type / weak target prior)
    try:
        classified = PhysicsClassifier().classify_physics(question)
    except Exception as e:
        logger.warning(f"[PHYSICS_PARSER] classifier failed: {e}")
        classified = None

    # ── Stage 1: deterministic regex pre-pass (no LLM) ────────────────────────
    regex_given: dict = {}
    regex_find = None
    phrasal_keys: set = set()
    try:
        regex_given, phrasal_keys = extract_given(question, return_phrasal=True)
        regex_find = detect_find_from_verb(question)
    except Exception as e:
        logger.warning(f"[PHYSICS_PARSER] regex prepass failed: {e}")

    # ── Stage 2: LLM augment (best-effort — skip when server is DOWN) ─────────
    llm_parsed: dict = {}
    if llm_server_available():
        try:
            from llm import get_shared_reasoner
            llm_parsed = get_shared_reasoner().parse_physics_question(question) or {}
        except Exception as e:
            logger.warning(f"[PHYSICS_PARSER] LLM augment skipped ({e}); regex-only")
    else:
        logger.debug("[PHYSICS_PARSER] LLM augment skipped (server DOWN, cached)")

    # ── Merge ─────────────────────────────────────────────────────────────────
    parsed: dict = {
        "given": {}, "find": "", "domain": "general",
        "formulas": [], "units": {},
    }
    for k in parsed:
        if llm_parsed.get(k):
            parsed[k] = llm_parsed[k]

    # given: LLM values first, regex overrides on conflict (deterministic wins).
    # Coerce to float + drop non-numeric — LLM can emit symbolic strings (e.g. "q")
    # that would crash numeric solvers (sympy/vector) downstream.
    merged_given = dict(parsed.get("given") or {})
    merged_given.update(regex_given)
    clean_given = {}
    for k, v in merged_given.items():
        try:
            clean_given[k] = float(v)
        except (TypeError, ValueError):
            logger.debug(f"[PHYSICS_PARSER] drop non-numeric given {k}={v!r}")
    parsed["given"] = clean_given

    # find priority: regex verb-context > LLM > classifier prior
    if regex_find:
        parsed["find"] = regex_find
    if not parsed.get("find") and classified and classified.target_variable:
        parsed["find"] = classified.target_variable

    # domain: keep LLM domain unless missing/"general", then classifier prior
    if (not parsed.get("domain") or parsed["domain"] == "general") and classified:
        parsed["domain"] = classified.domain

    # Flag whether any *used* given value came only from the (less reliable) prose
    # phrasal pass — sympy_solver uses this to defer a verify-failing symbolic
    # answer to the PAL/LLM chain instead of blocking it (when the LLM is up).
    parsed["_phrasal_used"] = bool(phrasal_keys & set(clean_given.keys()))

    # question_type for sympy_solver dispatch
    parsed["question_type"] = (
        classified.question_type.value if classified else "single_formula"
    )

    # Yes/No, error-calc, multi-answer and qualitative do NOT need a scalar `find`
    # or a regex-extracted `given` (handled by resonance_solver / error_solver /
    # LLM) — don't penalize their confidence for empty find/given here.
    _find_optional = {"yes_no", "error_calc", "multi_answer", "qualitative"}
    if parsed["question_type"] not in _find_optional:
        if not parsed.get("find"):
            confidence = 0.3
            logger.warning("[PHYSICS_PARSER] target variable not detected, confidence=0.3")
        elif not parsed.get("given"):
            confidence = min(confidence, 0.5)
            logger.warning("[PHYSICS_PARSER] no given values extracted, confidence<=0.5")

    logger.info(
        f"[PHYSICS_PARSER] domain={parsed['domain']} find={parsed.get('find')} "
        f"type={parsed['question_type']} given_keys={list(parsed['given'])} "
        f"(regex={len(regex_given)}, llm={len(llm_parsed.get('given', {}) if llm_parsed else {})})"
    )
    return {**state, "parsed_physics": parsed, "confidence": confidence}

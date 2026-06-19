"""
pipeline/type1/z3_rag.py

Z3 RAG Exemplar Selector — picks the most relevant Z3 code exemplars
for a given set of premises and question, using keyword/tag matching.

This module loads exemplars from data/z3_exemplars.json and selects
the top-k most relevant ones based on pattern detection in the input.
"""

import json
import os
import re
from typing import List, Dict, Optional
from loguru import logger

_EXEMPLARS: Optional[List[Dict]] = None
_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "z3_exemplars.json"
)


def _load_exemplars() -> List[Dict]:
    """Load exemplars from JSON file (cached)."""
    global _EXEMPLARS
    if _EXEMPLARS is not None:
        return _EXEMPLARS
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            _EXEMPLARS = json.load(f)
        logger.debug(f"[Z3_RAG] Loaded {len(_EXEMPLARS)} exemplars from {_DATA_PATH}")
    except Exception as e:
        logger.warning(f"[Z3_RAG] Failed to load exemplars: {e}")
        _EXEMPLARS = []
    return _EXEMPLARS


def _detect_tags(premises: List[str], question: str) -> set:
    """Detect pattern tags from premises and question text using robust regex."""
    tags = set()
    text = " ".join(premises) + " " + question
    text_lower = text.lower()

    # Question type — use the full text to detect MCQ (options may be embedded in question)
    q_lower = question.lower().strip()
    if re.search(r'\b(yes|no|does|do|is|are|can|will|should|has|have)\b', q_lower):
        tags.add("yes_no")
    # Detect MCQ from common option formats: A./B., (a)/(b), 1./2., etc.
    if (re.search(r'\n\s*[A-D][.)]\s', question) or
            re.search(r'\n\s*\([a-d]\)\s', question) or
            re.search(r'\n\s*[1-4][.)]\s', question) or
            any(ch in question for ch in ["A.", "B.", "C.", "D.", "(a)", "(b)", "(c)", "(d)"])):
        tags.add("mcq")

    # Pattern detection using word boundaries
    if re.search(r'\b(not|cannot|never|no|n\'t)\b', text_lower):
        tags.add("negation")

    if re.search(r'\b(eligible|qualified)\b', text_lower):
        tags.add("eligibility_vs_actuality")

    # Count conditional rules (if...then) using word boundaries
    rule_count = len(re.findall(r'\bif\b', text_lower))
    if rule_count >= 3:
        tags.add("chain")

    if re.search(r'\b(or|either)\b', text_lower):
        tags.add("disjunction")

    if re.search(r'\b(missing|cannot)\b', q_lower):
        tags.add("missing_condition")

    # Check for multiple independent chains (different domains in premises)
    if rule_count >= 4:
        tags.add("multiple_chains")

    if re.search(r'\b(strongest|best supported)\b', q_lower):
        tags.add("strongest_conclusion")

    if re.search(r'\b(fewest|minimum)\b', q_lower):
        tags.add("contraposition")

    return tags


def select_exemplars(
    premises: List[str],
    question: str,
    k: int = 3,
) -> List[Dict]:
    """
    Select the top-k most relevant Z3 code exemplars based on tag overlap
    between the input and the exemplar patterns.

    Args:
        premises: List of NL premise strings.
        question: The question text.
        k: Number of exemplars to return.

    Returns:
        List of exemplar dicts with keys: premises_nl, question, z3_code, expected_answer.
    """
    exemplars = _load_exemplars()
    if not exemplars:
        return []

    input_tags = _detect_tags(premises, question)
    logger.debug(f"[Z3_RAG] Detected tags: {input_tags}")
    is_mcq = "mcq" in input_tags

    # Filter exemplars by matching MCQ vs Yes/No type
    filtered_exemplars = []
    for ex in exemplars:
        ex_tags = ex.get("tags", [])
        ex_is_mcq = "mcq" in ex_tags
        if is_mcq == ex_is_mcq:
            filtered_exemplars.append(ex)

    if not filtered_exemplars:
        filtered_exemplars = exemplars

    # Score each exemplar by tag overlap
    scored = []
    for ex in filtered_exemplars:
        ex_tags = set(ex.get("tags", []))
        overlap = len(input_tags & ex_tags)
        # Bonus for pattern_type match
        if ex.get("pattern_type") in ("missing_condition",) and "missing_condition" in input_tags:
            overlap += 2
        if ex.get("pattern_type") in ("negated_fact_blocks",) and "negation" in input_tags:
            overlap += 2
        if ex.get("pattern_type") in ("eligibility_vs_actuality",) and "eligibility_vs_actuality" in input_tags:
            overlap += 2
        scored.append((overlap, ex))

    # Sort by overlap score descending, take top-k
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [ex for _, ex in scored[:k]]

    logger.debug(
        f"[Z3_RAG] Selected {len(selected)} exemplars: "
        f"{[e.get('pattern_type') for e in selected]}"
    )
    return selected


def format_exemplars_for_prompt(exemplars: List[Dict]) -> str:
    """
    Format selected exemplars into a string suitable for injection into
    the Z3 code generation prompt.
    """
    if not exemplars:
        return ""

    parts = []
    for i, ex in enumerate(exemplars, 1):
        premises_text = "\n".join(
            f"  {j+1}. {p}" for j, p in enumerate(ex.get("premises_nl", []))
        )
        parts.append(
            f"EXAMPLE {i} ({ex.get('description', '')}):\n"
            f"Premises:\n{premises_text}\n"
            f"Question: {ex.get('question', '')}\n"
            f"Expected answer: {ex.get('expected_answer', '')}\n"
            f"```python\n{ex.get('z3_code', '')}\n```\n"
        )

    return "--- Z3 CODE EXAMPLES ---\n" + "\n".join(parts) + "--- END EXAMPLES ---\n\n"

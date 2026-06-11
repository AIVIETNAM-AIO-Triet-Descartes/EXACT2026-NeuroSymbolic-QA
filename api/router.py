from typing import Literal
import re

PHYSICS_KEYWORDS = {
    "calculate", "resistance", "voltage", "current",
    "capacitor", "circuit", "power", "energy", "charge",
    "ohm", "ampere", "farad", "watt", "coulomb",
    "electric", "parallel", "series", "kirchhoff"
}


def _extract_words(text: str) -> set[str]:
    """Tokenize words and add a light singular form for plural nouns."""
    raw_words = re.findall(r"[a-zA-Z]+", text.lower())
    words = set(raw_words)
    for word in raw_words:
        if word.endswith("s") and len(word) > 3:
            words.add(word[:-1])
    return words


def classify_query(question: str, premises: list[str]) -> Literal["type1", "type2"]:
    """
    Classify query as Type 1 (logic) or Type 2 (physics).
    - If premises are provided → Type 1
    - If physics keywords in question → Type 2
    - Default fallback → Type 1
    """
    if premises:
        return "type1"
    words = _extract_words(question)
    if PHYSICS_KEYWORDS & words:
        return "type2"
    return "type1"

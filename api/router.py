from typing import Literal

PHYSICS_KEYWORDS = {
    "calculate", "resistance", "voltage", "current",
    "capacitor", "circuit", "power", "energy", "charge",
    "ohm", "ampere", "farad", "watt", "coulomb",
    "electric", "parallel", "series", "kirchhoff"
}


def classify_query(question: str, premises: list[str]) -> Literal["type1", "type2"]:
    """
    Classify query as Type 1 (logic) or Type 2 (physics).
    - If premises are provided → Type 1
    - If physics keywords in question → Type 2
    - Default fallback → Type 1
    """
    if premises:
        return "type1"
    words = set(question.lower().split())
    if PHYSICS_KEYWORDS & words:
        return "type2"
    return "type1"

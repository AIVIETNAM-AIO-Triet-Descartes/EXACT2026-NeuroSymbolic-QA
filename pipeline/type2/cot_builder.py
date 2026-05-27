"""
pipeline/type2/cot_builder.py

LangGraph node [6c]: Format solver steps into structured CoT list.
Pure string formatting — no LLM call, no failure mode.
"""


def build_cot(sympy_result: dict, parsed_physics: dict) -> list[str]:
    """
    Format sympy_result["steps"] into numbered CoT steps for API response.
    Falls back to minimal CoT from parsed_physics when steps is empty.
    """
    steps = sympy_result.get("steps", [])

    if steps:
        return [f"Step {i + 1} — {s}" for i, s in enumerate(steps)]

    # Fallback: build minimal CoT from parsed_physics
    given = parsed_physics.get("given", {})
    find = parsed_physics.get("find", "")
    cot: list[str] = []

    if given:
        given_str = ", ".join(f"{k}={v}" for k, v in given.items())
        cot.append(f"Step 1 — Identify known quantities: {given_str}")

    if find:
        cot.append(f"Step 2 — Find: {find}")

    cot.append("Step 3 — Unable to complete calculation — see explanation")
    return cot


def cot_builder_node(state: dict) -> dict:
    """Node 6c: Build CoT steps from solver output."""
    sympy_result = state.get("sympy_result", {})
    parsed = state.get("parsed_physics", {})
    cot = build_cot(sympy_result, parsed)
    return {**state, "cot": cot}

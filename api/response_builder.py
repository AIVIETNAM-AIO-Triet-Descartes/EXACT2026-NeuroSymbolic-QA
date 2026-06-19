from typing import Optional, List, Literal
from api.schemas import UnifiedResponse, ReasoningBlock


def build_response(
    query_id: str,
    query_type: Literal["type1", "type2"],
    answer: str,
    explanation: str,
    raw_unit: str = "",
    steps: Optional[List[str]] = None,
    premises_used: Optional[List[int]] = None,
    logs: Optional[List[str]] = None
) -> UnifiedResponse:
    """
    Formats and packages the pipeline outputs into the official EXACT 2026 UnifiedResponse schema.
    This also handles ASCII-fying unit strings.
    """
    # 1. ASCII-fy the unit (supports Greek small letter mu 'μ' and micro sign 'µ')
    unit_ascii = ""
    if raw_unit:
        unit_ascii = (
            raw_unit.replace("Ω", "ohm")
            .replace("μ", "u")
            .replace("µ", "u")
            .replace("°", "degree")
        )

    # 2. Build reasoning block if steps exist
    reasoning = None
    if steps:
        reasoning_type = "fol" if query_type == "type1" else "cot"
        reasoning = ReasoningBlock(type=reasoning_type, steps=steps)

    return UnifiedResponse(
        query_id=query_id,
        answer=str(answer),
        unit=unit_ascii,
        explanation=explanation or f"The answer is {answer}.",
        premises_used=premises_used or [],
        reasoning=reasoning,
        logs=logs
    )


if __name__ == "__main__":
    print("=================== BẮT ĐẦU KIỂM THỬ RESPONSE BUILDER ===================")

    # Test Case 1: Type 1 (Logic)
    res_type1 = build_response(
        query_id="T1_123",
        query_type="type1",
        answer="A",
        explanation="Logical proof path.",
        steps=["∀x (A(x) -> B(x))", "A(socrates)", "∴ B(socrates)"],
        premises_used=[0, 1]
    )
    assert res_type1.query_id == "T1_123"
    assert res_type1.answer == "A"
    assert res_type1.unit == ""
    assert res_type1.premises_used == [0, 1]
    assert res_type1.reasoning is not None
    assert res_type1.reasoning.type == "fol"
    assert len(res_type1.reasoning.steps) == 3
    print("✅ Test `build_response` với Type 1: PASS")

    # Test Case 2: Type 2 (Physics)
    res_type2 = build_response(
        query_id="T2_123",
        query_type="type2",
        answer="0.045",
        explanation="Calculated using energy formula.",
        raw_unit="μF",
        steps=["E = 0.5 * C * U^2", "E = 0.045"],
        premises_used=[]
    )
    assert res_type2.query_id == "T2_123"
    assert res_type2.answer == "0.045"
    assert res_type2.unit == "uF"  # ASCII-fied
    assert res_type2.premises_used == []
    assert res_type2.reasoning is not None
    assert res_type2.reasoning.type == "cot"
    print("✅ Test `build_response` với Type 2: PASS")

    print("\n========================= KẾT THÚC KIỂM THỬ =========================")

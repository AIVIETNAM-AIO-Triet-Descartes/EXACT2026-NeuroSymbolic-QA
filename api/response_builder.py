
# =============================================================================
# api/response_builder.py
# Owner: Người 5 — Response Builder
# Phụ thuộc: api/schemas.py (QueryResponse) — đã có sẵn, không cần chờ Người 1
# =============================================================================
# Schemas đã được mock sẵn bên dưới để Người 5 làm việc độc lập.
# Khi Người 1 hoàn thiện schemas.py thật, chỉ cần xóa phần MOCK SCHEMAS
# và bỏ comment dòng import thật.
# =============================================================================

# --- Import thật (dùng khi Người 1 xong) ---
# from api.schemas import QueryResponse

# --- Import hàm từ pipeline để xử lý FLAG C ---
from pipeline.type2.units import ascii_unit

# --- MOCK SCHEMAS — Người 5 dùng tạm, không cần chờ Người 1 ---
from typing import Optional, List
from pydantic import BaseModel, Field
from pipeline.state import SolverResult



def build_response(
    query_id: str,
    query_type: Literal["type1", "type2"],
    answer: str,
    explanation: str,
    raw_unit: str = "",
    steps: Optional[List[str]] = None,
    premises_used: Optional[List[int]] = None
) -> UnifiedResponse:
    """
    Formats and packages the pipeline outputs into the official EXACT 2026 UnifiedResponse schema.
    This also handles ASCII-fying unit strings.
    """

    answer: str = Field(..., description="Đáp án cuối cùng của hệ thống")
    explanation: str = Field(..., description="Lời giải thích đi kèm cho đáp án")
    fol: Optional[str] = Field(None, description="Công thức FOL tương ứng dạng chuỗi (Type 1)")
    cot: Optional[List[str]] = Field(None, description="Các bước suy luận Chain-of-Thought (Type 2)")
    premises: Optional[List[str]] = Field(None, description="Danh sách tiền đề chứng minh")
    confidence: Optional[float] = Field(None, description="Độ tin cậy từ 0.0 đến 1.0")
    unit: Optional[str] = Field(None, description="Đơn vị vật lý đã được ASCII hóa (FLAG C)")

    # 2. Build reasoning block if steps exist
    reasoning = None
    if steps:
        reasoning_type = "fol" if query_type == "type1" else "cot"
        reasoning = ReasoningBlock(type=reasoning_type, steps=steps)




def build_response(solver_result: SolverResult, explanation: str) -> QueryResponse:
    """
    Đóng gói SolverResult nội bộ của pipeline + văn bản giải thích thành QueryResponse API.
    """
    answer = solver_result.get("answer", "Error")
    confidence = solver_result.get("confidence", 0.5)
    source = solver_result.get("source")
    
    # Logic 1: fol = ", ".join(solver_result["fol"]) nếu có, else None
    fol_str = None
    if source == "z3" and solver_result.get("fol"):
        fol_str = ", ".join(solver_result["fol"])
        
    # Logic 2: cot = solver_result["steps"] nếu source là "sympy", else None
    cot_steps = None
    if source == "sympy":
        cot_steps = solver_result.get("steps")

    raw_unit = solver_result.get("unit")
    ascii_unit_str = ascii_unit(raw_unit) if raw_unit else None

    # Explanation luôn được truyền thẳng, không để rỗng theo đúng Spec
    return QueryResponse(
        answer=answer,
        explanation=explanation if explanation else "[No explanation provided]",
        fol=fol_str,
        cot=cot_steps,
        premises=solver_result.get("fol") if source == "z3" else None,
        confidence=confidence,
        unit=ascii_unit_str

    )


if __name__ == "__main__":
    print("=================== BẮT ĐẦU KIỂM THỬ RESPONSE BUILDER ===================")


    import sys
    from types import ModuleType

    if 'pipeline.type2.units' not in sys.modules:
        mock_units_module = ModuleType('pipeline.type2.units')
        def mock_ascii_unit(unit):
            mapping = {"Ω": "ohm", "µF": "uF"}
            return mapping.get(unit, unit)
        mock_units_module.ascii_unit = mock_ascii_unit
        sys.modules['pipeline.type2.units'] = mock_units_module
        globals()["ascii_unit"] = mock_ascii_unit

    mock_type1 = SolverResult(
        answer="A", unit=None,
        steps=["∀x (A(x) → B(x))", "A(socrates)", "∴ B(socrates)"],
        fol=["∀x (A(x) → B(x))", "A(socrates)"],
        source="z3", confidence=1.0,
    )
    
    mock_type2 = SolverResult(
        answer="10", unit="Ω",  # Thử nghiệm đơn vị Unicode Ω
        steps=["R = U / I", "R = 20 / 2", "R = 10"],
        fol=None, source="sympy", confidence=1.0,

    )
    assert res_type2.query_id == "T2_123"
    assert res_type2.answer == "0.045"
    assert res_type2.unit == "uF"  # ASCII-fied
    assert res_type2.premises_used == []
    assert res_type2.reasoning is not None
    assert res_type2.reasoning.type == "cot"
    print("✅ Test `build_response` với Type 2: PASS")

    # Chạy thử Nghiệm thu Case 1 (Type 1 - Logic)
    response = build_response(mock_type1, "The conclusion follows from premise 1 and 2.")
    assert response.answer == "A"
    assert response.explanation != ""
    assert response.fol == "∀x (A(x) → B(x)), A(socrates)"
    assert response.cot is None
    assert response.unit is None
    print(" Test `build_response` với Mock Type 1: PASS")


    # Chạy thử Nghiệm thu Case 2 (Type 2 - Physics)
    response_p2 = build_response(mock_type2, "Calculated using Ohm's law.")
    assert response_p2.answer == "10"
    assert response_p2.explanation != ""
    assert response_p2.fol is None
    assert response_p2.cot == ["R = U / I", "R = 20 / 2", "R = 10"]
    assert response_p2.unit == "ohm"  # Kiểm tra đã convert Ω -> ohm thành công
    print(" Test `build_response` với Mock Type 2 (FLAG C): PASS")
    

    print("\n========================= KẾT THÚC KIỂM THỬ =========================")

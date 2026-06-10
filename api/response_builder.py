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

# --- MOCK SCHEMAS — Người 5 dùng tạm, không cần chờ Người 1 ---
from typing import Optional, List
from pydantic import BaseModel, Field
from pipeline.state import SolverResult


class QueryResponse(BaseModel):
    """
    Mock của QueryResponse — khớp với SYSTEM.md §6 API Schema.
    Người 1 sẽ định nghĩa bản chính thức trong api/schemas.py.
    """
    answer: str = Field(..., description="Đáp án cuối cùng của hệ thống")
    explanation: str = Field(..., description="Lời giải thích đi kèm cho đáp án")
    fol: Optional[str] = Field(None, description="Công thức FOL tương ứng dạng chuỗi (Type 1)")
    cot: Optional[List[str]] = Field(None, description="Các bước suy luận Chain-of-Thought (Type 2)")
    premises: Optional[List[str]] = Field(None, description="Danh sách tiền đề chứng minh")
    confidence: Optional[float] = Field(None, description="Độ tin cậy từ 0.0 đến 1.0")


# --- END MOCK SCHEMAS ---


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

    # Explanation luôn được truyền thẳng, không để rỗng theo đúng Spec
    return QueryResponse(
        answer=answer,
        explanation=explanation if explanation else "[No explanation provided]",
        fol=fol_str,
        cot=cot_steps,
        premises=solver_result.get("fol") if source == "z3" else None,
        confidence=confidence
    )

if __name__ == "__main__":
    print("=================== BẮT ĐẦU KIỂM THỬ RESPONSE BUILDER ===================")

    mock_type1 = SolverResult(
        answer="A", unit=None,
        steps=["∀x (A(x) → B(x))", "A(socrates)", "∴ B(socrates)"],
        fol=["∀x (A(x) → B(x))", "A(socrates)"],
        source="z3", confidence=1.0,
    )
    
    mock_type2 = SolverResult(
        answer="0.045", unit="J",
        steps=["E = 0.5 * C * U^2", "E = 0.5 * 100e-6 * 30^2", "E = 0.045"],
        fol=None, source="sympy", confidence=1.0,
    )

    # Chạy thử Nghiệm thu Case 1 (Type 1 - Logic)
    response = build_response(mock_type1, "The conclusion follows from premise 1 and 2.")
    assert response.answer == "A"
    assert response.explanation != ""
    assert response.fol == "∀x (A(x) → B(x)), A(socrates)"  # Kiểm tra chuỗi đã được gộp phẳng
    assert response.cot is None
    print("✅ Test `build_response` với Mock Type 1: PASS")

    # Chạy thử Nghiệm thu Case 2 (Type 2 - Physics)
    response_p2 = build_response(mock_type2, "Calculated using energy formula.")
    assert response_p2.answer == "0.045"
    assert response_p2.explanation != ""
    assert response_p2.fol is None
    assert response_p2.cot == ["E = 0.5 * C * U^2", "E = 0.5 * 100e-6 * 30^2", "E = 0.045"]  # Kiểm tra nạp mảng steps thành công
    print("✅ Test `build_response` với Mock Type 2: PASS")
    
    print("\n========================= KẾT THÚC KIỂM THỬ =========================")

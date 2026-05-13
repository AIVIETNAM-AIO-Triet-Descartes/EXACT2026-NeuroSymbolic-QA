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
from pydantic import BaseModel
from typing import Optional


class QueryResponse(BaseModel):
    """
    Mock của QueryResponse — khớp với SYSTEM.md §6 API Schema.
    Người 1 sẽ định nghĩa bản chính thức trong api/schemas.py.
    """
    answer: str                          # Bắt buộc — letter (A/B/C/D) hoặc số
    explanation: str                     # Bắt buộc — giải thích NL
    fol: Optional[str] = None            # Optional — chỉ Type 1
    cot: Optional[list[str]] = None      # Optional — chủ yếu Type 2
    premises: Optional[list[str]] = None # Optional
    confidence: Optional[float] = None   # Optional — float 0.0–1.0


# --- END MOCK SCHEMAS ---


from pipeline.state import SolverResult  # noqa: E402


def build_response(
    solver_result: SolverResult,
    explanation: str,
) -> QueryResponse:
    """
    Đóng gói kết quả cuối thành QueryResponse.

    Đây là điểm hội tụ cuối cùng của pipeline — luôn trả về
    object hợp lệ, không bao giờ thiếu `answer` hoặc `explanation`.

    Args:
        solver_result: Kết quả từ Z3 hoặc SymPy (hoặc llm_fallback).
        explanation:   Chuỗi giải thích từ Explainer Agent.

    Returns:
        QueryResponse đúng API schema.
    """
    # TODO: implement — đóng gói solver_result + explanation thành QueryResponse
    # Gợi ý:
    #   - answer      = solver_result["answer"]
    #   - confidence  = solver_result["confidence"]
    #   - fol         = ", ".join(solver_result["fol"]) nếu solver_result["fol"] else None
    #   - cot         = solver_result["steps"] nếu source là "sympy"
    #   - explanation luôn được truyền thẳng vào, không được để rỗng
    raise NotImplementedError("build_response chưa được implement")

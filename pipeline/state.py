"""
pipeline/state.py

Single source of truth cho các data structure được chia sẻ giữa các node trong pipeline.

Tham khảo: docs/SYSTEM.md §3 (State Schema) và docs/DEMO_PLAN.md (File Interface Chung).
"""

from typing import Literal, Optional, TypedDict


class SolverResult(TypedDict):
    """
    Interface trung gian thống nhất giữa Solver (Z3 / SymPy) và Explainer Agent.

    Mục đích: Explainer Agent (bước 7) không cần biết kết quả đến từ track nào —
    cả Z3 lẫn SymPy đều phải populate struct này trước khi truyền xuống.

    Dev Rule #9: Mọi Solver đều phải trả về SolverResult trước khi truyền cho
    Explainer Agent — không truyền raw dict tùy tiện.
    """

    answer: str
    """Đáp án cuối — letter (A/B/C/D) cho Type 1, hoặc số cho Type 2."""

    unit: Optional[str]
    """Đơn vị vật lý — chỉ có ở Type 2. Ví dụ: "mJ", "Ω", "V". None cho Type 1."""

    steps: list[str]
    """
    Các bước lập luận/tính toán:
    - Type 1 (Z3): proof_steps — các bước chứng minh logic
    - Type 2 (SymPy): computation steps — các bước tính toán số học
    """

    fol: Optional[list[str]]
    """FOL (First-Order Logic) đã được validate — chỉ có ở Type 1. None cho Type 2."""

    source: Literal["z3", "sympy", "vector_solver", "resonance", "error_calc",
                    "llm_cot", "llm_fallback"]
    """
    Nguồn tạo ra kết quả — dùng để log và set confidence:
    - "z3"            → symbolic proof, confidence = 1.0
    - "sympy"         → symbolic computation, confidence = 1.0
    - "vector_solver" → Coulomb/E-field vector geometry (Type 2), confidence = 1.0
    - "resonance"     → CHLT Yes/No resonance check (deterministic), confidence = 1.0
    - "error_calc"    → THCB measurement-error computation (deterministic), confidence = 1.0
    - "llm_cot"       → LLM CoT fallback parse thành công, confidence = 0.5–0.6
    - "llm_fallback"  → LLM tự suy luận, confidence = 0.6 (RAG+LLM) hoặc 0.5 (LLM only)
    """

    confidence: float
    """
    Độ tin cậy của kết quả:
    - 1.0 → symbolic solver thành công (Z3 hoặc SymPy)
    - 0.6 → RAG + LLM reasoning fallback
    - 0.5 → LLM only fallback
    - 0.4 → SymPy solve thành công nhưng self-verification thất bại
    - 0.3 → LLM generation error, answer = "Unable to determine"
    """

    premises_used: Optional[list[int]]
    """
    Index (0-based) các premises đã dùng để chứng minh — Type 1 (chấm 50% điểm).
    - Track 1 (Z3/Logic Tree): list int, ví dụ [0, 2] (map từ proof trace / unsat core).
    - Track 2 (SymPy/vector): không áp dụng → None. build_response tự bọc None→[].
    Khai Optional để Track 2 (không set key này) vẫn hợp lệ TypedDict.
    """


class PipelineState(TypedDict):
    """
    Shared state chạy xuyên suốt toàn bộ pipeline (LangGraph StateGraph).

    Mỗi node đọc những field nó cần và cập nhật phần của mình.
    Tham khảo: docs/SYSTEM.md §3 và LangGraph Graph Definition §7.

    Usage:
        from pipeline.state import PipelineState
        workflow = StateGraph(PipelineState)
    """

    # -------------------------------------------------------------------------
    # Input — được populate bởi API Gateway (bước 1)
    # -------------------------------------------------------------------------

    question: str
    """Câu hỏi gốc từ request (bắt buộc)."""

    query_id: str
    """Mã định danh câu hỏi (bắt buộc)."""

    options: list[str]
    """Các lựa chọn trắc nghiệm (cho Type 1, nếu có)."""

    premises: list[str]
    """
    Danh sách tiền đề ngôn ngữ tự nhiên (Natural Language).
    - Type 1: có ít nhất 1 phần tử
    - Type 2: list rỗng []
    """

    query_type: str
    """
    Loại câu hỏi, được xác định bởi Router Agent (bước 2).
    Giá trị: "type1" | "type2"
    """

    # -------------------------------------------------------------------------
    # Track 1: Logic (Educational QA) — Z3 Symbolic Reasoning
    # Các node liên quan: Text Parser (3a) → Logic Evaluator (4a) → Z3 Solver (5a)
    # -------------------------------------------------------------------------

    fol_translation: Optional[list[str]]
    """
    Danh sách mệnh đề FOL (First-Order Logic) được dịch từ premises-NL.
    Được populate bởi Text Parser Agent (bước 3a).
    None nếu chưa được dịch hoặc đang ở Track 2.
    """

    fol_valid: Optional[bool]
    """
    Kết quả kiểm tra cú pháp FOL từ Logic Evaluator (bước 4a).
    - True  → FOL hợp lệ, tiếp tục sang Z3 Solver
    - False → FOL lỗi, loop lại Text Parser (tối đa fol_retries = 3 lần)
    - None  → chưa được validate
    """

    z3_result: Optional[dict]
    """
    Kết quả raw từ Z3 Solver (bước 5a).
    Schema: { "answer": str, "supporting_premises": list[str], "proof_steps": list[str] }
    None nếu chưa chạy hoặc đang ở Track 2.
    """

    # -------------------------------------------------------------------------
    # Track 2: Physics (Computation) — SymPy Symbolic Computation
    # Các node liên quan: Physics Parser (3b) → Formula RAG (4b) → SymPy Solver (5b)
    #                     → Self-Verifier (6b) → CoT Builder (6c)
    # -------------------------------------------------------------------------

    parsed_physics: Optional[dict]
    """
    Kết quả trích xuất từ Physics Parser Agent (bước 3b).
    Schema: { "given": dict, "find": str, "domain": str, "formulas": list[str] }
    None nếu chưa chạy hoặc đang ở Track 1.
    """

    sympy_result: Optional[dict]
    """
    Kết quả raw từ SymPy Solver (bước 5b).
    Schema: { "answer": str|float, "unit": str, "steps": list[str] }
    None nếu chưa chạy hoặc đang ở Track 1.
    """

    cot: Optional[list[str]]
    """
    Chain-of-Thought steps được xây dựng bởi CoT Builder (bước 6c).
    Mỗi phần tử là một bước lập luận dạng text tự nhiên.
    None nếu chưa build hoặc đang ở Track 1.
    """

    # -------------------------------------------------------------------------
    # Shared — kết quả cuối, được populate bởi Response Builder (bước 8)
    # -------------------------------------------------------------------------

    answer: Optional[str]
    """
    Đáp án cuối cùng sẽ trả về API response (bắt buộc trong response).
    Được set bởi Response Builder từ solver_result.answer.
    """

    explanation: Optional[str]
    """
    Giải thích bằng ngôn ngữ tự nhiên (bắt buộc trong response).
    Được generate bởi Explainer Agent (bước 7).
    """

    confidence: Optional[float]
    """
    Độ tin cậy tổng hợp của toàn bộ pipeline.
    Được kế thừa từ solver_result.confidence và có thể bị giảm bởi Self-Verifier.
    """

    # -------------------------------------------------------------------------
    # Critical fields — quan trọng cho flow control của LangGraph
    # -------------------------------------------------------------------------

    solver_result: Optional[SolverResult]
    """
    Interface trung gian thống nhất — unified interface cho Explainer Agent.
    Được set bởi Z3 Solver (Track 1) hoặc SymPy Solver (Track 2) sau khi hoàn thành.
    Explainer Agent chỉ đọc field này, không đọc z3_result hay sympy_result trực tiếp.
    """

    fol_retries: int
    """
    Số lần đã retry vòng lặp Text Parser → Logic Evaluator (bước 3a ↔ 4a).
    LangGraph dùng field này để quyết định conditional edge:
    - fol_retries < 3 → "retry" → quay lại Text Parser
    - fol_retries >= 3 → "fallback" → bỏ qua Z3, chuyển thẳng sang Explainer
    Khởi tạo = 0 tại API Gateway.
    """

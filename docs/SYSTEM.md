# 🧠 SYSTEM — Kiến trúc hệ thống EXACT 2026 NeuroSymbolic-QA

> **Single Source of Truth (SSOT)** — Tài liệu thống nhất mô tả toàn bộ pipeline, vai trò từng thư viện/tech stack, và các tài liệu nghiên cứu tham khảo.
> Được tổng hợp từ `APPROACHES.md`, `PIPELINE.md`, và `RESEARCH.md`.

---

## 1. Tổng quan hệ thống

**Triết lý cốt lõi:** "Không để LLM tự làm toán. LLM chỉ làm nhiệm vụ giao tiếp và dịch thuật, phần tính toán và suy luận logic giao cho các công cụ toán học chuyên dụng."

**Kiến trúc:** Multi-Agent Pipeline dạng **State Graph** kết hợp **Symbolic Reasoning**, sử dụng mẫu thiết kế Hybrid (Routing + Sequential + Evaluator-Optimizer).

**Ràng buộc quan trọng:**
- LLM phải chạy **nội bộ (local)**, kích thước ≤ 8B — cấm gọi API bên ngoài (OpenAI, Anthropic, Google)
- Dataset Type 1: `question` + `premises-NL` (text only)
- Dataset Type 2: `question` only (bài toán vật lý dạng text, không có ảnh)
- API Response bắt buộc phải có: `answer`, `explanation`
- API Response **không** có field `idx`

---

## 2. Pipeline đầy đủ: Từ Input đến Output

```
                        ┌─────────────────────────────┐
                        │      HTTP Request (JSON)    │
                        │  { question, premises? [] } │
                        └──────────────┬──────────────┘
                                       │
                                       ▼
                        ┌─────────────────────────────┐
                   1    │     API GATEWAY (FastAPI)   │
                        │     Nhận JSON, validate     │
                        └──────────────┬──────────────┘
                                       │
                                       ▼
                        ┌─────────────────────────────┐
                   2    │     ROUTER AGENT            │
                        │     (Pattern: Routing)      │
                        │  premises có? → Type 1      │
                        │  premises rỗng?             │
                        │  + physics keywords? → Type2│
                        │  default fallback → Type 1  │
                        └──────┬──────────────┬───────┘
                               │              │
                ┌──────────────┘              └──────────────┐
                │                                            │
                ▼                                            ▼
   ┌────────────────────────┐               ┌────────────────────────────┐
   │   TRACK 1: LOGIC       │               │   TRACK 2: PHYSICS         │
   │   (Educational QA)     │               │   (Computation)            │
   └────────┬───────────────┘               └────────┬───────────────────┘
            │                                        │
            ▼                                        ▼
   ┌────────────────────────┐               ┌────────────────────────────┐
3a │ TEXT PARSER AGENT      │          3b   │ PHYSICS PARSER AGENT       │
   │ (LLM ≤ 8B)             │               │ (LLM ≤ 8B)                 │
   │ NL premises → FOL      │               │ Trích xuất biến số,        │
   └────────┬───────────────┘               │ xác định domain & formula  │
            │                               └────────┬───────────────────┘
            ▼                                        │
   ┌────────────────────────┐                        │
4a │ LOGIC EVALUATOR NODE   │                        │
   │ Kiểm tra cú pháp FOL   │                        │
   │ Nếu lỗi → Loop về 3a   │                        ▼
   │   (tối đa 3 lần)       │               ┌────────────────────────────┐
   │ Nếu đúng → tiếp tục ↓  │          4b   │ FORMULA RAG / EXPERT NODE  │
   └────────┬───────────────┘               │ Truy xuất công thức phù    │
            │                               │ hợp từ Vector DB (FAISS)   │
            ▼                               └────────┬───────────────────┘
   ┌────────────────────────┐                        │
5a │ Z3 SOLVER NODE         │                        ▼
   │ Chứng minh/bác bỏ      │               ┌────────────────────────────┐
   │ từng answer option     │          5b   │ SYMPY SOLVER NODE          │
   │ → answer + proof_steps │               │ Giải phương trình, tính    │
   └────────┬───────────────┘               │ toán chính xác tuyệt đối   │
            │                               │ → answer + steps           │
            │                               └────────┬───────────────────┘
            │                                        │
            │                                        ▼
            │                               ┌────────────────────────────┐
            │                          6b   │ COT BUILDER                │
            │                               │ Xây dựng Chain-of-Thought  │
            │                               │ từ các bước giải SymPy     │
            │                               └────────┬───────────────────┘
            │                                        │
            └──────────────┬─────────────────────────┘
                           │
                           ▼
                ┌─────────────────────────────┐
           7    │    EXPLAINER AGENT          │
                │    (LLM ≤ 8B)               │
                │    Nhận kết quả từ Solver   │
                │    → Viết giải thích NL     │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
           8    │    RESPONSE BUILDER         │
                │    Đóng gói JSON response   │
                │    theo API Schema          │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │      HTTP Response (JSON)   │
                │  { answer, explanation,     │
                │    fol?, cot?, premises?,   │
                │    confidence? }            │
                └─────────────────────────────┘
```

**Router logic (chi tiết):**
```python
PHYSICS_KEYWORDS = {
    "calculate", "resistance", "voltage", "current",
    "capacitor", "circuit", "power", "energy", "charge",
    "ohm", "ampere", "farad", "watt", "coulomb",
    "electric", "parallel", "series", "kirchhoff"
}

def classify_query(question: str, premises: list[str]) -> Literal["type1", "type2"]:
    if premises:                                      # Có premises → Type 1
        return "type1"
    words = set(question.lower().split())
    if PHYSICS_KEYWORDS & words:                      # Keyword match → Type 2
        return "type2"
    return "type1"                                    # Default fallback
```

### Chi tiết từng bước

| Bước | Tên Node | Input | Output | Fallback |
|------|----------|-------|--------|----------|
| 1 | API Gateway | HTTP Request JSON | Validated `QueryRequest` | Trả HTTP 422 nếu sai schema |
| 2 | Router Agent | `question`, `premises` | `query_type`: "type1" / "type2" | Default → type1 nếu không xác định |
| 3a | Text Parser Agent | `premises-NL` (list[str]) | FOL list (list[str]) | Dùng `premises-NL` thô làm context |
| 3b | Physics Parser Agent | `question` (str) | `{given, find, domain, formulas}` | LLM tự suy luận với CoT prompt |
| 4a | Logic Evaluator | FOL list | FOL đã validate | Loop về 3a (max 3 lần), rồi fallback RAG |
| 4b | Formula RAG | `domain`, `formulas` | Công thức chính xác từ Vector DB | Dùng công thức LLM đề xuất |
| 5a | Z3 Solver | FOL validated + options | `{answer, supporting_premises, proof_steps}` | RAG + LLM reasoning (timeout > 5s) |
| 5b | SymPy Solver | `{given, find, formulas}` | `{answer, unit, steps}` | LLM tự tính + confidence = 0.5 |
| 6b | CoT Builder | `parsed` + `solver_steps` | `cot: list[str]` | — |
| 7 | Explainer Agent | Kết quả solver + question gốc | `explanation: str` | Retry 1 lần với simplified prompt |
| 8 | Response Builder | Tất cả kết quả | JSON theo API schema | Luôn đảm bảo có `answer` + `explanation` |

> **⚠️ TODO — Vector DB source:** Ban tổ chức sẽ công bố source materials của Type 2 tại kick-off workshop (09/05). Sau khi nhận, populate FAISS index từ các tài liệu đó. Trong thời gian chờ, dùng công thức vật lý cơ bản (Ohm's law, KVL, KCL, công thức tụ điện...) làm seed data.
---

## 3. State Schema — Dữ liệu chia sẻ giữa các Node

Toàn bộ pipeline hoạt động trên một **State chung** (shared state). Mỗi Node đọc những gì nó cần và cập nhật phần của mình:

```python
from typing import TypedDict, Optional

class PipelineState(TypedDict):
    # Input (từ API Gateway)
    question: str
    premises: list[str]                  # rỗng nếu Type 2
    query_type: str                      # "type1" | "type2"

    # Track 1: Logic
    fol_translation: Optional[list[str]] # FOL từ Text Parser
    fol_valid: Optional[bool]            # Kết quả validate
    z3_result: Optional[dict]            # {answer, supporting_premises, proof_steps}

    # Track 2: Physics
    parsed_physics: Optional[dict]       # {given, find, domain, formulas}
    sympy_result: Optional[dict]         # {answer, unit, steps}
    cot: Optional[list[str]]             # Chain-of-Thought steps

    # Shared (kết quả cuối)
    answer: Optional[str]
    explanation: Optional[str]
    confidence: Optional[float]
```

### Interface trung gian — SolverResult

Để Explainer Agent (7) không cần biết kết quả đến từ track nào, cả Z3 và SymPy đều phải trả về cùng một struct trước khi truyền xuống:

```python
from typing import TypedDict, Optional, Literal

class SolverResult(TypedDict):
    answer: str                          # Đáp án cuối (letter hoặc số)
    unit: Optional[str]                  # Đơn vị — chỉ Type 2 (vd: "mJ", "Ω")
    steps: list[str]                     # proof_steps (Z3) hoặc sympy steps
    fol: Optional[list[str]]             # FOL validated — chỉ Type 1
    source: Literal["z3", "sympy", "llm_fallback"]  # Để log và set confidence
    confidence: float                    # 1.0 (symbolic) | 0.6 (rag+llm) | 0.5 (llm only)
```

Explainer Agent nhận `SolverResult` và sinh `explanation` mà không cần if/else theo track.

---

## 4. Tech Stack — Vai trò từng thư viện

### 4.1. Orchestration & API

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **FastAPI** | Web framework xử lý HTTP request/response, validate input với Pydantic | 1 API Gateway |
| **Uvicorn** | ASGI server chạy FastAPI với hiệu năng cao | 1 API Gateway |
| **LangGraph** *(khuyến nghị)* | Framework orchestration dạng State Graph — quản lý luồng Node, conditional edges (rẽ nhánh), và vòng lặp (retry loop) | Toàn bộ pipeline (2→8) |
| **Pydantic** | Định nghĩa và validate schema cho Request/Response | 1, 8 |

### 4.2. LLM Inference

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **Transformers** (HuggingFace) | Load và chạy model LLM ≤ 8B (Qwen2.5-7B, LLaMA-3.1-8B) | 3a, 3b, 7 |
| **vLLM** | Inference engine tốc độ cao, hỗ trợ continuous batching — đảm bảo throughput ≥ 10 req/s | 3a, 3b, 7 |
| **PEFT** (Parameter-Efficient Fine-Tuning) | Hỗ trợ load adapter QLoRA nếu model đã fine-tune | 3a, 3b, 7 |
| **BitsAndBytes** | Quantization 4-bit để chạy model 7B trên GPU hạn chế VRAM | 3a, 3b, 7 |

> **Quy tắc chọn inference backend:**
> - **Local dev / macOS / CPU:** dùng `transformers` pipeline trực tiếp
> - **VPS production (Linux + GPU):** khởi động vLLM server, gọi qua `http://localhost:8001/v1`
> - Hai backend này **không chạy song song** trong cùng một process — chọn một, cấu hình qua `configs/config.yaml` (`inference_backend: "transformers" | "vllm"`)

### 4.3. Symbolic Reasoning (Cốt lõi Neuro-Symbolic)

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **Z3-Solver** | Theorem prover — chứng minh/bác bỏ logic mệnh đề dựa trên FOL. **Đây là thành phần "Symbolic" cốt lõi** đảm bảo tính deterministic và traceable cho reasoning | 4a (validate), 5a (solve) |
| **SymPy** | Thư viện tính toán symbolic — giải phương trình, đổi đơn vị, tính toán số học chính xác tuyệt đối (không bị hallucination số) | 5b |

### 4.4. RAG & Vector Database

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **FAISS** (hoặc ChromaDB) | Vector database lưu trữ embedding của các định luật/công thức vật lý. Giúp LLM nhỏ (< 8B) truy xuất đúng công thức thay vì tự "bịa" | 4b Formula RAG |
| **Sentence-Transformers** | Tạo embedding vector từ text (công thức, premises) để lưu vào FAISS | 4b Formula RAG |
| **LangChain** | Cung cấp các abstraction cho RAG chain (retriever → prompt → LLM) | 4b, Fallback flows |

### 4.5. Infrastructure & Monitoring

| Thư viện / Tool | Vai trò trong pipeline | Bước sử dụng |
|-----------------|----------------------|---------------|
| **Python logging** (JSON format) | Ghi log mỗi request: question, type, answer, confidence, có FOL/CoT hay không — phục vụ debug và demo live. Bắt buộc log thêm: fol_retries (số lần loop 4a), fallback_triggered (True/False), z3_timeout (True/False), solver_source ("z3"/"sympy"/"llm_fallback") — các field này là input cho /exact-error-analysis skill | Toàn bộ pipeline |
| **YAML config** (`configs/config.yaml`) | Cấu hình mặc định của hệ thống: model name, timeout, temperature... Được commit lên Git, dùng chung cho cả team | Toàn bộ |
| **`.env`** | Cấu hình riêng từng máy (device, model path...). Ghi đè lên config.yaml. **Không** commit lên Git | Toàn bộ |

---

## 5. Fallback Strategy — Chiến lược xử lý lỗi

Mọi bước trong pipeline đều **phải có fallback** — API endpoint không bao giờ được phép crash:

```
TOTAL_REQUEST_TIMEOUT = 30s  ← Budget tổng cho toàn bộ request
├── Z3 Solver timeout:  5s   ← Nếu vượt → fallback RAG+LLM
├── SymPy timeout:     10s   ← Nếu vượt → LLM tự tính
└── LLM generation:    ~15s  ← Còn lại cho inference + explainer
```

```
┌────────────────────────┬─────────────────────────────────┬──────────────────┐
│ Bước lỗi               │ Fallback                        │ Confidence       │
├────────────────────────┼─────────────────────────────────┼──────────────────┤
│ FOL parse error        │ Loop sửa FOL (max 3 lần)        │ Giảm mỗi lần     │
│                        │ → RAG + LLM reasoning           │                  │
│                        │   với premises-NL thô           │ 0.6              │
├────────────────────────┼─────────────────────────────────┼──────────────────┤
│ Z3 timeout (> 5s)      │ RAG retrieval trên premises-NL  │                  │
│                        │ → LLM reasoning với full context│ 0.6              │
├────────────────────────┼─────────────────────────────────┼──────────────────┤
│ SymPy solve failure    │ LLM tự tính toán với CoT prompt │ 0.5              │
├────────────────────────┼─────────────────────────────────┼──────────────────┤
│ LLM generation error   │ Retry 1 lần simplified prompt   │                  │
│                        │ → answer = "Unable to determine"│ 0.3              │
└────────────────────────┴─────────────────────────────────┴──────────────────┘
```

---

## 6. API Schema

### Request
```json
POST /query
{
  "question": "string (bắt buộc)",
  "premises": ["string", "..."]    // rỗng [] nếu Type 2
}
```

### Response
```json
{
  "answer": "string (bắt buộc)",
  "explanation": "string (bắt buộc)",
  "fol": "string (optional — chỉ Type 1)",
  "cot": ["string", "..."] ,       // optional — chủ yếu Type 2
  "premises": ["string", "..."],    // optional
  "confidence": 0.95                // optional, float
}
```

### Health Check
```
GET /health  →  { "status": "ok" }
```

---

## 7. Design Patterns đang áp dụng

Hệ thống áp dụng kết hợp (Hybrid) các mẫu thiết kế Multi-Agent:

| Pattern | Nơi áp dụng | Mô tả |
|---------|-------------|--------|
| **Routing** | Router Agent (②) | Phân loại input để điều hướng đến đúng track xử lý |
| **Sequential / Chain** | Mỗi Track (③→⑤→⑦) | Các Agent xử lý tuần tự, output của bước trước là input của bước sau |
| **Evaluator-Optimizer** | Logic Evaluator (④a) ↔ Text Parser (③a) | Vòng lặp kiểm tra-sửa lỗi FOL trước khi đưa vào Z3, tối đa 3 lần |
| **Tool-use** | Z3 Solver, SymPy Solver | LLM không tự tính — gọi tool chuyên dụng để đảm bảo chính xác |

### LangGraph Graph Definition (skeleton)

```python
from langgraph.graph import StateGraph, END
from pipeline.state import PipelineState

workflow = StateGraph(PipelineState)

# Đăng ký các node
workflow.add_node("router",          router_agent)
workflow.add_node("text_parser",     text_parser_agent)
workflow.add_node("logic_evaluator", logic_evaluator_node)
workflow.add_node("z3_solver",       z3_solver_node)
workflow.add_node("physics_parser",  physics_parser_agent)
workflow.add_node("formula_rag",     formula_rag_node)
workflow.add_node("sympy_solver",    sympy_solver_node)
workflow.add_node("cot_builder",     cot_builder_node)
workflow.add_node("explainer",       explainer_agent)
workflow.add_node("response_builder",response_builder_node)

# Entry point
workflow.set_entry_point("router")

# Conditional edge: router → type1 hoặc type2
workflow.add_conditional_edges("router", route_query, {
    "type1": "text_parser",
    "type2": "physics_parser"
})

# Track 1: text_parser → logic_evaluator → (retry hoặc z3)
workflow.add_edge("text_parser", "logic_evaluator")
workflow.add_conditional_edges("logic_evaluator", check_fol_valid, {
    "retry": "text_parser",    # FOL lỗi → loop lại (max 3 lần)
    "valid": "z3_solver",      # FOL đúng → tiếp tục
    "fallback": "explainer"    # Hết retry → bỏ qua Z3
})
workflow.add_edge("z3_solver", "explainer")

# Track 2: physics_parser → formula_rag → sympy_solver → cot_builder
workflow.add_edge("physics_parser", "formula_rag")
workflow.add_edge("formula_rag",    "sympy_solver")
workflow.add_edge("sympy_solver",   "cot_builder")
workflow.add_edge("cot_builder",    "explainer")

# Shared ending
workflow.add_edge("explainer",       "response_builder")
workflow.add_edge("response_builder", END)

app = workflow.compile()
```

---

## 8. Tài liệu nghiên cứu & Học tập

### 8.1. Framework & Tutorials

| Tài liệu | Mô tả | Liên quan đến |
|-----------|--------|---------------|
| **"Multi-Agent Architectures with LangGraph"** (LangChain Docs) | Hướng dẫn cấu hình Node, Edge, Conditional Edge — phục vụ trực tiếp cho việc xây pipeline | Toàn bộ pipeline |
| **LangGraph Concepts: State & Conditional Edges** | Hiểu cách State được chia sẻ giữa các Node, cách rẽ nhánh fallback | 2, 4a |
| **CrewAI Sequential Process** | Framework thay thế nếu muốn triển khai nhanh hơn LangGraph | Toàn bộ pipeline |
| **"AI Agents in LangGraph"** — Khóa học DeepLearning.AI | Rất sát với việc xây dựng node-based pipeline | Toàn bộ pipeline |
| **"Multi AI Agent Systems with crewAI"** — Khóa học DeepLearning.AI | Tư duy phân chia Task và Role cho từng Agent | Thiết kế Agent |

### 8.2. Nghiên cứu học thuật (Neuro-Symbolic & XAI)

| Tài liệu | Mô tả | Liên quan đến |
|-----------|--------|---------------|
| **"The Landscape of Emerging AI Agent Architectures"** | Phân tích sự khác biệt giữa Single Agent, Multi-Agent, và các cách giao tiếp | Kiến trúc tổng thể |
| **LLM-Compiler** | Cách LLM lập kế hoạch (planning) để gọi các tool solver như Z3/SymPy | 5a, 5b |
| **ReAct Pattern (Reason + Act)** | Agent tự suy nghĩ trước khi hành động — quan trọng cho `explanation` và `cot` | 7 Explainer |
| **Toolformer** | Cách LLM học cách gọi external tools — nền tảng lý thuyết cho Tool-use pattern | 5a, 5b |

### 8.3. Từ khóa tìm kiếm chuyên sâu
- `LLM + Theorem Prover pipeline`
- `Neuro-Symbolic QA system architecture`
- `ReAct prompt logic solver`
- `LangGraph Multi-Agent Workflows`
- `LangGraph state machine tutorial`

---

## 9. Quy tắc phát triển (Dev Rules)

> [!CAUTION]
> Các quy tắc bắt buộc tuân thủ — vi phạm có thể dẫn đến **disqualification**:

1. **KHÔNG** gọi bất kỳ external LLM API nào (OpenAI, Anthropic, Google)
2. **KHÔNG** sử dụng field `idx` trong codebase — field này không tồn tại trong API schema
3. `answer` và `explanation` là **bắt buộc** — không bao giờ trả response thiếu 2 field này
4. Luôn wrap LLM calls trong `try/except` — API endpoint không được phép crash
5. Khi parse JSON từ LLM output, luôn dùng `json.loads()` với error handling, **không** dùng `eval()`
6. Type 2 không có premises → field `premises` trong request là list rỗng `[]`
7. Đơn vị (unit) phải đi kèm answer số học trong explanation
8. **Không chạy song song** `transformers` và `vLLM` trong cùng process — chọn một backend qua `configs/config.yaml`
9. Mọi Solver đều phải trả về `SolverResult` struct trước khi truyền cho Explainer Agent — không truyền raw dict tùy tiện
10. Mọi request phải hoàn thành trong **30 giây** — thiết lập `asyncio.timeout(30)` ở API Gateway
# EXACT 2026 — System & Competition Reference

**Mục lục (gộp từ 2 file):**
- EXACT 2026 — Project Context  *(← `CONTEXT.md`)*
- 🧠 SYSTEM — Kiến trúc hệ thống EXACT 2026 NeuroSymbolic-QA  *(← `SYSTEM.md`)*

---

## EXACT 2026 — Project Context

### Competition Overview

**Full name:** The 2nd International XAI Challenge for Transparent Educational Question-Answering  
**Host:** URA Research Group, Ho Chi Minh City University of Technology (HCMUT), Vietnam  
**Affiliated with:** IEEE IJCNN 2026 (WCCI 2026, Maastricht)  
**Website:** https://ura.hcmut.edu.vn/exact  
**Contact:** ura.hcmut@gmail.com

### Goal

Build an **educational QA system** that:
1. Produces **correct answers** to educational queries
2. Generates **natural language explanations** justifying each answer
3. Optionally provides structured reasoning evidence: FOL derivations, CoT steps, premise lists, confidence scores

The challenge promotes **Explainable AI (XAI)** — systems must not only be accurate but also transparent and verifiable.

### Hard Constraints

- **Only open-source LLMs with ≤ 8 billion parameters** are allowed (e.g. LLaMA, Mistral, Qwen, Phi)
- **Closed-source models are strictly prohibited**: GPT, Claude, Gemini, or any commercial API
- All external datasets used for fine-tuning must be fully disclosed
- Submissions that violate these rules are disqualified

### Task Description

#### Dataset Type 1 — Logic-Based Educational Queries
- **Size:** 464 records, 913 questions
- **Domain:** University regulations (grading policies, enrollment rules, scholarship criteria)
- **Question types:** Multiple Choice (MCQ), Yes/No/Uncertain, Open-ended
- **Input at inference:** `question` + `premises-NL` (natural language premises)
- **Training data also includes:** `premises-FOL`, `answers`, `explanation`
- **Key challenge:** Multi-step logical reasoning over regulation rules

**Sample record:**
```json
{
  "premises-NL": [
    "If a curriculum is well-structured and has exercises, it enhances student engagement.",
    "If a curriculum enhances student engagement and provides access to advanced resources, it enhances critical thinking.",
    "The faculty prioritizes pedagogical training and curriculum development.",
    "The curriculum has practical exercises.",
    "The curriculum provides access to advanced resources."
  ],
  "premises-FOL": [
    "ForAll(c, (well_structured(c) ∧ has_exercises(c)) → enhances_engagement(c))",
    "ForAll(c, (enhances_engagement(c) ∧ advanced_resources(c)) → enhances_critical_thinking(c))"
  ],
  "questions": [
    "Based on the premises, what can we conclude about the curriculum?\nA. It enhances student engagement but not critical thinking\nB. It enhances critical thinking\nC. It needs more resources\nD. It is well-structured but lacks exercises"
  ],
  "answers": ["B"],
  "explanation": [
    "Faculty priorities satisfy premise 3, making the curriculum well-structured. Exercises and premise 1 lead to enhanced engagement, and with advanced resources, premise 2 confirms enhanced critical thinking."
  ]
}
```

#### Dataset Type 2 — Physics Problems
- **Size:** 5,520 problems
- **Domain:** Electric circuits and electrostatics (resistance, voltage, current, power, capacitance, electric fields, energy)
- **Question types:** Numerical computation, multi-step
- **Input at inference:** `question` only (no premises given)
- **Training data also includes:** `cot` (chain-of-thought steps), `answer`, `unit`
- **Key challenge:** Requires physics domain knowledge and step-by-step numerical reasoning

**Sample record:**
```json
{
  "id": "TD401",
  "question": "Calculate the energy stored in capacitor C when C = 100 μF and U = 30 V.",
  "cot": "Step 1: Identify given values: C = 100 μF, U = 30 V.\nStep 2: Formula: E = 0.5 * C * U^2.\nStep 3: Convert: C = 1e-4 F.\nStep 4: E = 0.5 × 1e-4 × 900 = 0.045 J.",
  "answer": "45",
  "unit": "mJ"
}
```

### API Submission Format

> 🚨 **STALE** — phần mô tả API + dataset count (5520 problems, Type1 464/913) bên dưới là bản CŨ. Spec + số liệu chuẩn ở **`docs/official_spec_gaps.md`** (API `/predict`, Type2 ~1354, Type1 411/808, deadline 12/06).

Each team exposes an **HTTP API endpoint**. For every query, the endpoint must return:

```json
{
  "answer": "B",
  "explanation": "The voltage across R2 is calculated using Ohm's law...",

  "fol": "∀x (Resistor(x) → HasVoltage(x, V))",
  "cot": [
    "Step 1: Identify the circuit topology...",
    "Step 2: Apply Kirchhoff's voltage law...",
    "Step 3: Solve for the unknown voltage..."
  ],
  "premises": [
    "Ohm's law: V = IR",
    "KVL: sum of voltages in a loop = 0"
  ],
  "confidence": 0.92
}
```

| Field | Required | Notes |
|---|---|---|
| `answer` | ✅ Mandatory | Final answer string |
| `explanation` | ✅ Mandatory | Natural language justification |
| `fol` | Optional | First-Order Logic derivation |
| `cot` | Optional | Chain-of-Thought steps as list |
| `premises` | Optional | Supporting rules/laws used |
| `confidence` | Optional | Float 0–1 |

Optional fields improve **P3 (Reasoning Depth)** scores and are strongly encouraged.

### Evaluation Criteria

| Criterion | Description | Priority |
|---|---|---|
| **P1: Correctness** | Accurate final answer | Highest |
| **P2: Explanation Quality** | Clear, coherent, verifiable NL explanation | High |
| **P3: Reasoning Depth** | FOL, CoT, premises, structured proofs | Medium |

**Evaluation process:**
- **Phase 1 & 2:** Automated scoring against ground-truth + committee review of explanation quality
- **Final Round (Top 10):** Live demo on unseen queries; chairs assess answer, explanation, reasoning depth in real time
- **Final score:** Weighted combination of P1 + P2 + P3 (weights announced at kick-off)

### Timeline

| Phase | Date |
|---|---|
| Team Registration | Apr 10 – May 10, 2026 |
| Kick-off & Dataset Release | May 4, 2026 |
| Main Competition (submit API) | May 5 – May 30, 2026 |
| Phase 1 Evaluation Results | Jun 1–2, 2026 |
| Model Refinement Window | Jun 3–4, 2026 |
| Phase 2 Evaluation Results | Jun 5–7, 2026 |
| Top 10 Announcement | Jun 10, 2026 |
| Public Test Day (live demo) | Jun 15, 2026 |
| Paper Submission (Top 10) | Jun 30 – Jul 15, 2026 |
| Awards at CSoNet 2026 | Nov 16–18, 2026 |

### Recommended System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Endpoint                         │
│                     (FastAPI / Flask)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │    Query Classifier  │
              │  (Type 1 or Type 2) │
              └────┬────────────┬───┘
                   │            │
       ┌───────────▼──┐    ┌────▼──────────────┐
       │  Logic Track  │    │  Physics Track     │
       │  (Type 1)     │    │  (Type 2)          │
       │               │    │                    │
       │ 1. NL→FOL     │    │ 1. Formula RAG     │
       │ 2. Z3 Solver  │    │ 2. CoT Reasoner    │
       │ 3. NL Explain │    │ 3. Numerical Calc  │
       └───────┬───────┘    └────────┬───────────┘
               │                     │
               └──────────┬──────────┘
                          │
               ┌──────────▼──────────┐
               │   Response Builder   │
               │  answer + explanation│
               │  + fol/cot/premises  │
               └─────────────────────┘
```

### Suggested Tech Stack

| Component | Options |
|---|---|
| **Base LLM** | LLaMA 3.1 8B Instruct, Qwen2.5 7B Instruct, Mistral 7B Instruct, Phi-3 Mini |
| **Fine-tuning** | LoRA / QLoRA via HuggingFace PEFT |
| **Symbolic engine** | Z3 Solver (`pip install z3-solver`) |
| **Orchestration** | LangChain, LlamaIndex |
| **Retrieval** | FAISS, ChromaDB |
| **API server** | FastAPI + Uvicorn |
| **Containerization** | Docker |

### Key References

- EXACT 2025 findings paper: https://ceur-ws.org/Vol-4152/paper98.pdf
- Z3 Solver (Python): https://github.com/Z3Prover/z3
- LLaMA 3.1 8B: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
- Qwen2.5 7B: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- LangChain: https://python.langchain.com
- FastAPI: https://fastapi.tiangolo.com

### Notes for the Agent

- The system must handle **two distinct input formats** depending on dataset type — always detect which type a query belongs to before processing
- For Type 1, the `premises-NL` field is provided in the request and should be used as context
- For Type 2, no context is provided — the model must rely on internal physics knowledge or a retrieval system
- `answer` and `explanation` are **always required** in every response — never return a response without them
- Richer optional fields (`fol`, `cot`, `premises`) directly improve the final score; include them whenever feasible
- All LLM calls must route through a **local or self-hosted** model — no external commercial API calls

---

## 🧠 SYSTEM — Kiến trúc hệ thống EXACT 2026 NeuroSymbolic-QA

> **Single Source of Truth (SSOT)** — Tài liệu thống nhất mô tả toàn bộ pipeline, vai trò từng thư viện/tech stack, và các tài liệu nghiên cứu tham khảo.
> Được tổng hợp từ `APPROACHES.md`, `PIPELINE.md`, và `RESEARCH.md`.

---

### 1. Tổng quan hệ thống

**Triết lý cốt lõi:** "Không để LLM tự làm toán. LLM chỉ làm nhiệm vụ giao tiếp và dịch thuật, phần tính toán và suy luận logic giao cho các công cụ toán học chuyên dụng."

**Kiến trúc:** Multi-Agent Pipeline dạng **State Graph** kết hợp **Symbolic Reasoning**, sử dụng mẫu thiết kế Hybrid (Routing + Sequential + Evaluator-Optimizer).

**Ràng buộc quan trọng:**
- LLM phải chạy **nội bộ (local)**, kích thước ≤ 8B — cấm gọi API bên ngoài (OpenAI, Anthropic, Google)
- Dataset Type 1: `question` + `premises-NL` (text only)
- Dataset Type 2: `question` only (bài toán vật lý dạng text, không có ảnh)
- API Response bắt buộc phải có: `answer`, `explanation`
- API Response **không** có field `idx`

---

### 2. Pipeline đầy đủ: Từ Input đến Output

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
            │                          6b   │ SELF-VERIFIER NODE         │
            │                               │ Substitute kết quả ngược   │
            │                               │ vào phương trình gốc để    │
            │                               │ kiểm tra tính đúng đắn     │
            │                               │ Sai → trigger fallback     │
            │                               └────────┬───────────────────┘
            │                                        │
            │                                        ▼
            │                               ┌────────────────────────────┐
            │                          6c   │ COT BUILDER                │
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

#### Chi tiết từng bước

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
| 5b* | Code Agent *(optional, sau demo)* | `question` (str) | `SolverResult` | Fallback về SymPy Solver truyền thống |
| 6b | Self-Verifier | `{answer, unit, given, formulas}` | `{verified: bool}` | Log warning + giảm confidence, không block pipeline |
| 6c | CoT Builder | `parsed` + `solver_steps` | `cot: list[str]` | — |
| 7 | Explainer Agent | Kết quả solver + question gốc | `explanation: str` | Retry 1 lần với simplified prompt |
| 8 | Response Builder | Tất cả kết quả | JSON theo API schema | Luôn đảm bảo có `answer` + `explanation` |

> **⚠️ TODO — Vector DB source:** Ban tổ chức sẽ công bố source materials của Type 2 tại kick-off workshop (09/05). Sau khi nhận, populate FAISS index từ các tài liệu đó. Trong thời gian chờ, dùng công thức vật lý cơ bản (Ohm's law, KVL, KCL, công thức tụ điện...) làm seed data.
> 
> **📌 Memory note:** FAISS index này đóng vai trò **Semantic Memory** (công thức/định luật cố định) + **Episodic Memory** (bài mẫu + CoT). Ưu tiên populate Semantic Memory trước để demo chạy được, thêm Episodic Memory sau. Xem chi tiết tại Section 4.4.
---

### 3. State Schema — Dữ liệu chia sẻ giữa các Node

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

    solver_result: Optional[SolverResult]  # Critical: unified interface cho Explainer
    fol_retries: int                       # Critical: LangGraph retry loop cần biết đã retry bao nhiêu lần
```

#### Interface trung gian — SolverResult

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

### 4. Tech Stack — Vai trò từng thư viện

#### 4.1. Orchestration & API

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **FastAPI** | Web framework xử lý HTTP request/response, validate input với Pydantic | 1 API Gateway |
| **Uvicorn** | ASGI server chạy FastAPI với hiệu năng cao | 1 API Gateway |
| **LangGraph** *(khuyến nghị)* | Framework orchestration dạng State Graph — quản lý luồng Node, conditional edges (rẽ nhánh), và vòng lặp (retry loop) | Toàn bộ pipeline (2→8) |
| **Pydantic** | Định nghĩa và validate schema cho Request/Response | 1, 8 |

#### 4.2. LLM Inference

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

#### 4.3. Symbolic Reasoning (Cốt lõi Neuro-Symbolic)

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **Z3-Solver** | Theorem prover — chứng minh/bác bỏ logic mệnh đề dựa trên FOL. **Đây là thành phần "Symbolic" cốt lõi** đảm bảo tính deterministic và traceable cho reasoning | 4a (validate), 5a (solve) |
| **SymPy** | Thư viện tính toán symbolic — giải phương trình, đổi đơn vị, tính toán số học chính xác tuyệt đối (không bị hallucination số) | 5b |

#### 4.4. RAG & Vector Database

| Thư viện | Vai trò trong pipeline | Bước sử dụng |
|----------|----------------------|---------------|
| **FAISS** (hoặc ChromaDB) | Vector database lưu trữ embedding của các định luật/công thức vật lý. Giúp LLM nhỏ (< 8B) truy xuất đúng công thức thay vì tự "bịa" | 4b Formula RAG |
| **Sentence-Transformers** | Tạo embedding vector từ text (công thức, premises) để lưu vào FAISS | 4b Formula RAG |
| **LangChain** | Cung cấp các abstraction cho RAG chain (retriever → prompt → LLM) | 4b, Fallback flows |

##### Agent Memory Architecture cho Physics Knowledge Base

FAISS Vector DB trong node ④b thực chất là sự kết hợp của **2 loại memory** phù hợp nhất với đặc thù kiến thức vật lý của cuộc thi:

| Loại Memory | Vai trò trong pipeline | Implementation |
|---|---|---|
| **Semantic Memory** *(bắt buộc, ưu tiên cao nhất)* | Lưu kiến thức vật lý có cấu trúc cố định: công thức, định luật, mối quan hệ giữa các đại lượng (`V → depends on → I, R`). Đây là nền tảng để SymPy Solver tính đúng | FAISS index với `formula_sympy`, `variables`, `keywords` — theo format `PHYSICS_DATA.md` |
| **Episodic Memory** *(nên có, sau demo)* | Lưu lại các bài toán đã giải thành công cùng CoT mẫu. Khi gặp bài tương tự, retrieve ra làm few-shot examples cho LLM — giúp explanation đúng format kỳ vọng của BTC | Thêm `example_question` + `example_cot` vào cùng FAISS document (đã có sẵn trong format `PHYSICS_DATA.md`) |

**3 loại memory không cần áp dụng:**
- **Working Memory** — đã có sẵn dưới dạng `PipelineState`, không cần thiết kế riêng
- **Procedural Memory** — có giá trị về lâu dài (lưu workflow thành công làm template), nhưng không phải ưu tiên trong phạm vi cuộc thi
- **Hierarchical Memory** — overkill, phù hợp agent cần nhớ hàng nghìn interaction, không phải knowledge base vật lý cố định

**Kết quả:** Mỗi document trong FAISS vừa là Semantic Memory (công thức) vừa là Episodic Memory (ví dụ giải mẫu) — nhất quán với format đã định nghĩa trong `PHYSICS_DATA.md`.

#### 4.5. Infrastructure & Monitoring

| Thư viện / Tool | Vai trò trong pipeline | Bước sử dụng |
|-----------------|----------------------|---------------|
| **Python logging** (JSON format) | Ghi log mỗi request: question, type, answer, confidence, có FOL/CoT hay không — phục vụ debug và demo live. Bắt buộc log thêm: fol_retries (số lần loop 4a), fallback_triggered (True/False), z3_timeout (True/False), solver_source ("z3"/"sympy"/"llm_fallback") — các field này là input cho /exact-error-analysis skill | Toàn bộ pipeline |
| **YAML config** (`configs/config.yaml`) | Cấu hình mặc định của hệ thống: model name, timeout, temperature... Được commit lên Git, dùng chung cho cả team | Toàn bộ |
| **`.env`** | Cấu hình riêng từng máy (device, model path...). Ghi đè lên config.yaml. **Không** commit lên Git | Toàn bộ |

#### 4.6. Code Execution Sandbox (Type 2 — Optional Enhancement)

> Áp dụng sau demo khi muốn nâng cấp node ⑤b. Thay thế hoặc chạy song song với SymPy Solver hiện tại.

| Thư viện / Tool | Vai trò | Bước sử dụng |
|---|---|---|
| **RestrictedPython** | Sandbox nhẹ, chạy trong cùng process Python — block các lệnh nguy hiểm (`import os`, `open`, network calls), chỉ cho phép math/sympy operations | ⑤b Code Agent |
| **subprocess + venv** | Sandbox nặng hơn — chạy code trong subprocess riêng với timeout, hoàn toàn isolated khỏi main process | ⑤b Code Agent (fallback nếu RestrictedPython không đủ) |

---

### 5. Fallback Strategy — Chiến lược xử lý lỗi

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

### 5.1. Self-Verification — Kiểm tra tính đúng đắn của SymPy (Type 2)

Sau khi SymPy tính được kết quả, **substitute ngược lại vào phương trình gốc** để xác minh. Đây là practical tip được ban tổ chức khuyến nghị tại kick-off workshop.

**Cơ chế hoạt động:**
```python
def self_verify(answer: float, unit: str, given: dict, formula: str) -> bool:
    """
    Ví dụ: tính được R = 5Ω từ V=10V, I=2A
    Substitute ngược: V/R = 10/5 = 2 → khớp I = 2A ✅

    Nếu không khớp (tolerance > 1e-6) → verified = False
    → Giảm confidence xuống 0.4, log warning
    → Không block pipeline — vẫn trả về answer nhưng confidence thấp
    """
    from sympy import symbols, solve, Eq, N
    try:
        # Parse formula và substitute các giá trị đã biết
        # So sánh kết quả tính ngược với given values
        ...
        return abs(computed - expected) < 1e-6
    except Exception:
        return True  # Không verify được → không penalty, tiếp tục bình thường
```

**Lưu ý quan trọng:**
- Self-verification **không block pipeline** — nếu fail, chỉ giảm `confidence` và log, không trigger full fallback
- Nếu verify thành công → `confidence` giữ nguyên (1.0)
- Nếu verify thất bại → `confidence` = 0.4, log `self_verify_failed=True`
- Nếu không verify được (formula phức tạp) → bỏ qua, `confidence` giữ nguyên

---

### 5.2. Fine-Tuning — Optional Optimization (sau khi có baseline)

> ⚠️ **Không phải bước bắt buộc.** Chỉ thực hiện sau khi pipeline cơ bản đã chạy được và có kết quả eval từ `/exact-eval-run`.

Ban tổ chức khuyến nghị: *"Fine-tune on training data to adapt the LLM to the specific question format."*

**Khi nào nên fine-tune:**
- FOL parsability rate < 70% sau khi đã tối ưu prompt hết mức
- Physics Parser trích xuất sai biến số/đơn vị trên > 30% mẫu
- Explanation không đúng format mong đợi của BTC

**Cách tiếp cận (QLoRA):**
```python
# Chỉ fine-tune node có vấn đề, không fine-tune toàn bộ
qlora_config = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "v_proj"],
    "bits": 4,
}
# Training data format: instruction → output theo đúng format API
# Bắt buộc khai báo mọi external dataset dùng để fine-tune (rules cuộc thi)
```

**Thứ tự ưu tiên:**
```
Prompt engineering → Đo eval → Nếu chưa đủ: LoRA fine-tune node cụ thể → Đo lại
```

---

### 5.3. Ensemble — Optional, High Effort

> ⚠️ **Optional hoàn toàn** — chỉ xem xét nếu còn thời gian sau khi pipeline chính đã ổn định và đạt baseline tốt.

Ban tổ chức đề xuất: *"Ensemble multiple approaches and select the most consistent answer."*

**Ý tưởng:** Chạy song song nhiều approaches cho cùng 1 query, chọn answer xuất hiện nhiều nhất (majority vote):

```
Query
  │
  ├──► Approach A: Z3 Symbolic    → answer_A
  ├──► Approach B: RAG + LLM      → answer_B
  └──► Approach C: Pure LLM CoT   → answer_C
                │
                ▼
        Majority Vote / Confidence-weighted
                │
                ▼
        Final answer (answer xuất hiện nhiều nhất)
```

**Ràng buộc cần nhớ:** Tổng tham số của tất cả LLM trong ensemble **phải ≤ 8B**. Nếu dùng 1 model 7B thì không thể chạy thêm model khác song song.

**Thực tế:** Với 1 model ≤ 8B, ensemble khả thi nhất là chạy **cùng 1 model với nhiều prompt khác nhau** (temperature sampling) rồi majority vote — không cần nhiều model.

---

### 5.4. Code Agent cho Type 2 — Optional Enhancement

> ⚠️ **Thực hiện sau demo** — chỉ khi SymPy Solver hiện tại không đủ xử lý các bài toán phức tạp (hệ nhiều phương trình, mạch điện phức hợp). Thay thế hoặc chạy **song song** với node ⑤b hiện tại.

Ban tổ chức đề xuất tại kick-off workshop: *"LLM generates Python/SymPy code for computation, execute code to get precise numerical answers."*

#### Cơ chế hoạt động

Thay vì parse cứng input → gọi SymPy API, LLM **tự sinh Python code** rồi execute trong sandbox:

```
Physics Parser (③b)
        │
        ▼
Code Agent (⑤b nâng cấp)
        │
        ├─► LLM sinh Python/SymPy code giải bài toán
        │       prompt: "Write Python code using SymPy to solve: {question}"
        │
        ├─► Execute trong sandbox (RestrictedPython hoặc subprocess)
        │
        ├─► Lấy stdout làm numerical answer
        │
        └─► Self-Verifier (⑥b) kiểm tra kết quả như bình thường
```

#### Implementation tối giản

```python
import RestrictedPython
from RestrictedPython import compile_restricted, safe_globals

CODE_GEN_PROMPT = """Write a Python script using SymPy to solve the following physics problem.
The script must:
1. Import only sympy and math
2. Print ONLY the final numerical answer followed by its unit on the last line
   Format: "ANSWER: <value> <unit>"
3. Show intermediate calculation steps as comments

Problem: {question}
"""

def code_agent_solve(question: str) -> SolverResult:
    # Bước 1: LLM sinh code
    raw_code = call_llm(
        prompt=CODE_GEN_PROMPT.format(question=question),
        system="You are a physics problem solver. Generate clean, correct Python code."
    )
    code = extract_code_block(raw_code)  # strip markdown fences

    # Bước 2: Execute trong sandbox với timeout
    try:
        result = execute_sandboxed(code, timeout=10)
        answer, unit = parse_answer_line(result.stdout)
        steps = extract_comments_as_steps(code)
        return SolverResult(
            answer=answer, unit=unit, steps=steps,
            fol=None, source="sympy", confidence=1.0
        )
    except (TimeoutError, SyntaxError, Exception) as e:
        logger.warning(f"code_agent_failed: {e}")
        # Fallback về SymPy parser truyền thống
        return sympy_solver_fallback(question)


def execute_sandboxed(code: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """
    Chạy code trong subprocess riêng biệt với timeout.
    Hoàn toàn isolated — không thể truy cập filesystem hay network.
    """
    return subprocess.run(
        ["python3", "-c", code],
        capture_output=True, text=True,
        timeout=timeout,
        # Không truyền env vars — giảm attack surface
        env={"PATH": "/usr/bin:/bin"}
    )
```

#### Tích hợp vào LangGraph

Không cần thêm node mới — Code Agent **thay thế bên trong node ⑤b**:

```python
def sympy_solver_node(state: PipelineState) -> PipelineState:
    parsed = state["parsed_physics"]

    # Thử Code Agent trước (linh hoạt hơn)
    result = code_agent_solve(state["question"])

    # Nếu Code Agent fail → fallback về SymPy parser truyền thống
    if result["source"] == "llm_fallback":
        result = sympy_solver_classic(parsed)

    return {**state, "solver_result": result}
```

#### So sánh với SymPy Parser truyền thống

| | SymPy Parser (hiện tại) | Code Agent (nâng cấp) |
|---|---|---|
| **Bài đơn giản** | ✅ Nhanh, ổn định | ✅ Tốt |
| **Hệ nhiều phương trình** | ⚠️ Cần parse phức tạp | ✅ LLM tự xử lý |
| **Mạch điện phức hợp** | ⚠️ Khó parse | ✅ LLM viết code linh hoạt |
| **Rủi ro sai** | Thấp (deterministic) | Trung bình (LLM có thể bug) |
| **Cần sandbox** | ❌ Không | ✅ Bắt buộc |
| **Khi nào dùng** | Demo + baseline | Sau demo, khi SymPy không đủ |

#### Quy tắc bắt buộc khi implement

- **Bắt buộc dùng sandbox** — không bao giờ `exec()` hay `eval()` code LLM sinh ra trực tiếp trong main process
- **Timeout cứng 10 giây** — code LLM có thể sinh ra infinite loop
- **Chỉ cho phép import** `sympy`, `math`, `cmath` — block tất cả các module khác
- **Parse stdout nghiêm ngặt** — chỉ đọc dòng `ANSWER: <value> <unit>`, ignore toàn bộ output khác
- **Luôn có fallback** về SymPy parser truyền thống nếu Code Agent fail

---

### 6. API Schema

> 🚨 **STALE — KHÔNG dùng schema dưới đây.** Đây là thiết kế NỘI BỘ cũ (`/query`, response 1 object). Spec BTC chính thức = `POST /predict`, response JSON **list** `{query_id, answer, unit(ASCII), explanation, premises_used, reasoning}`. **Nguồn chuẩn: `docs/official_spec_gaps.md` + `CLAUDE.md` §"API Schema — OFFICIAL".**

#### Request
```json
POST /query
{
  "question": "string (bắt buộc)",
  "premises": ["string", "..."]    // rỗng [] nếu Type 2
}
```

#### Response
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

#### Health Check
```
GET /health  →  { "status": "ok" }
```

---

### 7. Design Patterns đang áp dụng

Hệ thống áp dụng kết hợp (Hybrid) các mẫu thiết kế Multi-Agent:

| Pattern | Nơi áp dụng | Mô tả |
|---------|-------------|--------|
| **Routing** | Router Agent (②) | Phân loại input để điều hướng đến đúng track xử lý |
| **Sequential / Chain** | Mỗi Track (③→⑤→⑦) | Các Agent xử lý tuần tự, output của bước trước là input của bước sau |
| **Evaluator-Optimizer** | Logic Evaluator (④a) ↔ Text Parser (③a) | Vòng lặp kiểm tra-sửa lỗi FOL trước khi đưa vào Z3, tối đa 3 lần |
| **Tool-use** | Z3 Solver, SymPy Solver | LLM không tự tính — gọi tool chuyên dụng để đảm bảo chính xác |

#### LangGraph Graph Definition (skeleton)

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
workflow.add_node("self_verifier",    self_verifier_node)
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
workflow.add_edge("sympy_solver",    "self_verifier")
workflow.add_edge("self_verifier",   "cot_builder")
workflow.add_edge("cot_builder",     "explainer")

# Shared ending
workflow.add_edge("explainer",       "response_builder")
workflow.add_edge("response_builder", END)

app = workflow.compile()
```

---

### 8. Tài liệu nghiên cứu & Học tập

#### 8.1. Framework & Tutorials

| Tài liệu | Mô tả | Liên quan đến |
|-----------|--------|---------------|
| **"Multi-Agent Architectures with LangGraph"** (LangChain Docs) | Hướng dẫn cấu hình Node, Edge, Conditional Edge — phục vụ trực tiếp cho việc xây pipeline | Toàn bộ pipeline |
| **LangGraph Concepts: State & Conditional Edges** | Hiểu cách State được chia sẻ giữa các Node, cách rẽ nhánh fallback | 2, 4a |
| **CrewAI Sequential Process** | Framework thay thế nếu muốn triển khai nhanh hơn LangGraph | Toàn bộ pipeline |
| **"AI Agents in LangGraph"** — Khóa học DeepLearning.AI | Rất sát với việc xây dựng node-based pipeline | Toàn bộ pipeline |
| **"Multi AI Agent Systems with crewAI"** — Khóa học DeepLearning.AI | Tư duy phân chia Task và Role cho từng Agent | Thiết kế Agent |

#### 8.2. Nghiên cứu học thuật (Neuro-Symbolic & XAI)

| Tài liệu | Mô tả | Liên quan đến |
|-----------|--------|---------------|
| **"The Landscape of Emerging AI Agent Architectures"** | Phân tích sự khác biệt giữa Single Agent, Multi-Agent, và các cách giao tiếp | Kiến trúc tổng thể |
| **LLM-Compiler** | Cách LLM lập kế hoạch (planning) để gọi các tool solver như Z3/SymPy | 5a, 5b |
| **ReAct Pattern (Reason + Act)** | Agent tự suy nghĩ trước khi hành động — quan trọng cho `explanation` và `cot` | 7 Explainer |
| **Toolformer** | Cách LLM học cách gọi external tools — nền tảng lý thuyết cho Tool-use pattern | 5a, 5b |

#### 8.3. Từ khóa tìm kiếm chuyên sâu
- `LLM + Theorem Prover pipeline`
- `Neuro-Symbolic QA system architecture`
- `ReAct prompt logic solver`
- `LangGraph Multi-Agent Workflows`
- `LangGraph state machine tutorial`

---

### 9. Quy tắc phát triển (Dev Rules)

> [!CAUTION]
> Các quy tắc bắt buộc tuân thủ — vi phạm có thể dẫn đến **disqualification**:

1. **KHÔNG** sử dụng bất kỳ closed-source model nào (GPT, Claude, Gemini...) — kể cả gọi API lẫn chạy local. Chỉ được dùng **open-source LLM ≤ 8B** tham số. Vi phạm → **disqualification**
2. **KHÔNG** sử dụng field `idx` trong codebase — field này không tồn tại trong API schema
3. `answer` và `explanation` là **bắt buộc** — không bao giờ trả response thiếu 2 field này
4. Luôn wrap LLM calls trong `try/except` — API endpoint không được phép crash
5. Khi parse JSON từ LLM output, luôn dùng `json.loads()` với error handling, **không** dùng `eval()`
6. Type 2 không có premises → field `premises` trong request là list rỗng `[]`
7. Đơn vị (unit) phải đi kèm answer số học trong explanation
8. **Không chạy song song** `transformers` và `vLLM` trong cùng process — chọn một backend qua `configs/config.yaml`
9. Mọi Solver đều phải trả về `SolverResult` struct trước khi truyền cho Explainer Agent — không truyền raw dict tùy tiện
10. Mọi request phải hoàn thành trong **30 giây** — thiết lập `asyncio.timeout(30)` ở API Gateway
11. **Phải công khai mọi external dataset** sử dụng để fine-tune LLM hoặc Symbolic Engine. Mọi nguồn dữ liệu bên ngoài phải được khai báo rõ ràng trong tài liệu. Giấu nguồn dữ liệu → **disqualification**
12. **Khi dùng Code Agent (⑤b*):** bắt buộc chạy trong sandbox, timeout cứng 10s, chỉ cho phép import `sympy`/`math`/`cmath` — tuyệt đối không `exec()` code LLM trực tiếp trong main process

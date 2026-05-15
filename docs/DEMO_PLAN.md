# EXACT 2026 — Demo Pipeline Plan

**Mục tiêu:** Hoàn thành pipeline end-to-end nhận câu hỏi → trả về answer + explanation.
**Thời gian:** 3–4 ngày (không gấp — ưu tiên đúng hơn nhanh).
**Tiêu chí done:** `POST /query` với câu hỏi thật từ training data trả về JSON hợp lệ có `answer` và `explanation`, dù chất lượng chưa cần tốt.
**Chưa cần quan tâm:** Độ chính xác của answer, chất lượng FOL, prompt engineering, fine-tuning.

---

## Nguyên tắc

- **Parallel tối đa** — 5 người làm song song, hội tụ 1 lần duy nhất ở cuối
- **Mock trước, thật sau** — mỗi người dùng mock của dependency để không bị blocked
- **Interface ưu tiên** — `pipeline/state.py` phải được thống nhất trong buổi đầu trước khi ai bắt đầu code
- **Không tự ý thay đổi** `SolverResult` và `PipelineState` sau khi đã thống nhất — mọi thay đổi phải báo cả team
- **Không vội** — 3–4 ngày đủ để làm kỹ từng bước, không cần rush

---

## File Interface Chung — Thống nhất trước khi bắt đầu

> **Người 5 viết, cả team review và ký off trong buổi đầu tiên (Ngày 1 sáng) trước khi ai bắt đầu code.**

### `pipeline/state.py`

```python
from typing import TypedDict, Optional, Literal

class SolverResult(TypedDict):
    answer: str
    unit: Optional[str]        # Chỉ Type 2 — vd: "mJ", "Ω"
    steps: list[str]           # proof_steps (Z3) hoặc sympy steps
    fol: Optional[list[str]]   # FOL validated — chỉ Type 1
    source: Literal["z3", "sympy", "llm_fallback"]
    confidence: float          # 1.0 | 0.6 | 0.5

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

---

## Phân công

```
Người 1 ──────────────────────────────────► API Gateway + Router
Người 2 ──────────────────────────────────► Type 1 Track (③a → ④a → ⑤a) + Explainer Type 1
Người 3 ──────────────────────────────────► Type 2 Track (③b → ④b → ⑤b → ⑥b) + Explainer Type 2
Người 4 ──────────────────────────────────► LLM Loader + Inference Wrapper
Người 5 ──────────────────────────────────► Response Builder + Integration
                                                              ▲
                                                  Điểm hội tụ cuối cùng
```

---

## Người 1 — API Gateway & Router

**Phụ thuộc:** Không ai — bắt đầu ngay.
**Unblocks:** Người 5 (cần endpoint để test integration).

### Việc cần làm

| Task               | File                  | Mô tả                                           |
| ------------------ | --------------------- | ----------------------------------------------- |
| Định nghĩa schemas | `api/schemas.py`      | `QueryRequest`, `QueryResponse` Pydantic models |
| Router logic       | `api/router.py`       | Phân loại type1/type2 theo premises và keyword  |
| FastAPI app        | `api/main.py`         | `POST /query`, `GET /health`, mock response tạm |
| Cấu hình server    | `configs/config.yaml` | host, port, timeout                             |

### Mock tạm để team test ngay

```python
@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    query_type = classify_query(request.question, request.premises)
    return QueryResponse(
        answer="A",
        explanation=f"[MOCK — {query_type}] Pipeline not yet connected."
    )
```

### Tiêu chí hoàn thành

- [x] `GET /health` trả về `{"status": "ok"}` — không exception ✅
- [x] `POST /query` với payload hợp lệ trả về JSON đúng schema `QueryResponse` — đang trả mock, chờ wire pipeline thật
- [x] `POST /query` thiếu field `question` trả về HTTP 422, không crash server ✅ (Pydantic validation)
- [x] Router phân loại đúng: request có `premises` → `type1`; câu hỏi chứa "calculate", "voltage", "resistance"... → `type2` ✅
- [x] Router test pass trên 10 mẫu thủ công (5 type1 + 5 type2) — dùng official training data
- [x] Server khởi động bằng `uvicorn api.main:app --reload` không có lỗi import — port 8000 đang được instance khác giữ

---

## Người 2 — Type 1 Track + Explainer Type 1

**Phụ thuộc:** `call_llm()` từ Người 4 — dùng `call_llm_mock()` trước khi Người 4 xong.
**Unblocks:** Người 5 (cần `SolverResult` + `explain_type1()` từ Type 1 để wire pipeline).

### Việc cần làm

| Task             | File                          | Mô tả                                                     |
| ---------------- | ----------------------------- | --------------------------------------------------------- |
| NL → FOL         | `pipeline/type1/nl_to_fol.py` | Gọi LLM, nhận `premises_nl`, trả về `list[str]` FOL       |
| FOL Validator    | `pipeline/type1/z3_solver.py` | Parse FOL, chạy Z3, trả về `SolverResult`                 |
| Explainer Type 1 | `pipeline/type1/explainer.py` | Implement `explain_type1(solver_result, question) -> str` |

### Prompt tối giản (chưa cần tối ưu)

```python
NL_TO_FOL_PROMPT = """Convert each premise to FOL notation.
Use: ∀ ∃ ∧ ∨ → ¬
Return ONLY a JSON array of strings, no explanation.

Premises:
{premises}"""
```

### Fallback tối giản khi Z3 fail

```python
# Nếu Z3 không parse được → trả về llm_fallback ngay, không retry
return SolverResult(
    answer="Unable to determine",
    unit=None,
    steps=["Z3 parse failed — fallback to LLM"],
    fol=None,
    source="llm_fallback",
    confidence=0.5
)
```

### Tiêu chí hoàn thành

- [ ] `nl_to_fol(premises_nl: list[str]) -> list[str]` chạy được với `call_llm_mock()`
- [ ] `nl_to_fol` trả về đúng kiểu `list[str]`, không crash khi LLM trả về JSON lỗi
- [ ] `z3_solver(fol_list, question) -> SolverResult` chạy được trên ít nhất 1 record từ training data
- [ ] Khi Z3 timeout hoặc parse fail → trả về `SolverResult` với `source="llm_fallback"`, không raise exception
- [ ] Toàn bộ Type 1 track chạy end-to-end: `premises_nl` → `SolverResult` — dù answer sai cũng được
- [ ] Không có unhandled exception khi input là string rỗng hoặc premises list rỗng
- [ ] `explain_type1(solver_result, question) -> str` trả về string không rỗng
- [ ] `explain_type1` không crash khi `solver_result["steps"]` là list rỗng

---

## Người 3 — Type 2 Track + Explainer Type 2

**Phụ thuộc:** `call_llm()` từ Người 4 — dùng `call_llm_mock()` trước khi Người 4 xong.
**Unblocks:** Người 5 (cần `SolverResult` + `explain_type2()` từ Type 2 để wire pipeline).

### Việc cần làm

| Task             | File                               | Mô tả                                                     |
| ---------------- | ---------------------------------- | --------------------------------------------------------- |
| Physics Parser   | `pipeline/type2/physics_parser.py` | Gọi LLM, trích xuất given/find/formulas                   |
| SymPy Solver     | `pipeline/type2/sympy_solver.py`   | Giải phương trình, trả về `SolverResult`                  |
| CoT Builder      | `pipeline/type2/cot_builder.py`    | Format solver steps thành `list[str]`                     |
| Explainer Type 2 | `pipeline/type2/explainer.py`      | Implement `explain_type2(solver_result, question) -> str` |

### Prompt tối giản (chưa cần tối ưu)

```python
PHYSICS_PARSER_PROMPT = """Extract physics problem components. Return ONLY valid JSON.
Question: {question}
Format:
{{
  "given": [{{"var": "C", "value": 100, "unit": "μF"}}],
  "find": {{"var": "E", "unit": "J"}},
  "formulas": ["E = 0.5 * C * U^2"]
}}"""
```

### Unit conversion tối giản cần có ngay

```python
UNIT_CONVERSIONS = {
    "μF": 1e-6, "mF": 1e-3,
    "kΩ": 1e3,  "MΩ": 1e6,
    "mA": 1e-3, "kV": 1e3,
    "mW": 1e-3, "kW": 1e3,
    "mJ": 1e-3, "kJ": 1e3,
}
```

### Tiêu chí hoàn thành

- [ ] `physics_parser(question: str) -> dict` chạy được với `call_llm_mock()`
- [ ] `physics_parser` không crash khi LLM trả về JSON lỗi — fallback về dict rỗng
- [ ] `sympy_solver(parsed: dict) -> SolverResult` tính được ít nhất 1 bài mẫu từ training data (vd: `E = 0.5 * C * U^2`)
- [ ] `cot_builder(steps: list[str]) -> list[str]` trả về list có ít nhất 1 phần tử
- [ ] Khi SymPy fail → trả về `SolverResult` với `source="llm_fallback"`, không raise exception
- [ ] Toàn bộ Type 2 track chạy end-to-end: `question` → `SolverResult` — dù answer sai cũng được
- [ ] Unit conversion hoạt động đúng với ít nhất: μF, kΩ, mJ, mA, kV
- [ ] `explain_type2(solver_result, question) -> str` trả về string không rỗng
- [ ] `explain_type2` không crash khi `solver_result["steps"]` là list rỗng

---

## Người 4 — LLM Loader & Inference Wrapper

**Phụ thuộc:** Không ai — bắt đầu ngay.
**Unblocks:** Người 2 và 3 (đang chờ `call_llm()`).
**Ưu tiên cao nhất:** Cần xong mock version trước, real version sau.

### Việc cần làm

| Task           | File               | Mô tả                                             | Ưu tiên       |
| -------------- | ------------------ | ------------------------------------------------- | ------------- |
| Mock LLM       | `llm/inference.py` | `call_llm_mock()` trả về dummy output đúng format | 🔴 Cao nhất   |
| Model loader   | `llm/loader.py`    | Load model từ config, singleton pattern           | 🟡 Sau mock   |
| Real inference | `llm/inference.py` | `call_llm()` thật với transformers backend        | 🟡 Sau loader |

### Mock version — viết trước tiên

```python
def call_llm_mock(prompt: str, system: str = "") -> str:
    """Mock trả về dummy output đúng format để Người 2, 3 test ngay."""
    if "FOL" in system or "FOL" in prompt:
        return '["∀x (A(x) → B(x))", "∀x (B(x) → C(x))"]'
    if "physics" in system.lower() or "Extract" in prompt:
        return ('{"given": [{"var": "C", "value": 100, "unit": "μF"},'
                '{"var": "U", "value": 30, "unit": "V"}],'
                '"find": {"var": "E", "unit": "J"},'
                '"formulas": ["E = 0.5 * C * U**2"]}')
    return "The answer follows from the given premises."
```

### Real version interface

```python
def call_llm(prompt: str, system: str = "", max_retries: int = 2) -> str:
    """
    Gọi LLM thật, retry tối đa max_retries lần nếu lỗi.
    Raise RuntimeError nếu vẫn fail sau max_retries.
    """
    ...
```

### Tiêu chí hoàn thành

- [ ] `call_llm_mock()` available để Người 2 và 3 import — **xong trong buổi sáng Ngày 1**
- [ ] Model load được từ đường dẫn trong `configs/config.yaml` mà không OOM
- [ ] `call_llm(prompt)` trả về string, không trả về `None`
- [ ] Retry đúng `max_retries` lần khi model throw exception, sau đó raise `RuntimeError`
- [ ] Thời gian load model chỉ xảy ra 1 lần (singleton) — gọi `call_llm()` lần 2 không load lại model
- [ ] `call_llm()` chạy được trên CPU nếu không có GPU (chậm nhưng không crash)

---

## Người 5 — Response Builder + Integration

**Phụ thuộc:** Tất cả — bắt đầu muộn hơn, nhưng có việc làm ngay từ đầu.
**Owns:** Điểm hội tụ cuối — chịu trách nhiệm pipeline chạy end-to-end.

> ✅ `pipeline/state.py` đã hoàn thành — không cần làm lại. Import trực tiếp:
>
> ```python
> from pipeline.state import SolverResult, PipelineState
> ```

### Việc cần làm

| Task             | File                      | Phụ thuộc                     | Làm khi nào          | Trạng thái  |
| ---------------- | ------------------------- | ----------------------------- | -------------------- | ----------- |
| Logging setup    | `api/logger.py`           | Không ai                      | **Bắt đầu ngay**     | 🔴 Chưa làm |
| Response Builder | `api/response_builder.py` | `api/schemas.py` (✅ có mock) | **Bắt đầu ngay**     | 🔴 Chưa làm |
| Wire pipeline    | `api/main.py`             | Người 2, 3 done               | Sau khi P2 + P3 xong | ⏳ Chờ      |
| End-to-end test  | `tests/test_api.py`       | Wire xong                     | Cuối cùng            | ⏳ Chờ      |

### File 1 — `api/logger.py` (làm trước tiên)

Mỗi request phải được log đầy đủ theo JSON format (yêu cầu từ `SYSTEM.md §4.5`).
Các node khác **chỉ import `get_logger()`** từ file này — không tự cấu hình logging riêng.

**Spec cần implement** (file hiện có TODO-FIX — thiếu `ts` và chưa merge `extra`):

```python
import logging
import json
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":     datetime.now(timezone.utc).isoformat(),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        if hasattr(record, "extra"):
            payload.update(record.extra)   # merge các field nghiệp vụ vào JSON
        return json.dumps(payload, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

**Cách dùng tại `api/main.py` (cuối mỗi request — 7 field bắt buộc):**

```python
from api.logger import get_logger
logger = get_logger(__name__)

logger.info("request", extra={
    "extra": {
        "question":           request.question[:80],
        "query_type":         query_type,
        "answer":             solver_result["answer"],
        "confidence":         solver_result["confidence"],
        "solver_source":      solver_result["source"],
        "fol_retries":        state.get("fol_retries", 0),
        "fallback_triggered": solver_result["source"] == "llm_fallback",
        "z3_timeout":         False,
    }
})
```

---

### File 2 — `api/response_builder.py` (làm song song với logger)

Đóng gói `SolverResult` + `explanation` thành `QueryResponse`.

**Không cần chờ Người 1** — `api/schemas.py` đã có sẵn, và `response_builder.py` có mock nội bộ để dùng tạm:

```python
# Dùng tạm (mock nội bộ đã có trong file):
from api.response_builder import QueryResponse

# Khi Người 1 xong → chỉ đổi 1 dòng:
from api.schemas import QueryResponse
```

**Spec `build_response` cần implement:**

```python
from pipeline.state import SolverResult

def build_response(solver_result: SolverResult, explanation: str) -> QueryResponse:
    # answer      = solver_result["answer"]
    # confidence  = solver_result["confidence"]
    # fol         = ", ".join(solver_result["fol"]) nếu có, else None
    # cot         = solver_result["steps"] nếu source là "sympy", else None
    # explanation luôn được truyền thẳng, không để rỗng
    ...
```

**Mock `SolverResult` để test `build_response` ngay (không cần chờ P2, P3):**

```python
from pipeline.state import SolverResult

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

response = build_response(mock_type1, "The conclusion follows from premise 1 and 2.")
assert response.answer == "A"
assert response.explanation != ""
```

---

### File 3 — `api/main.py` (wire pipeline — sau khi P2 + P3 xong)

**Mock explainer để wire pipeline trước khi P2, P3 deliver:**

```python
# Dùng tạm — xóa khi Người 2 và 3 deliver explainer thật
def explain_type1(solver_result, question) -> str:
    return f"[MOCK] Logical conclusion: {solver_result['answer']}"

def explain_type2(solver_result, question) -> str:
    return f"[MOCK] Calculated result: {solver_result['answer']} {solver_result.get('unit', '')}"
```

### Prompt Explainer tối giản (dùng khi cần fallback)

```python
EXPLAINER_PROMPT = """Given the following solution, write a clear explanation in English.
Answer: {answer}
Steps: {steps}
Write 2-3 sentences explaining how the answer was reached."""
```

### Wire pipeline vào main.py

```python
@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    try:
        query_type = classify_query(request.question, request.premises)

        if query_type == "type1":
            fol = nl_to_fol(request.premises)
            solver_result = z3_solver(fol, request.question)
            explanation = explain_type1(solver_result, request.question)
        else:
            parsed = physics_parser(request.question)
            solver_result = sympy_solver(parsed)
            solver_result["steps"] = cot_builder(solver_result["steps"])
            explanation = explain_type2(solver_result, request.question)

        return build_response(solver_result, explanation)

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return QueryResponse(answer="Error", explanation=str(e))
```

### Tiêu chí hoàn thành

- [x] `pipeline/state.py` với `SolverResult` và `PipelineState` — **đã xong**
- [ ] `api/logger.py` với `get_logger()` import được từ mọi module — **xong trong buổi sáng Ngày 1**
- [ ] Mỗi request log ra stdout đủ 7 field bắt buộc: `question`, `query_type`, `answer`, `confidence`, `solver_source`, `fol_retries`, `fallback_triggered`
- [ ] Log output là **valid JSON** mỗi dòng — parse được bằng `json.loads(line)`
- [ ] `logger.error()` được gọi trong `except` block của `handle_query` với message chứa traceback
- [ ] `build_response(solver_result, explanation) -> QueryResponse` không bao giờ thiếu `answer` hoặc `explanation`
- [ ] `build_response` pass với cả `mock_type1` và `mock_type2` trước khi wire thật
- [ ] `POST /query` với câu hỏi Type 1 thật từ training data → trả về JSON có `answer` và `explanation`
- [ ] `POST /query` với câu hỏi Type 2 thật từ training data → trả về JSON có `answer` và `explanation`
- [ ] Pipeline không crash khi bất kỳ node nào trả về fallback result
- [ ] `GET /health` vẫn trả về `{"status": "ok"}` sau khi wire pipeline thật

---

## Timeline — 4 ngày

```
         NGÀY 1                NGÀY 2                NGÀY 3           NGÀY 4
  Sáng        Chiều      Sáng        Chiều      Sáng      Chiều      Sáng
    │            │         │            │         │          │          │
    ├─ P5: state.py ───────────────────────────────────────────────────────► ✅
    │
    ├─ P4: call_llm_mock ──► loader ──► call_llm() thật ──────────────────► ✅
    │
    ├─ P1: schemas ──────────► router ──► /health + mock ─────────────────► ✅
    │
    ├─ P2: (mock) nl_to_fol ──────────────► z3_solver ────────────────────► ✅
    │                                                                         │
    ├─ P3: (mock) physics_parser ──────────► sympy ──► cot_builder ─────────► ✅
    │                                                                         │
    └─ P5: ────────────────────────────────────────── explainer ─► wire ───► DEMO ✅
```

| Ngày       | Mục tiêu                   | Milestone                                                                              |
| ---------- | -------------------------- | -------------------------------------------------------------------------------------- |
| **Ngày 1** | Setup + Interface + Mock   | `state.py` approved, `call_llm_mock()` chạy được, API skeleton trả về mock response    |
| **Ngày 2** | Build từng track song song | Type 1: `nl_to_fol` + `z3_solver` xong; Type 2: `physics_parser` + `sympy_solver` xong |
| **Ngày 3** | Explainer + Integration    | `explainer` xong, wire pipeline thật vào `main.py`, chạy thử với câu hỏi thật          |
| **Ngày 4** | Test + Fix + Buffer        | Chạy checklist demo, fix bug, buffer cho sự cố bất ngờ                                 |

**Target: Demo hoạt động cuối Ngày 3, Ngày 4 dành để polish và test.**

---

## Dependency Map

```
call_llm_mock()  ←── Người 4 (xong trong 30 phút đầu)
      │
      ├──────────────────────────────────┐
      ▼                                  ▼
Người 2 (Type 1 track)          Người 3 (Type 2 track)
nl_to_fol → z3_solver           physics_parser → sympy_solver → cot_builder
      │                                  │
      └──────────────┬───────────────────┘
                     ▼
              Người 5 (Integration)
         explainer → response_builder → wire vào main.py
                     │
                     ▼
              Người 1 (API)
            POST /query hoạt động
```

---

## Quy tắc trong quá trình build

1. **Không push thẳng lên `main`** — mỗi người làm trên branch riêng (`p1/api`, `p2/type1`, `p3/type2`, `p4/llm`, `p5/integration`)
2. **Báo ngay khi xong mock dependency** — Người 4 xong `call_llm_mock()` Ngày 1 → ping Người 2 và 3 ngay để họ bắt đầu Ngày 2
3. **Không tự ý thay đổi `pipeline/state.py`** sau khi đã approve — raise PR nếu cần thay đổi
4. **Fallback luôn trả về `SolverResult` hợp lệ** — không raise exception ra ngoài node
5. **Integration là trách nhiệm của Người 5** — các người khác không sửa `api/main.py`

---

## Checklist Demo (Cuối Ngày 3)

Trước khi tuyên bố demo xong, chạy các lệnh sau và confirm tất cả pass:

```bash
# 1. Server khởi động
uvicorn api.main:app --reload

# 2. Health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 3. Type 1 query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which conclusion follows?\nA. All projects are optimized\nB. No projects are optimized",
    "premises": ["If a project is well-tested, it is optimized.", "All projects are well-tested."]
  }'
# Expected: JSON có "answer" và "explanation" không rỗng

# 4. Type 2 query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Calculate the energy stored when C = 100 μF and U = 30 V.",
    "premises": []
  }'
# Expected: JSON có "answer" và "explanation" không rỗng

# 5. Error handling
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "", "premises": []}'
# Expected: Trả về JSON hợp lệ, không trả về HTTP 500
```

**Demo đạt khi:** Cả 5 lệnh trên chạy không có lỗi và trả về đúng format.

> **Ngày 4 — Buffer:** Nếu demo đạt sớm hơn, dùng thời gian còn lại để: test thêm với nhiều câu hỏi từ training data, cải thiện fallback handling, hoặc bắt đầu giai đoạn tối ưu chất lượng sớm.

---

_Sau khi demo xong (Ngày 3–4) → chuyển sang giai đoạn tối ưu chất lượng: prompt engineering, FOL accuracy, SymPy coverage, self-verification._

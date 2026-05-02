# Kiến trúc hệ thống: Phân tích các hướng tiếp cận (System Architecture Approaches)

Tài liệu này trình bày chi tiết hai hướng tiếp cận khả thi nhất để giải quyết bài toán EXACT 2026, cân bằng giữa tính chính xác của toán học/logic và sự trôi chảy của các mô hình ngôn ngữ lớn (LLM).

> **Lưu ý quan trọng về dataset (đọc trước khi implement):**
> - **Type 1 input:** `question` + `premises-NL` (text only, không có ảnh)
> - **Type 2 input:** `question` only (text only, không có ảnh, không có premises)
> - Dataset Type 2 là bài toán vật lý dạng **text thuần** — không có sơ đồ mạch điện dạng hình ảnh
> - API submission **không có field `idx`** — các field hợp lệ là: `answer`, `explanation`, `fol`, `cot`, `premises`, `confidence`

---

## So sánh nhanh hai hướng

| Tiêu chí | Hướng 1: Multi-Agent + Symbolic | Hướng 2: MoE Fine-Tuning |
|---|---|---|
| Độ chính xác P1 | ⭐⭐⭐⭐⭐ (deterministic) | ⭐⭐⭐⭐ (phụ thuộc training) |
| Chất lượng giải thích P2 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (end-to-end fluent) |
| Reasoning depth P3 | ⭐⭐⭐⭐⭐ (FOL từ Z3) | ⭐⭐⭐ (CoT có thể bịa) |
| Latency | Cao (nhiều bước) | Thấp (1 lần gọi model) |
| Độ phức tạp triển khai | Cao | Trung bình |
| Rủi ro hallucination | Thấp | Trung bình (số học) |
| Khả năng debug | Dễ (từng bước tách biệt) | Khó (black box) |

**Khuyến nghị:** Hướng 1 phù hợp hơn cho EXACT 2026 vì ban giám khảo đánh giá **reasoning depth trực tiếp** trong vòng live demo — cần output có thể trace được.

---

## Hướng tiếp cận 1: Multi-Agent Systems kết hợp Symbolic Reasoning

**Triết lý:** "Không để LLM tự làm toán. LLM chỉ làm nhiệm vụ giao tiếp và dịch thuật, phần tính toán và suy luận logic giao cho các công cụ toán học chuyên dụng."

### Kiến trúc tổng thể

```
HTTP Request (question [+ premises-NL])
        │
        ▼
┌───────────────────┐
│   API Gateway     │  FastAPI, nhận JSON input
│   & Type Router   │  Phân loại: Type 1 hay Type 2?
└───────┬───────────┘
        │
   ┌────┴─────┐
   │          │
   ▼          ▼
[Type 1]   [Type 2]
Logic      Physics
Track      Track
   │          │
   └────┬─────┘
        ▼
┌───────────────────┐
│  Explainer Agent  │  LLM sinh explanation từ kết quả solver
│  Response Builder │  Đóng gói JSON response theo API schema
└───────────────────┘
        │
        ▼
HTTP Response { answer, explanation, fol, cot, premises, confidence }
```

### Type Router — Phân loại yêu cầu

**Input:** raw query text  
**Logic phân loại:**
- Nếu request payload có field `premises-NL` và không rỗng → **Type 1**
- Nếu không có `premises-NL` → **Type 2**
- Fallback: dùng keyword detection ("calculate", "resistance", "voltage", "capacitor", "circuit" → Type 2)

```python
def classify_query(payload: dict) -> Literal["type1", "type2"]:
    if payload.get("premises") and len(payload["premises"]) > 0:
        return "type1"
    physics_keywords = {"calculate", "resistance", "voltage", "current",
                        "capacitor", "circuit", "power", "energy", "charge"}
    question_words = set(payload["question"].lower().split())
    if physics_keywords & question_words:
        return "type2"
    return "type1"  # default fallback
```

---

### Luồng Type 1 — Logic-Based Educational Queries

**Input:** `question` (str) + `premises_nl` (list[str])

#### Bước 1: Text Parser Agent — NL → FOL

**Model:** LLM ≤ 8B (LLaMA 3.1 8B Instruct hoặc Qwen2.5 7B Instruct)  
**Nhiệm vụ:** Chuyển từng premise tiếng Anh thành FOL

**Prompt template:**
```
System: You are a First-Order Logic (FOL) translator. 
Convert each natural language premise into FOL notation.
Use standard symbols: ∀ (ForAll), ∃ (Exists), ∧ (AND), ∨ (OR), → (implies), ¬ (NOT).
Return ONLY a JSON list of FOL strings, no explanation.

User: Convert these premises to FOL:
{premises_nl_numbered_list}
```

**Output expected:**
```json
[
  "ForAll(c, (well_structured(c) ∧ has_exercises(c)) → enhances_engagement(c))",
  "ForAll(c, (enhances_engagement(c) ∧ advanced_resources(c)) → enhances_critical_thinking(c))"
]
```

**Error handling:** Nếu LLM trả về FOL không parse được → fallback sang dùng `premises-NL` trực tiếp làm context cho Explainer Agent, bỏ qua Z3.

#### Bước 2: Logic Solver Agent — Z3 Solver

**Tool:** `z3-solver` (Python package)  
**Nhiệm vụ:** Nhận FOL list, chứng minh/bác bỏ từng answer option

```python
from z3 import *

def solve_with_z3(fol_premises: list[str], question_type: str, options: list[str]) -> dict:
    """
    Với MCQ: thử chứng minh từng option, tìm option được entail bởi premises
    Với Yes/No/Uncertain: chứng minh conclusion, bác bỏ negation, hoặc báo uncertain
    Returns: { "answer": "B", "supporting_premises": [0, 2], "proof_steps": [...] }
    """
    ...
```

**Output của Z3:**
- `answer`: đáp án đúng (letter hoặc Yes/No/Uncertain)
- `supporting_premises`: index của các premise được dùng trong proof
- `proof_steps`: các bước suy luận trung gian

**Fallback khi Z3 thất bại:** Nếu FOL parse error hoặc timeout (>5s) → chuyển sang **RAG + LLM reasoning** với premises-NL làm context.

#### Bước 3: Explainer Agent (dùng chung cho cả 2 luồng)

**Model:** LLM ≤ 8B  
**Input:** answer + supporting_premises + proof_steps + original question + premises-NL  

**Prompt template:**
```
System: You are an educational AI assistant. Given a proven answer and the reasoning steps,
write a clear, concise explanation in English. The explanation must:
- State which premises were used
- Show the logical chain step by step
- Conclude with the final answer
- Be understandable to a university student

User:
Question: {question}
Premises used: {supporting_premises_text}
Proof steps: {proof_steps}
Answer: {answer}

Write the explanation:
```

---

### Luồng Type 2 — Physics Problems

**Input:** `question` (str) only — không có premises, không có ảnh

#### Bước 1: Physics Parser Agent

**Model:** LLM ≤ 8B  
**Nhiệm vụ:** Trích xuất các đại lượng đã cho và xác định công thức cần dùng

**Prompt template:**
```
System: You are a physics problem parser. Extract:
1. Given values (variable name, value, unit)
2. Unknown variable to find
3. Physics domain (circuits / electrostatics / other)
4. Relevant formulas needed
Return ONLY valid JSON, no explanation.

User: {question}

Expected JSON format:
{
  "given": [{"var": "C", "value": 100, "unit": "μF"}, {"var": "U", "value": 30, "unit": "V"}],
  "find": {"var": "E", "unit": "J"},
  "domain": "electrostatics",
  "formulas": ["E = 0.5 * C * U^2"]
}
```

#### Bước 2: Symbolic Math Solver — SymPy

**Tool:** `sympy` (Python package)  
**Nhiệm vụ:** Giải hệ phương trình hoặc tính toán theo công thức đã trích xuất

```python
from sympy import symbols, solve, Rational
from sympy.physics.units import convert_to, farad, volt, joule

def solve_physics(parsed: dict) -> dict:
    """
    1. Convert units về SI (μF → F, kΩ → Ω, ...)
    2. Substitute given values vào formula
    3. Solve for unknown
    Returns: { "answer": "0.045", "unit": "J", "steps": [...] }
    """
    ...
```

**Unit conversion table thường gặp:**
```python
UNIT_CONVERSIONS = {
    "μF": 1e-6, "mF": 1e-3,           # Capacitance
    "kΩ": 1e3,  "MΩ": 1e6,            # Resistance
    "mA": 1e-3, "μA": 1e-6,           # Current
    "kV": 1e3,  "mV": 1e-3,           # Voltage
    "mW": 1e-3, "kW": 1e3, "MW": 1e6, # Power
    "mJ": 1e-3, "kJ": 1e3,            # Energy
}
```

#### Bước 3: CoT Builder

**Nhiệm vụ:** Xây dựng chuỗi Chain-of-Thought từ các bước giải của SymPy

```python
def build_cot(parsed: dict, solver_steps: list[str]) -> list[str]:
    """
    Sinh ra list CoT steps dạng:
    [
      "Step 1: Identify given values: C = 100 μF = 1×10⁻⁴ F, U = 30 V",
      "Step 2: Recall formula for energy stored in capacitor: E = ½CV²",
      "Step 3: Substitute values: E = 0.5 × (1×10⁻⁴) × (30)² = 0.045 J",
      "Step 4: Final answer: E = 45 mJ"
    ]
    """
    ...
```

---

### Response Builder — Đóng gói API Response

Gom kết quả từ cả 2 luồng và trả về đúng schema:

```python
def build_response(track_result: dict) -> dict:
    response = {
        # Mandatory
        "answer": track_result["answer"],
        "explanation": track_result["explanation"],
    }
    # Optional — thêm nếu có
    if track_result.get("fol"):
        response["fol"] = track_result["fol"]
    if track_result.get("cot"):
        response["cot"] = track_result["cot"]
    if track_result.get("premises"):
        response["premises"] = track_result["premises"]
    if track_result.get("confidence"):
        response["confidence"] = track_result["confidence"]
    return response
```

> ⚠️ **Không bao giờ trả về field `idx`** — field này không có trong API schema chính thức của EXACT 2026.

---

### Fallback Strategy (quan trọng)

Mọi bước trong pipeline đều phải có fallback để API không bao giờ trả về lỗi:

```
Z3 parse error / timeout
    → RAG retrieval trên premises-NL
    → LLM reasoning với full context
    → Trả về answer + explanation (không có FOL)

SymPy solve failure
    → LLM tự tính toán với CoT prompt
    → Đánh dấu confidence thấp (0.5)

LLM generation error
    → Retry 1 lần với simplified prompt
    → Trả về answer = "Unable to determine", explanation = error message
```

---

## Hướng tiếp cận 2: Multi-Task Fine-Tuning với Mixture-of-Experts (MoE)

**Triết lý:** "Đào tạo một mô hình duy nhất trở thành chuyên gia cho nhiều tác vụ thông qua việc chia nhỏ mạng nơ-ron."

> ⚠️ **Correction từ bản gốc:** Dataset Type 2 là text-only, không có ảnh mạch điện. Không cần Vision-Language Model (VLM). Bỏ Vision Agent (Qwen-VL / LLaVA).

### Kiến trúc tổng thể

```
HTTP Request
    │
    ▼
┌──────────────────────────────────────────┐
│         Single Fine-Tuned LLM            │
│    (Base: Qwen2.5 7B / LLaMA 3.1 8B)    │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     Internal MoE Router          │   │
│  │  Token → Expert 1 | Expert 2     │   │
│  └──────────────────────────────────┘   │
│                                          │
│  Expert 1: Logic & Policy Reasoning      │
│  Expert 2: Physics & Math Computation    │
└──────────────────────┬───────────────────┘
                       │
                       ▼
        JSON { answer, explanation, cot, ... }
                       │
                       ▼
              ┌────────────────┐
              │ Answer Verifier │  (heuristic check)
              └────────────────┘
                       │
                       ▼
                 HTTP Response
```

### Data Synthesis — Chuẩn bị dữ liệu fine-tuning

**Định dạng chuẩn cho mỗi training sample:**

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an explainable educational QA assistant. Always respond in valid JSON with fields: answer, explanation, cot (list of steps), premises (list of rules used), confidence (float)."
    },
    {
      "role": "user",
      "content": "Question: {question}\nPremises: {premises_nl_or_empty}"
    },
    {
      "role": "assistant",
      "content": "{\"answer\": \"B\", \"explanation\": \"...\", \"cot\": [\"Step 1: ...\"], \"premises\": [\"...\"], \"confidence\": 0.95}"
    }
  ]
}
```

**Nguồn dữ liệu cần khai báo (bắt buộc theo rules):**
- Training data chính thức từ EXACT 2026
- Bất kỳ dataset bổ sung nào phải ghi vào solution description

### Fine-Tuning với QLoRA

```python
# Cấu hình QLoRA gợi ý
qlora_config = {
    "r": 16,                    # rank
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
    "bits": 4,                  # 4-bit quantization
    "task_type": "CAUSAL_LM"
}

training_args = {
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "warmup_ratio": 0.03,
    "lr_scheduler_type": "cosine",
    "output_dir": "./checkpoints"
}
```

### Answer Verifier — Heuristic Checks (bắt buộc có)

Đây là lớp kiểm tra **sau khi model sinh output** để giảm hallucination số học:

```python
def verify_answer(question: str, raw_output: dict) -> dict:
    """
    Các kiểm tra heuristic:
    1. Nếu answer là số: parse và kiểm tra magnitude hợp lý
       (điện trở không âm, năng lượng không âm, v.v.)
    2. Nếu answer là MCQ: phải là A/B/C/D
    3. Nếu answer là Yes/No/Uncertain: phải là một trong 3
    4. Nếu confidence < 0.6: đánh dấu cần review
    """
    answer = raw_output.get("answer", "")

    # Check MCQ format
    if is_mcq_question(question):
        if answer not in ["A", "B", "C", "D"]:
            raw_output["answer"] = extract_letter_from_text(answer)
            raw_output["confidence"] = min(raw_output.get("confidence", 1.0), 0.7)

    # Check numeric answer sanity
    if is_numeric_answer(answer):
        value = parse_numeric(answer)
        if value < 0 and "resistance" in question.lower():
            raw_output["confidence"] = 0.3  # resistance không thể âm

    return raw_output
```

### Inference với vLLM

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="./checkpoints/final",
    max_model_len=4096,
    tensor_parallel_size=1,   # tăng nếu có nhiều GPU
    dtype="float16"
)

sampling_params = SamplingParams(
    temperature=0.1,           # thấp để output ổn định, deterministic hơn
    max_tokens=1024,
    stop=["</s>", "<|end|>"]
)
```

---

## Điểm chung cần implement cho cả 2 hướng

### API Endpoint (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    question: str
    premises: list[str] = []   # empty list nếu Type 2

class QueryResponse(BaseModel):
    answer: str
    explanation: str
    fol: str | None = None
    cot: list[str] | None = None
    premises: list[str] | None = None
    confidence: float | None = None

@app.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest):
    try:
        result = pipeline.run(request.question, request.premises)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Logging — Bắt buộc để debug

```python
import logging, json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exact2026")

def log_request(question: str, query_type: str, result: dict):
    logger.info(json.dumps({
        "question": question[:100],
        "type": query_type,
        "answer": result.get("answer"),
        "confidence": result.get("confidence"),
        "has_fol": bool(result.get("fol")),
        "has_cot": bool(result.get("cot")),
    }))
```

### Environment & Dependencies

```
# requirements.txt
fastapi>=0.110.0
uvicorn>=0.29.0
z3-solver>=4.13.0          # Hướng 1
sympy>=1.12                # Hướng 1
transformers>=4.40.0
peft>=0.10.0               # QLoRA
bitsandbytes>=0.43.0       # 4-bit quantization
vllm>=0.4.0                # Hướng 2, inference nhanh
langchain>=0.1.0
sentence-transformers>=2.7.0
faiss-cpu>=1.8.0
```

---

## Notes for the Agent

- **Không dùng field `idx`** ở bất kỳ đâu trong codebase — field này không tồn tại trong API schema
- **Không gọi bất kỳ external LLM API nào** (OpenAI, Anthropic, Google) — vi phạm rules dẫn đến disqualification
- Luôn wrap LLM calls trong try/except — API endpoint không được phép crash
- Type 2 không có premises → `premises` field trong request sẽ là list rỗng `[]`
- Khi sinh JSON từ LLM, luôn dùng `json.loads()` với error handling, không dùng `eval()`
- `answer` và `explanation` là **bắt buộc** — không bao giờ trả response thiếu 2 field này
- Với Type 2, đơn vị (unit) phải đi kèm với answer số học trong explanation, dù API chỉ nhận `answer` dạng string

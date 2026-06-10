# 🤖 LLM Reasoning & Prompt Engineering

> **Model:** Qwen 2.5 7B Instruct (GGUF)  
> **Nhiệm vụ:** Chain-of-Thought (CoT) reasoning, NL Explanation Generation, Fallback khi Z3 fail.

---

## 1. Chiến Lược Kích Hoạt Suy Luận (Prompting Strategies)

### 1.1 Step-aware Verification Prompt (Safe-like)

Dùng cho việc lấy Explanation (P2) sau khi Z3 đã giải xong (biết trước đáp án).

```python
EXPLANATION_PROMPT = """
You are an expert logician. Given a set of premises, a question, and the mathematically verified correct answer, explain step-by-step how to derive the answer from the premises.

PREMISES (Natural Language):
{premises_nl}

PREMISES (First-Order Logic):
{premises_fol}

QUESTION:
{question}

VERIFIED ANSWER: {answer}

REQUIRED EXPLANATION FORMAT:
1. State the relevant premises used (refer to them by their numbers, e.g., Premise 1, Premise 5).
2. Show the step-by-step logical deduction. Use Modus Ponens, Modus Tollens, or Transitivty where applicable.
3. Conclude by confirming why the verified answer is correct.

Limit your explanation to 3-5 concise sentences. Be precise and logical.
"""
```

### 1.2 Chain-of-Thought with Logic Tree (Z3 Fallback)

Dùng khi Z3 timeout hoặc fail (đóng vai trò solver).

```python
COT_REASONING_PROMPT = """
You are an expert AI reasoning system. Solve the following logical deduction problem step-by-step.

PREMISES:
{premises_nl}

QUESTION:
{question}
{options}

REASONING STEPS:
1. Identify the core facts (premises without conditions).
2. Identify the rules (if-then statements).
3. Apply rules to facts to derive new information (Forward Chaining). List each derived fact and the premises used.
4. If the question asks to verify a statement, check if it matches your derived facts or contradicts them.
5. If it's multiple choice, evaluate each option against the derived facts.

Final Answer Format:
Answer: [A/B/C/D or Yes/No/Unknown]
"""
```

### 1.3 LLM-as-a-Judge (Self-Evaluation)

Dùng để đánh giá độ tốt của Explanation trước khi output (cải thiện điểm P2).

```python
EVALUATION_PROMPT = """
Evaluate the following explanation for a logical reasoning question.

Question: {question}
Correct Answer: {answer}
Explanation to Evaluate: {explanation}

Check the following criteria:
1. Does it explicitly mention the premise numbers used? (e.g., Premise 1, Premise 4)
2. Is the logical chain unbroken from premises to conclusion?
3. Is it concise (under 5 sentences)?

If all criteria are met, output "PASS". Otherwise, output "FAIL" and provide a corrected, concise explanation.
"""
```

---

## 2. LLM Pipeline Integration

### 2.1 The Two-Phase Reasoning Pipeline

1. **Phase 1: Fast Symbolic Check (Z3)**
   - Nếu Z3 thành công → có `answer` và `proof_trace` (từ Logic Tree).
   - Truyền `answer` + `proof_trace` vào LLM bằng `EXPLANATION_PROMPT` để sinh NL text.
   - *Ưu điểm:* Zero hallucination cho câu trả lời, LLM chỉ đóng vai trò "dịch giả" từ proof sang NL.

2. **Phase 2: LLM Fallback (khi Z3 fail)**
   - Dùng `COT_REASONING_PROMPT`.
   - Lấy đáp án trực tiếp từ LLM.
   - Thêm câu `[Fallback] ` vào explanation để dễ debug.

### 2.2 Tích hợp Llama-cpp-python

```python
from llama_cpp import Llama

class LLMReasoner:
    def __init__(self, model_path: str, n_ctx: int = 4096, n_gpu_layers: int = -1):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers, # Offload to GPU
            verbose=False
        )
    
    def generate_explanation(self, premises, question, answer, trace=None):
        # Format the prompt
        prompt = EXPLANATION_PROMPT.format(...)
        
        # Call Qwen 2.5
        output = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are a precise logic assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temp for logic
            max_tokens=256,
            stop=["\n\n"]
        )
        return output['choices'][0]['message']['content'].strip()
```

---

## 3. Tối Ưu Hóa LLM (Cho Qwen 2.5 7B)

1. **Temperature:** Đặt ở mức `0.1` hoặc `0.0`. Logical reasoning cần deterministic, không cần creativity.
2. **System Prompt:** Qwen 2.5 tuân thủ System Prompt rất tốt. Luôn khai báo rõ vai trò ("expert logician") và định dạng output.
3. **Context Window:** Dataset có sample max 36 premises. Tokenize NL và FOL premises tốn khoảng 500-1000 tokens. Set `n_ctx=2048` hoặc `4096` là an toàn.
4. **JSON Output:** Có thể dùng `response_format={"type": "json_object"}` của Qwen để ép output trả về dict có key `explanation` và `answer` để dễ parse.
5. **Robust Answer Extraction (Xử lý định dạng Markdown):** Khi trả về đáp án, các model LLM thường tự động thêm các ký tự markdown như in đậm (`**Answer:** **A**`). Do đó, file `src/llm/prompt_templates.py` sử dụng các biểu thức Regex hỗ trợ nhận diện linh hoạt các thẻ markdown và bỏ qua phân biệt hoa thường (Case-Insensitive) nhằm tránh việc không trích xuất được đáp án. Đồng thời, hàm gọi LLM được cấu hình để log raw response bằng `logger.debug` giúp dễ dàng gỡ lỗi khi format sinh ra bị sai lệch.
6. **Z3 MCQ Code Generation — Check Tất Cả Options:** Nguyên nhân gốc rễ (#1) khiến hệ thống sai là LLM chỉ sinh Z3 code kiểm tra **1 option** thay vì **cả 4 options A/B/C/D**, đồng thời ánh xạ sai predicates (ví dụ: Option A nói `¬O(x) → ¬WT(x)` nhưng code check `¬CR(x) → ¬PEP8(x)`). Prompt `Z3_CODE_GENERATION_PROMPT` đã được thiết kế lại hoàn toàn với **2 skeleton riêng biệt** (Yes/No và MCQ). Skeleton MCQ yêu cầu bắt buộc kiểm tra tất cả 4 options bằng vòng lặp push/pop với `Not(ForAll([x], option_expr))` và in ra option entailed đầu tiên. Các IMPORTANT RULES nhấn mạnh: (a) phải check TẤT CẢ options, (b) phải dùng ForAll, (c) phải ánh xạ đúng predicate names.
7. **Question-Aware CoT Reasoning — Xử lý "fewest premises":** Nguyên nhân gốc rễ (#3, nghiêm trọng nhất) là CoT Prompt bước 5 chỉ nói chung chung "Select the option that is logically supported" — khiến LLM 7B bỏ qua ràng buộc "fewest premises" trong câu hỏi dù đã nhận diện đúng cả A lẫn C là hợp lệ. Prompt `COT_MCQ_PROMPT` đã được bổ sung: (a) **Few-Shot Example 2** chứng minh cách đếm premises cho mỗi option và chọn option ít nhất, (b) **Bước 5 mới** liệt kê rõ các tiêu chí ("fewest premises" → chọn ít nhất, "strongest conclusion" → chọn mạnh nhất, "correct" → chọn bất kỳ option hợp lệ), (c) **Bước 4 mới** yêu cầu cho mỗi option phải ghi rõ cần bao nhiêu premises.
8. **Z3 Refinement MCQ-Aware:** Nguyên nhân gốc rễ (#2) là khi Z3 code thất bại, prompt Refinement chỉ truyền error message chung chung (`"Execution returned no output"`) mà không chỉ ra lỗi cụ thể cho MCQ. Prompt `Z3_REFINEMENT_PROMPT` mới bổ sung danh sách **COMMON MISTAKES TO FIX** gồm 5 lỗi thường gặp: thực thể chưa khai báo, chỉ check 1 option, thiếu ForAll, sai tên predicate, dùng NOT() thay vì Not().
9. **Symbolic Hinting for CoT (Neo đậu tri thức):** Khi Z3 gặp lỗi và rơi vào nhánh Fallback (Chain-of-Thought), LLM sẽ không phải mò mẫm tự suy luận từ đầu. Hệ thống tự động trích xuất các sự thật đã được Logic Tree chứng minh thông qua cơ chế `Forward Chaining` và bơm ngược lại vào Prompt làm **Guaranteed True Facts** (`hints`).
10. **Quản Lý VRAM RTX 3050 (4GB):** Khi chạy nội suy cục bộ trên card RTX 3050 4GB, tham số `--gpu-layers` bắt buộc phải cấu hình ở mức trung bình (ví dụ: `--gpu-layers 10`) để tránh lỗi tràn GPU memory. Nếu VRAM dư dả (như trên Colab T4 16GB), tham số này có thể đặt ở mức tối đa `-1`.

---

## 4. Xử Lý Đáp Án "Unknown" và Chống "Yes Bias"

### 4.1 Hỗ Trợ Đáp Án `Unknown`

Từ phiên bản v2.0, cả hai prompt `COT_MCQ_PROMPT` và `COT_YESNO_PROMPT` đều hỗ trợ đáp án `Unknown`.

**Khi nào trả lời Unknown?**
- **MCQ:** Khi không có option nào có thể suy luận được từ premises. Điều này thường xảy ra khi premises chỉ chứa rules (if-then) mà không có ground facts cụ thể.
- **Yes/No:** Khi statement không thể chứng minh đúng hay sai — ví dụ premises chỉ có rules mà không có instance nào để kích hoạt chain.

**Cơ chế:**
1. Few-shot example thứ 3 trong MCQ prompt minh họa rõ khi nào `Unknown` là hợp lệ.
2. Few-shot example thứ 2 trong YN prompt (Insufficient Information) minh họa trường hợp thiếu ground facts.
3. Bước 7 trong MCQ instructions và Bước 5 trong YN instructions định nghĩa rõ decision rules.

### 4.2 Chống "Yes Bias" cho Chuỗi Logic Bị Đứt

LLM 7B có xu hướng **"Yes bias"** — khi thấy chuỗi suy luận dài (4-5 bước đúng), nó tự tin nói "Yes" mà không kiểm tra bước cuối cùng.

**Giải pháp đã triển khai:**

1. **Few-shot example "Broken Chain"** trong `COT_YESNO_PROMPT`:
   - Minh họa chuỗi A→B→C→D nhưng thiếu D→E.
   - LLM thấy ví dụ cụ thể về cách đánh dấu ✓/✗ từng link.

2. **Bước 4 (Chain Completeness Check):**
   - Yêu cầu LLM liệt kê TỪNG link: `A -> B (Premise N) ✓`
   - Nếu BẤT KỲ link nào missing: `A -> B ← MISSING ✗` → Answer: No.

3. **Từ khóa trigger:** Khi câu hỏi chứa "pathway", "chain", "causal chain", "leads to" → tự động kích hoạt kiểm tra completeness.

### 4.3 Cải thiện Logic Tree Parser

Logic Tree parser đã được nâng cấp để xử lý các cú pháp FOL phức tạp:

| Cú pháp | Trước | Sau |
|---------|-------|-----|
| `∀x(¬P(x) → ¬Q(x))` | ❌ Parse fail | ✅ RuleNode(NOT_P → NOT_Q) |
| `¬depleted_fund` | ❌ Parse fail | ✅ FactNode(depleted_fund, negated=True) |
| `∃x P(x)` | ⚠️ Inconsistent | ✅ FactNode (treated as existential witness) |
| `available_mentors` | ❌ Parse fail | ✅ FactNode(available_mentors, args=[]) |
| `(time_diff(A, B) = 0.5)` | ❌ Parse fail | ✅ FactNode(time_diff, [A, B, 0.5]) |

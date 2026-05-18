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

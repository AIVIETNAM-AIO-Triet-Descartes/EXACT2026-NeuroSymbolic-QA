# Neuro-Symbolic QA: Advanced Hybrid Strategies (EXACT 2026)

Để đưa hệ thống Neuro-Symbolic QA bứt phá từ 85% lên ngưỡng >95% Accuracy cho cuộc thi EXACT 2026, chúng ta cần chuyển từ mô hình "Fallback tuần tự" sang kiến trúc **Hybrid (Lai ghép) đa luồng**. Dưới đây là các chiến lược kỹ thuật cốt lõi cần triển khai tiếp theo.

## 1. Chiến lược Lai ghép Đồng thuận (Consensus Hybridization)

Thay vì thử Z3 trước rồi mới đến CoT (Fallback), chúng ta sẽ chạy song song các luồng và dùng cơ chế bỏ phiếu (Voting/Tie-breaker).

*   **CoT + Logic Tree Cross-Check:** 
    *   **Cách làm:** Chạy song song `llm_cot` và `Logic Tree`. 
    *   **Đồng thuận:** Nếu cả hai cùng ra một đáp án, đẩy Confidence lên 1.0 (Chắc chắn đúng).
    *   **Xung đột:** Nếu CoT ra A, nhưng Logic Tree ra B, hệ thống sẽ tự động tạo một prompt *"Reflection"* (phản tư): *"Logic hình thức cho ra đáp án B vì luật X bị vi phạm, nhưng bạn lập luận là A. Hãy kiểm tra lại lập luận của bạn."* LLM sẽ tự sửa lỗi của chính nó.
*   **Self-Consistency (CoT Majority Vote):**
    *   Với các câu hỏi siêu khó, gọi hàm `llm_cot` 3 lần độc lập (với temperature = 0.4). Sau đó lấy đáp án xuất hiện nhiều nhất (Majority Vote). Kỹ thuật này đã được chứng minh giúp tăng độ chính xác của LLM lên 10-15%.

## 2. Nâng cấp Few-Shot Prompting cho Z3

Hiện tại `llm_z3` đang sinh code dựa trên (Zero-shot) hướng dẫn. Qwen 7B rất dễ bị "trôi" (hallucinate) nếu không có ví dụ mẫu.
*   **Giải pháp:** Bổ sung **In-Context Learning (Few-Shot)** vào `Z3_CODE_GENERATION_PROMPT`.
*   **Cách làm:** Chèn 2 ví dụ (Q&A) đã được giải hoàn hảo bằng Z3 vào prompt (một câu hỏi dạng MCQ, một câu hỏi dạng Yes/No). Khi LLM nhìn thấy format chuẩn, tỷ lệ lỗi cú pháp (Syntax/NameError) sẽ giảm tiệm cận về 0, ngay cả với mô hình 7B.

## 3. Cải tiến Động cơ Suy luận Logic Tree (Xử lý Phủ định)

Trong file log, ta thấy Logic Tree sai 2 câu vì cảnh báo: `Blocked rule... Antecedent negated`. Logic Tree hiện tại chỉ giỏi xử lý logic khẳng định (Positive Logic).
*   **Giải pháp:** Nâng cấp Forward Chaining engine để hỗ trợ **Tri-state Logic (True / False / Unknown)**.
*   Lưu trữ các facts dưới dạng `Literal(name, is_positive=True/False)`. Khi đó, các luật chứa hàm phủ định `Not()` sẽ được đánh giá chính xác mà không bị hệ thống tự động block. Điều này sẽ đẩy Accuracy của Logic Tree lên mức hoàn hảo.

## 4. Multi-Agent Delegation (Định tuyến Mô hình Chuyên biệt)

Nếu môi trường chạy (Colab/Local) cho phép load nhiều adapter hoặc sử dụng nhiều mô hình:
*   **Reasoning Agent:** Dùng Qwen 2.5 7B (hoặc Llama 3 8B) chuyên xử lý `llm_cot` và sinh Natural Language.
*   **Coding Agent:** Dùng một mô hình chuyên code siêu nhỏ (như `DeepSeek-Coder-1.3B` hoặc `Qwen2.5-Coder-7B`) chỉ để làm đúng một việc duy nhất: Dịch FOL sang Z3 Python Code. Mô hình coder sẽ KHÔNG bao giờ sinh ra toán tử `>>` hay quên khai báo biến như mô hình ngôn ngữ thông thường.

## 5. Xử Lý Đáp Án "Unknown" (MỚI — v2.0)

### Vấn đề

Dataset EXACT 2026 chứa nhiều câu hỏi có đáp án `Unknown` — cả MCQ lẫn Yes/No. Điều này xảy ra khi:
- Premises chỉ chứa rules (if-then) mà **không có ground facts cụ thể** để kích hoạt suy luận.
- Không đủ thông tin để kết luận bất kỳ option nào là đúng.

### Triển khai

| Thành phần | Thay đổi |
|------------|----------|
| `COT_MCQ_PROMPT` | Cho phép trả lời `Unknown` kèm few-shot example (Example 3) |
| `COT_YESNO_PROMPT` | Cho phép trả lời `Unknown` kèm few-shot example (Insufficient Information) |
| `ANSWER_EXTRACT_PATTERNS` | Regex đã hỗ trợ capture `Unknown` |
| `_extract_answer()` | Normalize `unknown` → `Unknown` |

### Khi nào LLM nên trả lời Unknown?

1. **MCQ:** Tất cả options đều yêu cầu ground facts nhưng premises chỉ có rules.
2. **Yes/No:** Statement không thể chứng minh true hay false — thiếu facts.
3. **Combination:** Chuỗi logic tồn tại nhưng thiếu trigger facts.

## 6. Chống "Yes Bias" trên Chuỗi Logic Bị Đứt (MỚI — v2.0)

### Vấn đề

LLM 7B có xu hướng trả lời "Yes" khi thấy chuỗi suy luận dài (4-5 bước đúng), mà **không kiểm tra** bước cuối cùng có tồn tại không. Ví dụ:

```
Q: Is there a causal chain from A to Z?
Premises: A→B, B→C, C→D  (no D→Z!)
LLM: "Yes" ← WRONG! Chain is BROKEN.
```

### Giải pháp

1. **Few-shot "Broken Chain" example** trong `COT_YESNO_PROMPT` — minh họa cụ thể cách phát hiện chain bị đứt.
2. **Chain Completeness Check (Bước 4 mới):**
   - Khi câu hỏi chứa từ khóa: "pathway", "chain", "causal chain", "leads to"
   - LLM PHẢI liệt kê từng link: `A → B (Premise N) ✓` hoặc `A → B ← MISSING ✗`
   - Nếu BẤT KỲ link nào missing → Answer: No
3. **Kết quả dự kiến:** Fix 8 câu sai trong batch 30-50 (từ 49% lên ~71% riêng loại lỗi này).

## 7. Cải Thiện Logic Tree Parser (MỚI — v2.0)

### Vấn đề

Parser `FOLPremiseParser` không xử lý được nhiều cú pháp FOL phổ biến trong dataset, dẫn đến "Could not parse" → 0 derived facts → LLM thiếu symbolic hints.

### Các pattern mới được hỗ trợ

| Pattern | Ví dụ | Trước | Sau |
|---------|-------|-------|-----|
| Negated antecedent rule | `∀x(¬P(x) → ¬Q(x))` | ❌ Skip | ✅ RuleNode(NOT_P → NOT_Q) |
| Bare atom (no parens) | `¬depleted_fund` | ❌ Skip | ✅ FactNode(negated) |
| Bare positive atom | `available_mentors` | ❌ Skip | ✅ FactNode |
| Equality constraint | `(time_diff(A,B) = 0.5)` | ❌ Skip | ✅ FactNode |
| Existential facts | `∃x P(x)` with `Exists` keyword | ⚠️ Partial | ✅ Full support |

### Kết quả

Thay đổi parser giúp Logic Tree parse thêm 10-15 premises/sample → derive thêm facts → cung cấp symbolic hints tốt hơn cho LLM.

## Lộ trình triển khai (Next Steps)

### Đã triển khai (v2.0) ✅
1. ✅ Hỗ trợ đáp án `Unknown` cho cả MCQ và Yes/No prompt
2. ✅ Chống "Yes bias" bằng few-shot broken chain + chain completeness check
3. ✅ Cải thiện Logic Tree parser: bare atoms, negated antecedent rules, equality
4. ✅ Cập nhật docs

### Sắp triển khai (v2.1)
1. **(Ưu tiên cao):** Self-Consistency Majority Vote — gọi LLM 3 lần, lấy majority answer
2. **(Ưu tiên trung bình):** Tri-state Logic trong Forward Chaining — xử lý triệt để phủ định
3. **(Ưu tiên thấp):** Multi-Agent Delegation — routing mô hình theo loại task

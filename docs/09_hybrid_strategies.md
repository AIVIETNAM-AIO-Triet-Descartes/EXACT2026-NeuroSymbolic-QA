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

## Lộ trình triển khai (Next Steps)

Nếu bạn muốn tiếp tục tối ưu code ngay bây giờ, tôi đề xuất chúng ta nên bắt đầu với **Ưu tiên 1**:
1. **(Dễ nhất - Hiệu quả cao nhất):** Nâng cấp Prompt thêm **Few-Shot Examples** cho Z3.
2. **(Độ khó trung bình):** Cải tiến thuật toán Forward Chaining trong `logic_tree.py` để xử lý triệt để phép Phủ định (`Not`).
3. **(Nâng cao):** Viết lại hàm `_solve_question` trong `main.py` để chạy Cross-Check (CoT đối chiếu với Logic Tree) tạo ra cơ chế Self-Correction.

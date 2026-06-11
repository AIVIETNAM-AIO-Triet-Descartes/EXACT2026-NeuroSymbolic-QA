# 🎯 Evaluation & Scoring Strategy

> **Mục đích:** Tối ưu hóa điểm số cho cuộc thi EXACT 2026 dựa trên 3 tiêu chí cốt lõi.

---

## 1. Cơ Cấu Điểm Số (Scoring Matrix)

| Tiêu chí | Trọng số | Làm sao để lấy điểm tối đa? | Rủi ro mất điểm |
|:---|:---|:---|:---|
| **P1: Correctness** (Đáp án) | 50% | Z3 Solver phải hoạt động hoàn hảo. Cover được Yes/No/Unknown. | LLM hallucinate ra đáp án sai (nếu Z3 fail). |
| **P2: Explanation** (Giải thích) | 30% | Dùng prompt ép LLM output theo template: (1) Reference premises, (2) Step-by-step, (3) Conclusion. | Giải thích quá dài, lan man, không viện dẫn đúng ID của premise. |
| **P3: Reasoning/Depth** (Chiều sâu) | 20% | Xuất đúng mảng `idx` (những premises đã dùng). | Đoán bừa `idx` hoặc liệt kê toàn bộ premises. |

---

## 2. Chiến Lược Lấy Điểm P3 (Khó Nhất)

### Vấn đề:
Làm sao biết chính xác một conclusion được sinh ra từ những premises nào? (để build mảng `idx`).

### Giải pháp 1: Z3 Unsatisfiable Core (Khuyên dùng)
Khi Z3 trả về `unsat` (chứng minh được), Z3 có khả năng chỉ ra tập hợp tối thiểu các assertions gây ra unsat core.

```python
def get_used_premises_z3(ctx: Z3Context, goal: z3.ExprRef):
    solver = ctx.solver
    solver.push()
    
    # Add premises as named assertions to track them
    trackers = []
    for i, expr in enumerate(ctx.assertions):
        p_name = z3.Bool(f'p_{i+1}')
        trackers.append(p_name)
        solver.add(z3.Implies(p_name, expr))
        
    solver.add(z3.Not(goal))
    
    # Check with tracked variables
    res = solver.check(*trackers)
    
    if res == z3.unsat:
        core = solver.unsat_core()
        idx_list = [int(str(c).split('_')[1]) for c in core]
        return sorted(idx_list)
    
    return []
```

### Giải pháp 2: Logic Tree Path Tracking
Dùng thuật toán Forward Chaining (đã định nghĩa ở file 03), theo vết (trace back) từ Goal Node lên Fact Nodes để gom tất cả ID của rules và facts đi qua.

---

## 3. Chiến Lược Lấy Điểm P2 (Explanation)

Hạn chế của LLM (đặc biệt là model 7B) là hay nói lan man.

**Template bắt buộc:**
> "By Premise [X], [fact 1]. By Premise [Y], [rule]. Applying Modus Ponens, [intermediate deduction]. Finally, combining with Premise [Z], we conclude [Answer]."

**Cách ép LLM:**
Truyền `idx` (ví dụ `[1, 7, 10]`) vào System Prompt:
*"You MUST ONLY use information from Premise 1, Premise 7, and Premise 10 in your explanation. Do not mention any other premises."*

---

## 4. Chiến Lược Fallback (Giảm thiểu rủi ro P1)

1. **Z3 Timeout (30s) →** LLM CoT Prompt
2. **LLM Parser fail (không trích xuất được A/B/C/D) →** Regex rule-based text matching.
3. **Mâu thuẫn giữa NL và FOL trong dataset →** LUÔN TIN FOL. Vì các giám khảo (đề thi) thường sinh FOL bằng tool, NL là human viết có thể sai sót. Đưa FOL vào Z3 là nguồn "chân lý" (ground truth).

# 📊 Phân Tích Chi Tiết Dataset - Logic-Based Educational Queries

> **File nguồn:** `Logic_Based_Educational_Queries.json`  
> **Tổng mẫu:** 411 samples | **~808 questions**

---

## 1. Cấu Trúc Mỗi Sample

Mỗi sample trong JSON có cấu trúc:

```json
{
  "idx": [[1, 2, 3], [1, 2, 4, 5]],
  "premises-FOL": ["ForAll(x, P(x) → Q(x))", ...],
  "premises-NL": ["If a student...", ...],
  "questions": ["Which conclusion follows?...", "Does X hold?"],
  "answers": ["A", "Yes"],
  "explanation": ["Premise 1 states...", "The requirement..."]
}
```

### 1.1 Giải Thích Các Field

| Field | Kiểu | Mô tả |
|:---|:---|:---|
| `idx` | `List[List[int]]` | **Chỉ số premises cần dùng** cho từng câu hỏi (1-indexed) |
| `premises-FOL` | `List[str]` | Các tiền đề dưới dạng **First-Order Logic** |
| `premises-NL` | `List[str]` | Các tiền đề dưới dạng **ngôn ngữ tự nhiên** (English) |
| `questions` | `List[str]` | Danh sách câu hỏi (thường 2 câu/sample) |
| `answers` | `List[str]` | Đáp án đúng (A/B/C/D hoặc Yes/No/Unknown) |
| `explanation` | `List[str]` | Giải thích chi tiết cho mỗi đáp án |

> **GHI CHÚ VỀ `idx`:**
> - `idx[i]` chứa danh sách index premises cần thiết cho `questions[i]`
> - Index là **1-based** (bắt đầu từ 1)
> - Dùng để validate: nếu hệ thống chọn đúng premises → tăng điểm P3
> - Ví dụ: `idx = [[1], [7, 10]]` → Q1 chỉ cần premise 1, Q2 cần premise 7 và 10

---

## 2. Phân Loại Chi Tiết Câu Hỏi

### 2.1 Loại 1: Multiple Choice (MCQ) - 346 câu

**Đặc điểm:** Câu hỏi kèm 4 đáp án A/B/C/D

```
"Which conclusion follows with the fewest premises?
A. If a Python project is not optimized, then it is not well-tested
B. If all Python projects are optimized, then all Python projects are well-structured
C. If a Python project is well-tested, then it must be clean and readable
D. If a Python project is not optimized, then it does not follow PEP 8 standards"
```

**Chiến lược giải:**
1. Parse từng option thành FOL
2. Với mỗi option, thử chứng minh bằng Z3 (satisfiability check)
3. Chọn option valid với ít premises nhất (nếu hỏi "fewest")
4. Hoặc chọn "strongest conclusion" (kéo theo nhiều nhất)

### 2.2 Loại 2: Yes/No - 416 câu

**Đặc điểm:** Câu hỏi dạng "Does X follow according to premises?"

```
"Does it follow that if all Python projects are well-structured, 
 then all Python projects are optimized, according to the premises?"
```

**Chiến lược giải:**
1. Parse statement cần kiểm tra thành FOL
2. Thêm vào Z3 cùng premises
3. Check: `premises ∧ ¬conclusion` → UNSAT = "Yes", SAT = "No"

### 2.3 Loại 3: Unknown - 43 câu

**Đặc điểm:** Không đủ thông tin để kết luận

```
"Based on the mission parameters, which scenario accurately describes 
 Luna's Mars expedition?"
→ Answer: "Unknown" (thiếu thông tin trong premises)
```

**Chiến lược giải:**
1. Thử cả proving và disproving
2. Nếu cả hai đều fail → "Unknown"
3. Logic: `premises ⊬ conclusion` VÀ `premises ⊬ ¬conclusion`

---

## 3. Phân Loại FOL Theo Độ Phức Tạp

### 3.1 Level 1: Propositional Logic (đơn giản)

```fol
∀x (UpdateEmail(x))                              # Atomic universal
∀x (UpdateEmail(x) → Paid(x))                    # Simple implication
∀x (¬PEP8(x) → ¬WT(x))                          # Contraposition
∃x (BP(x))                                       # Existential
```

**Đặc điểm:** Chỉ có `∀`, `∃`, `→`, `¬`  
**Z3 Translation:** Trực tiếp, dễ dàng

### 3.2 Level 2: Predicate Logic + Conjunction (trung bình)

```fol
ForAll(x, (completed_core_curriculum(x) ∧ passed_science_assessment(x)) 
  → qualified_for_advanced_courses(x))

ForAll(x, (awarded_honors_diploma(x) ∧ completed_community_service(x)) 
  → qualifies_for_scholarship(x))
```

**Đặc điểm:** Có `∧` trong antecedent, multi-predicate  
**Z3 Translation:** Cần parse conjunction correctly

### 3.3 Level 3: Arithmetic Constraints (nâng cao)

```fol
ForAll(x, ForAll(h, (clinical_hours(x, h) ∧ h ≥ 500) → advanced_practice(x)))
ForAll(x, (completed_courses(x) ≥ 5) → eligible_advanced(x))
clinical_hours(john, 600)
membership_duration(Alex) = 8
```

**Đặc điểm:** So sánh số (`≥`, `≤`, `=`), hàm trả về giá trị  
**Z3 Translation:** Cần `z3.Int()`, `z3.ArithRef`

### 3.4 Level 4: Nested Quantifiers + Transitivity (phức tạp)

```fol
ForAll(x, ForAll(d, (faculty_member(x) ∧ has_degree(x, d) ∧ higher(d, MSc)) 
  → teach_graduate(x)))
ForAll(a, ForAll(b, ForAll(c, (higher(a, b) ∧ higher(b, c)) → higher(a, c))))
```

**Đặc điểm:** Nested `ForAll`, transitivity rules, multi-sort  
**Z3 Translation:** Cần `z3.Function`, closure computation

### 3.5 Level 5: Complex Multi-Step Chains (rất phức tạp)

```fol
# 28-36 premises, chuỗi suy luận 5-10 bước
ForAll(a, (training(a) ∧ simulations(a)) → clearance(a))
ForAll(a, (clearance(a) ∧ safety_audit(vehicle(a))) → approved(a))
ForAll(a, (approved(a) ∧ trajectory(a)) → departs(a))
# ... kéo dài nhiều bước
```

**Đặc điểm:** Chuỗi dài, nhiều biến, negation trong premises  
**Z3 Translation:** Cần systematic approach, có thể timeout

---

## 4. Thống Kê Theo Domain

Dataset cover các domain giáo dục:

| Domain | Ví dụ |
|:---|:---|
| **Academic/University** | Graduation, scholarship, courses, GPA |
| **Faculty/HR** | PhD requirements, teaching qualification |
| **Medical/Nursing** | Clinical hours, prescribing rights |
| **Transportation** | Vehicle inspection, hazmat training |
| **Technology/CS** | PEP8, code testing, optimization |
| **Space/Science** | Mars expedition, astronaut training |
| **Gym/Membership** | Equipment use, trainer booking |

---

## 5. Pattern Nhận Dạng Cho Từng Loại Câu Hỏi

### 5.1 MCQ Pattern Detection

```python
def is_mcq(question: str) -> bool:
    return bool(re.search(r'\nA[\.\)]', question))

def extract_options(question: str) -> dict:
    pattern = r'([A-D])[\.\)]\s*(.+?)(?=\n[A-D][\.\)]|\Z)'
    return {m.group(1): m.group(2).strip() 
            for m in re.finditer(pattern, question, re.DOTALL)}
```

### 5.2 Yes/No Pattern Detection

```python
def is_yes_no(question: str) -> bool:
    patterns = [
        r'^Does\s',
        r'^Can\s',
        r'^Is\s',
        r'^Do\s',
        r'according to the premises\?',
        r'based on .+ premises\?'
    ]
    return any(re.search(p, question, re.IGNORECASE) for p in patterns)
```

### 5.3 Phân Biệt Yes/No vs Unknown

```python
def determine_answer_type(premises_fol, question, options=None):
    """
    1. Thử prove conclusion → nếu SAT: "Yes"
    2. Thử prove ¬conclusion → nếu SAT: "No"  
    3. Nếu cả 2 fail → "Unknown"
    """
    pass
```

---

## 6. Xử Lý Edge Cases

### 6.1 Mâu thuẫn giữa FOL và NL

Một số samples có **sự không nhất quán** giữa `premises-FOL` và `premises-NL`:
- FOL dùng predicate khác với mô tả NL
- Thứ tự premises trong FOL khác NL

**Giải pháp:** Luôn ưu tiên `premises-FOL` cho symbolic reasoning, dùng `premises-NL` cho explanation generation.

### 6.2 Answer key không nhất quán

Phát hiện một số samples có answer key mâu thuẫn với explanation:
- Sample idx trỏ tới premises nhưng explanation reference premises khác
- Ví dụ: Answer "C" nhưng explanation chứng minh "A" là đúng

**Giải pháp:** Sử dụng Z3 verification để cross-check, nếu mâu thuẫn → tin Z3 proof.

### 6.3 Notation không đồng nhất

```
# Hai styles cùng tồn tại trong dataset:
"∀x (WT(x) → O(x))"                    # Unicode style
"ForAll(x, completed_courses(x) → ...)" # Text style
```

**Giải pháp:** Xem chi tiết tại [02_fol_normalizer.md](./02_fol_normalizer.md)

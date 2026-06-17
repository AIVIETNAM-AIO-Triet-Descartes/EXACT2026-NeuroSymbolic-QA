# Đề xuất cải tiến Pipeline Trích xuất dữ kiện và Formula RAG (Track 2)

Tài liệu này tổng hợp phân tích, phản biện và kế hoạch chi tiết để cải tiến kiến trúc trích xuất dữ kiện và truy xuất công thức (Formula RAG) cho Track 2.

---

## Review & Đánh giá (2026-06-16) — CẬP NHẬT SAU P0

### Kết quả sau khi hoàn thành Giai đoạn 0
Chạy `demo_type2.py --limit 100` (no LLM, Ollama offline): **85.2% accuracy** (46/54 evaluable). 44 FALLBACK, 8 WRONG.
Tăng từ baseline pre-P0 **83.6%** (46/55). P0 formulas mới (formula_054–060) đang contribute.

### Bug phát hiện trong P0: `_solve_multi_step` alias fallback sai
**Triệu chứng:** Accuracy giảm từ 83.6% → 47.8% ngay sau P0. 27 câu E_field electrostatics WRONG(100%).

**Root cause:** Code alias fallback thêm vào `_solve_multi_step` có 2 lỗi:
1. `for var, val in accumulated.items()` (inner loop) leak `val = <last given value>` ra ngoài scope
2. `return {"answer": f"{val:.6g}"}` chạy **unconditionally** trên iteration đầu tiên của alias loop khi alias không tìm thấy trong accumulated → trả về garbage value thay vì `None`

**Hệ quả:** Scalar solver trả về e.g. `E_field = 0.08` (giá trị `d_perp` từ given) thay vì `None` → vector_solver không được gọi (chỉ fallback khi `source == "llm_fallback"`).

**Fix:** Xóa unconditional return, rename `val` → `alias_val` trong alias block. File: `pipeline/type2/sympy_solver.py` lines 192–216.

---

## Review & Đánh giá (2026-06-15)

### Kết quả baseline hiện tại (pre-P0)
Chạy `demo_type2.py --limit 100` (no LLM): **83.6% accuracy** (46/55 evaluable). 43 FALLBACK, 9 WRONG.
Bottleneck thực sự: **extraction + symbol mismatch**, không phải retrieval scoring.

### Nhận xét tổng quan

**Phần 2.1 (Hybrid Retrieval / Symbol-IDF):** Đúng hướng về lý thuyết. IDF tôn vinh biến đặc trưng (`ε₀`, `λ`) và giảm noise từ biến phổ quát (`m`, `t`). Domain soft boost thay hard filter cũng hợp lý vì hard-filter hiện tại giết retrieval khi domain mismatch. Tuy nhiên với DB chỉ 53 formulas, IDF không có nhiều room để differentiate — **ROI thấp hơn dự kiến**.

**Phần 2.2 (Forward Chaining / Fixpoint Closure):** Giải quyết đúng vấn đề multi-step chain với intermediate variables. Tuy nhiên là rewrite lớn, risk cao. **Tiên quyết**: toàn bộ logic Closure phụ thuộc symbol consistency — nếu `symbol_registry` chưa xong thì Forward Chaining fail tương tự vì `I` vs `I_0`.

**Thứ tự ưu tiên sai** so với bottleneck thực tế. Cần fix symbol mismatch trước, retrieval scoring sau.

---

## 1. Vấn đề của hệ thống hiện tại

* **Cascade Failure ở Layer 1**: Việc hard-filter theo Domain khiến hệ thống bị kẹt nếu Classifier dự đoán sai domain, dẫn đến FAISS không thể tìm thấy công thức đúng.
* **Hạn chế của Jaccard thuần và Keyword Matching**: Các biến phổ biến (`m`, `t`, `v`) có thể làm loãng độ chính xác nếu chỉ đếm số lượng biến trùng khớp, trong khi các biến đặc trưng (`ε₀`, `λ`) lại mang thông tin định hướng (discriminative) mạnh hơn.
* **Điểm mù trong Multi-step Solver**: DFS chain builder hiện tại (`build_formula_chain`) ánh xạ tĩnh mỗi biến ở vế trái (LHS) với **chỉ một công thức duy nhất**. Nếu giải bài toán cần một công thức bắc cầu khác (vd: dùng $P = I^2R$ thay vì $P = UI$), chuỗi giải sẽ gãy. Ngoài ra, điều kiện `RHS known` là chưa đủ để quét hết các trường hợp phương trình 1 ẩn.
* **[MỚI — ROOT CAUSE] Symbol namespace không nhất quán**: 3 nguồn dữ liệu độc lập không đồng bộ nhau:
  - `physics_formulas.json` LHS: `formula_012` dùng `E = 0.5*C*U²` (capacitor energy), `formula_052` dùng `W = Q²/(2*C)` (cùng đại lượng, LHS khác)
  - `regex_extract.py` `_VERB_TARGET_MAP`: `"energy" → "E"`
  - `type2_classifier.py` `_detect_target_variable`: map riêng, lệch với regex
  
  Khi `find="E"` nhưng formula matched là `W = ...` → `solve(eq, E)` fail → LLM fallback dù DB có đúng công thức.

---

## 2. Các đề xuất cải tiến cốt lõi

### [TIÊN QUYẾT] Symbol Registry — Single Source of Truth

**Tạo `pipeline/type2/symbol_registry.py`** làm authoritative source cho toàn pipeline để giải quyết sự lệch pha ký hiệu giữa RAG DB, Regex và Classifier:

```python
# Canonical symbol cho mỗi đại lượng
CANONICAL = {
    "energy":               "W",       # Thống nhất năng lượng là W để tránh đụng E_field
    "capacitor_energy":     "W",
    "inductor_energy":      "W_L",
    "emf":                  "e",       # Thống nhất suất điện động là e nhỏ
    "electric_field":       "E_field",
    "impedance":            "Z",
    "inductive_reactance":  "Z_L",
    "capacitive_reactance": "Z_C",
}

# Alias map: canonical → tất cả ký hiệu có thể gặp trong formulas hoặc đề bài
ALIASES: dict[str, list[str]] = {
    "W":       ["W", "E", "W_C", "U_E"],
    "W_L":     ["W_L", "W", "E"],
    "e":       ["e", "EMF", "emf", "ε"],
    "E_field": ["E_field", "E", "E0"],
    "Z_L":     ["Z_L", "X_L"],
    "Z_C":     ["Z_C", "X_C"],
    "U":       ["U", "V"],
}

# Bản đồ lọc Alias theo Domain để giải quyết xung đột ý nghĩa của ký hiệu (Symbol Ambiguity)
# Ví dụ: Ký hiệu "E" có thể là Điện trường (electrostatics) hoặc Năng lượng (ac_circuits)
DOMAIN_ALIASES = {
    "electrostatics": {
        "E": "E_field",
    },
    "ac_circuits": {
        "E": "W",
    }
}

def get_aliases(symbol: str, domain: str = None) -> list[str]:
    """Lấy danh sách các ký hiệu thay thế an toàn dựa trên Domain của bài toán."""
    resolved_sym = symbol
    if domain and domain in DOMAIN_ALIASES:
        resolved_sym = DOMAIN_ALIASES[domain].get(symbol, symbol)
    return [resolved_sym] + ALIASES.get(resolved_sym, [])
```

**3 thay đổi đi kèm (thứ tự tăng dần risk):**

| Bước | File | Nội dung | Risk |
|------|------|----------|------|
| A | `sympy_solver.py` | Domain-aware Alias fallback khi `solve()` rỗng | Thấp |
| B | `physics_formulas.json` + rebuild FAISS | Normalize LHS → canonical + Tích hợp MD5 Drift Guard | Trung bình |
| C | `regex_extract.py`, `type2_classifier.py` | Import từ `symbol_registry` thay vì định nghĩa map riêng | Thấp |

**Bước A — alias fallback trong solver (~25 dòng):**
```python
from pipeline.type2.symbol_registry import get_aliases

def _solve_with_aliases(eq, find: str, sym_dict: dict, domain: str = None):
    # Lấy danh sách alias an toàn dựa trên domain để tránh xung đột E (điện trường) vs E (năng lượng)
    aliases = get_aliases(find, domain)
    for sym_name in aliases:
        sym = sym_dict.get(sym_name) or sp.Symbol(sym_name)
        result = sp.solve(eq, sym)
        if result:
            return result
    return []
```
Fix được `find="E"` + `formula_052` dùng `W` mà không bị nhầm sang cường độ điện trường.

**Bước B.2 — Rebuild FAISS & MD5 Drift Guard:**
* Tích hợp cơ chế tự động ghi nhận mã MD5 của `physics_formulas.json` khi chạy `build_faiss_index.py`.
* Khi hệ thống khởi chạy API, thực hiện kiểm tra mã MD5 của DB hiện tại với mã MD5 đã index để cảnh báo lập tức nếu lập trình viên chỉnh sửa công thức nhưng chưa build lại FAISS index.


---

### 2.1. Giải pháp Hybrid Retrieval (Parallel Scoring)
Thực hiện đánh giá song song thay vì lọc tuần tự.

> **Ghi chú:** Làm sau khi Symbol Registry xong. Với DB 53 formulas, IDF gain có thể khiêm tốn — nên đo baseline trước khi invest.

1. **Symbol-IDF Weighted Jaccard**: 
   Thay vì dùng Jaccard thuần, tính toán IDF (Inverse Document Frequency) cho từng biến vật lý trong toàn bộ Database.
   $$\text{Score}_{\text{overlap}} = \frac{\sum_{x \in A \cap B} \text{IDF}(x)}{\sum_{x \in A \cup B} \text{IDF}(x)}$$
   *Giúp tôn vinh các biến hiếm, đặc trưng và giảm nhiễu từ các biến phổ quát.*

2. **Giữ `find` làm Hard Constraint (Nhẹ)**:
   Công thức đích (terminal formula) bắt buộc phải chứa biến mục tiêu (`find`). Khác với Domain, đây là ranh giới toán học bắt buộc. Bất kỳ công thức nào đưa vào Fusion Score đều phải pass điều kiện `find ∈ variables` (hoặc tập các alias của nó).

3. **Domain Soft Boost**:
   Thay vì loại bỏ công thức khác domain, dùng domain như một "tie-breaker" (điểm thưởng phụ):
   $$\text{Score}_{\text{total}} = \alpha \cdot \text{FAISS} + \beta \cdot \text{Score}_{\text{overlap}} + \gamma \cdot \mathbb{1}[\text{domain match}]$$

### 2.2. Nâng cấp Multi-step Solver (Forward Chaining / Fixpoint Closure)

> **Ghi chú:** High risk. Chỉ làm sau khi Symbol Registry + Hybrid Retrieval ổn định. Forward Chaining chết ngay nếu symbol consistency chưa đảm bảo.

* **Định nghĩa lại "Fireable Formula"**:
  Một công thức có thể giải được nếu **số biến chưa biết đúng bằng 1** (bất kể nằm ở LHS hay RHS).
  ```python
  def is_fireable(formula_vars: set, known_vars: set) -> bool:
      return len(formula_vars - known_vars) == 1
  ```
* **Thuật toán Closure Computation**:
  Dùng vòng lặp suy diễn tiến (Forward Chaining) giống thuật toán Datalog fixpoint. Lặp qua tất cả công thức, tìm các công thức `fireable` để giải ra biến mới, cập nhật vào tập `known_vars`, lặp lại cho đến khi tìm được `find` hoặc không thể suy ra biến mới. Cấu trúc này không lo bị infinite loop (chỉ tối đa $|V|$ vòng) và O(F × V) chạy cực nhanh, giải quyết triệt để việc chọn nhầm công thức bắc cầu.

---

## 3. Kế hoạch triển khai (Phased Execution) — CẬP NHẬT

### Giai đoạn 0 [DONE ✅]: Symbol Registry (Tiên quyết cho mọi thứ)
- [x] Tạo `pipeline/type2/symbol_registry.py` với `CANONICAL` + `ALIASES`
- [x] Bước A: alias fallback trong `sympy_solver.py` — **+bugfix unconditional return**
- [x] Bước B: normalize LHS `physics_formulas.json` + rebuild FAISS (58 formulas, MD5 guard)
- [x] Bước C: `regex_extract.py` + `type2_classifier.py` import từ registry
- [x] Audit script `scripts/audit_db_formulas.py` + thêm 7 formulas mới (formula_054–060)
- [x] Unit tests 4/4 PASS (`tests/unit_test_edge_cases.py`)

### Giai đoạn 1 [SỬA]: Nâng cấp Retrieval Score (Low Risk)
> Chỉ bắt đầu sau khi Giai đoạn 0 xong và test 100-sample không regression.

1. Cài đặt thuật toán tính Symbol-IDF lúc hệ thống load công thức.
2. Áp dụng công thức Parallel Scoring (FAISS + Weighted Jaccard + Domain Boost).
3. **Grid Search Validation**: 
   * Thu gọn không gian tìm kiếm: Đặt ràng buộc $\alpha + \beta = 1$, giới hạn $\gamma \in [0, 0.3]$.
   * Tránh Overfit: Tách tập 75 test cases hiện tại thành tập tune (60 cases) và tập validation (15 cases). Xác nhận không bị regression trên tập validation.

### Giai đoạn 2: Nâng cấp Multi-step Solver (High Risk)
> Chỉ sau Giai đoạn 1 ổn định.

1. Cấu trúc lại bộ xây dựng chuỗi giải sử dụng thuật toán Closure / Forward Chaining.
2. Giữ code DFS `build_formula_chain` cũ chạy song song (qua tính năng flag bật/tắt) để so sánh và A/B testing độ rủi ro.
3. Tạo thêm 2-3 test cases **mới hoàn toàn** — cố ý dựng scenario ép hệ thống chọn biến trung gian/công thức bắc cầu khác biệt (vd: phải dùng biến thể $P=I^2R$). Chỉ khi pass các test case này, ta mới xác nhận Phase 2 hoàn thành đúng nghĩa.

---

## 4. Các TODO còn lại từ improvement1206.md

| # | Item | Priority | Status |
|---|------|----------|--------|
| 1 | Symbol namespace (E vs W) → Symbol Registry | HIGH | ✅ done — P0: `symbol_registry.py` + alias fallback |
| 2 | Gộp 2 detector thành `TARGET_SYMBOL_MAP` chung | MEDIUM | ❌ chưa làm — `regex_extract` dùng `CANONICAL`, `type2_classifier._detect_target_variable` vẫn riêng |
| 3 | Thêm `QUALITATIVE_PROPORTIONAL` question type | MEDIUM | ✅ done — triển khai là `QUALITATIVE` (line 31 `type2_classifier.py`); proportional keywords → QUALITATIVE |
| 4 | Thêm `e = L*delta_I/delta_t` vào RAG DB | MEDIUM | ✅ done — `formula_055` trong `physics_formulas.json`; hardcode fallback vẫn giữ làm safety net |
| 5a | Angular frequency `omega` extraction | LOW | ❌ chưa làm |
| 5b | `electromotive force` → `e` (hiện map sang `EMF`, lệch với `_VERB_TARGET_MAP`) | LOW | ✅ done — `_PHRASAL_PATTERNS` lines 255–256 đổi `'EMF'` → `'e'` |
| 6 | `nJ: 1e-9` trong `_EXPECTED_UNIT_SI` | LOW | ✅ done |
| 7 | Z3 structured logging (JSON + z3_timeout) | LOW | ❌ chưa làm |

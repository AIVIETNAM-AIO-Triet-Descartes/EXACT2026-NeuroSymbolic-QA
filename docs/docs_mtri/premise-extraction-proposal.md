# Đề xuất cải tiến Pipeline Trích xuất dữ kiện và Formula RAG (Track 2)

Tài liệu này tổng hợp phân tích, phản biện và kế hoạch chi tiết để cải tiến kiến trúc trích xuất dữ kiện và truy xuất công thức (Formula RAG) cho Track 2.

---

## Review & Đánh giá (2026-06-19) — SAU VÒNG CHẤM 1 + RE-RUN

> Chi tiết kết quả test: **`docs/docs_mtri/round1_eval_results.md`**. Deadline gia hạn: **~15h 21/06/2026** (~2 ngày).

### Điểm chính thức vòng 1 (submission #28): **39.38**
- Type1: 19.62/25 (answer **17/25**, premises Jaccard ~0.89)
- Type2: 17.0/25 (answer **+ unit**)
- base 36.62 + time bonus 2.75

### Re-run sau Fix (server redeploy, tuần tự, 0 error)
- Type1 answer **17 → 20/25** (+3 — Fix 1 Z3-override, verified deterministic: T1_0034/0042/0016)
- Type2 full **17 → 18/25** (+1: T2_0007 energy `P=U²/R·t`, T2_0013 braking)
- Latency avg **11.3s**, 0 câu >60s → time bonus an toàn
- base ~38.9, total ~**41.6**

### ⚠️ PHÁT HIỆN LỚN: BTC mở rộng domain ngoài điện/từ
Vòng 1 BTC đưa vào **CƠ HỌC / NHIỆT / QUANG** (kinematics, thermodynamics, optics):
- T2_0012-0016 kinematics (accel, braking, F=ma, projectile)
- T2_0017-0019 thermo (Q=mcΔT, latent heat, ideal gas)
- T2_0020 optics (thấu kính)

Các domain này **KHÔNG có trong `physics_formulas.json`** (58 formula toàn điện/từ) và gần như
không có trong 1352-câu CSV (scan keyword: kinematics 1, thermo 5, optics 0). Hiện chỉ "đúng nhờ
PAL fallback" — không deterministic, rủi ro. **Đây là bottleneck điểm Type2 mới.**

### Test mở rộng: `physics_test.csv` 100 câu (type2, tuần tự) — 2026-06-19
Bộ "toàn diện" khó hơn btc_round1 nhiều: **answer 51/100, FULL (ans+unit) 39/100**.
- **Unit emission là lỗ hổng lớn**: answer 51 vs full 39 → **12 câu đúng số nhưng sai/thiếu unit** (12% điểm bay).
- **4 câu timeout 60s** (LD050, LD332, CH107, DT030) ngay cả khi chạy tuần tự — competition scored wrong.
- Yếu nhất: DDT/DT 14%, LD 34% (vector Coulomb + multi-step). Khá hơn: NL 53%, CH/TD/THCB ~50%.

### Reprioritize (2 ngày)
| # | Việc | Mức | Ghi chú |
|---|------|-----|---------|
| P1-A | Bổ sung formula domain mới (kinematics/thermo/optics) + điện thiếu (resistivity, transformer) | **HIGH** | xem §5.1 |
| P1-B | Symbol binding cho domain mới (extraction trả `initial_speed`/`braking_distance` → symbol formula) | **HIGH** | **blocker**: thêm formula vô ích nếu không bind (§5.2) |
| P1-C | Type2 unit emission/convention (N/C, `Z_L`→ohm, optics cm) | **HIGH** ⬆ | đo được **12/100** câu mất điểm chỉ vì unit (§5.3) |
| P1-F | Hard timeout safeguard (~45s) — trả best-effort thay vì để >60s | **HIGH** ⭐mới | 4/100 câu timeout đo được (§5.6) |
| P1-D | Multi-step solver — Forward Chaining (§2.2), fix series capacitor | MED | T2_0006; DDT/DT/LD yếu (§5.4) |
| P1-E | Type1 CoT reasoning (5 câu MCQ/yes-no sai) | LOW | ROI thấp, khó |

### Test tooling sẵn sàng
- `scripts/eval_server.py` — bắn cả 2 track vào `/predict`, scorer committee-faithful (prefix/sci-notation/single-letter), `--batch`.
- `scripts/build_eval_set.py` → `data/eval/eval_set.json` (2160 câu: 808 t1 + 1352 t2).
- `scripts/build_test_batches.py` → `data/eval/test_batches.json` (8 batch × 200, 50/50, stratified).
- `data/eval/btc_round1.json` — 50 câu BTC vòng 1 + gold (regression set).
- **Lưu ý**: batch từ 2160 chỉ test domain điện; cần thêm câu cơ/nhiệt/quang để test domain mới.

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

---

## 5. P1 — Mở rộng Domain + Fixes (từ phân tích vòng 1, 2026-06-19)

### 5.1 [P1-A] Formula domain mới cần thêm vào `physics_formulas.json`
Mỗi formula cần: `formula_sympy`, `variables` (description + unit), `keywords`, `domain`, example.
Sau khi thêm → `python scripts/build_faiss_index.py` (rebuild FAISS + MD5 guard).

**Kinematics** (domain `mechanics`):
- `v = v0 + a*t`
- `s = v0*t + 0.5*a*t**2`
- `v**2 = v0**2 + 2*a*s`  ← braking distance (T2_0013), max height
- `h = v0**2 / (2*g)`  ← projectile max height (T2_0016)
- `F = m*a`  ← Newton 2 (T2_0015)
- `N = m*(g + a)`  ← apparent weight trong thang máy (T2_0014)

**Thermodynamics** (domain `thermodynamics`):
- `Q = m*c*dT`  ← specific heat (T2_0017)
- `Q = m*L`  ← latent heat melt/boil (T2_0018)
- `P*V = n*R*T`  ← ideal gas (T2_0019)

**Optics** (domain `optics`):
- `1/f = 1/do + 1/di`  ← thin lens (T2_0020); chú ý đơn vị cm
- `M = -di/do`  ← magnification

**Điện còn thiếu**:
- `R = rho*l/S`  ← resistivity (T2_0039 hiện sai 1000× do mm² → m² conversion)
- `U2/U1 = N2/N1`  ← transformer (T2_0049, hiện đúng nhưng nên có formula chính thức)

### 5.2 [P1-B] Symbol binding domain mới — BLOCKER
Solver bind theo **tên symbol khớp chính xác** (`sym_dict.get(var)`). Extraction (regex + LLM)
trả **tên dài, KHÔNG nhất quán**: `initial_speed` vs `initial_velocity`, `m` vs `mass`,
`braking_distance`, `max_height`, `object_distance`. → formula `v**2=v0**2+2*a*s` không bind được.

**Việc cần làm:**
1. Mở rộng `symbol_registry.CANONICAL` cho đại lượng cơ/nhiệt/quang (vd `initial speed`→`v0`,
   `acceleration`→`a`, `distance`→`s`, `mass`→`m`, `specific heat`→`c`, `focal length`→`f`,
   `object distance`→`do`, `image distance`→`di`).
2. Thêm `ALIASES` cho các symbol đó (gom các biến thể tên dài LLM hay sinh).
3. Trong solver, normalize `given` keys + `find` qua registry TRƯỚC khi bind (hiện chỉ alias `find`).
4. Test: ép các câu T2_0012-0020 đi qua **SymPy deterministic** (confidence 1.0), không rớt PAL.

### 5.3 [P1-C] Unit emission / convention
- `Z_L`, `Z_C` (inductive/capacitive reactance) phải emit unit `ohm` (T2_0011 hiện rỗng).
- E-field: BTC dùng `N/C`, ta emit `V/m` → cần map `V/m`→`N/C` cho E-field point/charge (T2_0004).
- Optics: trả `cm` (hoặc đảm bảo giá trị + unit khớp đề, T2_0020).
- Đảm bảo mọi solver path set `unit` trong `_UNIT_MAP` / SolverResult.

### 5.4 [P1-D] Multi-step (Forward Chaining, §2.2)
Series capacitor T2_0006 (`C_eq = C1*C2/(C1+C2)` → `Q = C_eq*U`) hiện sai. Đây là case multi-step
điển hình → triển khai Forward Chaining (§2.2) hoặc tối thiểu thêm formula series/parallel cap.

### 5.5 [P1-F] Hard timeout safeguard — MỚI (rủi ro mất điểm)
Đo trên physics_test 100: **4 câu vượt 60s** (LD050, LD332, CH107, DT030) ngay cả tuần tự
→ competition (60s/câu, no retry) sẽ chấm SAI dù pipeline có thể ra đúng nếu kịp.

Nguyên nhân nghi: LLM PAL/CoT fallback trên câu khó (vector Coulomb đa điện tích, multi-step)
chạy lâu + có thể retry. SymPy/vector path nhanh (<1s); chậm là ở nhánh LLM.

**Việc cần làm:**
1. Đặt **deadline tổng ~45s/request** trong `/predict` (vd `asyncio.wait_for` / ThreadPool timeout
   bọc cả pipeline), khi hết giờ → trả **best-effort hiện có** (kết quả solver tốt nhất, hoặc
   answer rỗng + explanation hợp lệ) thay vì treo tới 60s.
2. Giảm `retry_attempts`/`max_tokens` cho nhánh LLM Type2 khi gần deadline.
3. Log thời gian từng node để xác định node nào ngốn (parser LLM vs PAL vs explainer).
4. Cân nhắc: câu vector nặng nên ưu tiên `vector_solver` (deterministic, nhanh) trước khi rớt PAL.

### 5.6 Regression check
Sau mỗi thay đổi: `python scripts/eval_server.py --url <host> --input data/eval/btc_round1.json
--workers 1` — phải KHÔNG regression trên 50 câu BTC, và Type2 full tăng dần. Backup: `demo_type2.py
--limit 100` no-LLM không tụt.

# Proposed Improvements — Track 2 Pipeline (+ Track 1)

> Đã đối chiếu với repo hiện tại (HEAD `cd9ea05`). Chỉ liệt kê việc **CÒN cần làm**.
> Ưu tiên giảm dần.

---

## 1. ⭐ Symbol namespace KHÔNG nhất quán → confident-fallback *(HIGH)*

**Files:** `data/rag/physics_formulas.json`, `pipeline/type2/type2_classifier.py` (`_detect_target_variable`), `pipeline/type2/regex_extract.py` (`_VERB_TARGET_MAP`)

**Bug:** cùng một đại lượng có **nhiều ký hiệu LHS khác nhau** giữa DB và detector:

| Đại lượng | DB formula dùng | Detector trả `find` |
|-----------|-----------------|---------------------|
| Năng lượng tụ | `E = 0.5·C·U²` **và** `W = 0.5·C·U²` | "energy" → `E` (nhưng "potential energy" → `W`) |
| Năng lượng cuộn | `W_L = 0.5·L·I²` | → `E` hoặc `W` |

→ Khi `find="E"` nhưng formula match là `W = 0.5·C·U²`, `solve(eq, E)` fail vì `E` không có trong phương trình → rơi LLM fallback **dù DB CÓ công thức đúng**.

**Fix:**
1. Chọn 1 ký hiệu chuẩn mỗi đại lượng (vd năng lượng = `W`, EMF = `e`).
2. Sửa LHS trong `physics_formulas.json` về ký hiệu chuẩn (gộp `E`/`W`/`W_L` → `W`), rebuild index.
3. Đồng bộ map ở cả 2 detector về cùng ký hiệu.
4. Cẩn thận `E` (energy) vs `E_field` (điện trường) — đừng để đụng nhau.

---

## 2. Gộp 2 detector target_variable làm một *(MEDIUM)*

**Files:** `type2_classifier.py::_detect_target_variable` + `regex_extract.py::detect_find_from_verb` / `_VERB_TARGET_MAP`

Hai map độc lập đã lệch nhau (classifier có "magnetic flux"→`Φ` mà regex không; regex có "inductive reactance"→`Z_L` mà classifier chỉ "impedance"→`Z`). Sửa một bên, bên kia không theo → bug âm thầm.

**Fix:** gộp thành **một dict dùng chung** (`TARGET_SYMBOL_MAP` trong 1 file), cả 2 import. Giảm bề mặt lỗi cho mục #1.

---

## 3. Thêm `QUALITATIVE_PROPORTIONAL` question type *(MEDIUM)*

**Files:** `type2_classifier.py` → `sympy_solver.py`

Tách "directly/inversely proportional" khỏi `QUALITATIVE` → solve bằng phân tích exponent thay vì fallback LLM.

Classifier — thêm vào `_detect_physics_type()` **trước** block `QUALITATIVE` (dòng 176), và **bỏ** "proportional to"/"directly proportional" khỏi block `QUALITATIVE` hiện tại (dòng 178):
```python
# enum:
QUALITATIVE_PROPORTIONAL = "qualitative_proportional"

# _detect_physics_type:
if any(kw in q_lower for kw in (
    "directly proportional", "proportional to", "inversely proportional"
)):
    return PhysicsQuestionType.QUALITATIVE_PROPORTIONAL
```

Solver — thêm `_solve_proportional(parsed, question)`, wire vào `sympy_solver_node`. Logic: lấy `formulas[0]`, `solve(eq, find_sym)` lấy RHS, `fraction(rhs)` → liệt kê symbol tử số + exponent → trả `"U^2, C"`.

---

## 4. Thêm formula EMF cảm ứng vào RAG *(MEDIUM)*

**Files:** `data/rag/physics_formulas.json` → rebuild `data/formula_index/`

Thiếu `e = L * delta_I / delta_t` (DB hiện không có). Thêm formula rồi:
```bash
python scripts/build_faiss_index.py
```

---

## 5. Bổ sung extraction còn thiếu *(LOW)*

**File:** `pipeline/type2/regex_extract.py`

- **Angular frequency** — `_PHRASAL_FIELDS` chưa bắt "angular frequency of X rad/s":
  ```python
  _RADS = r'(rad/s)'
  # trong _PHRASAL_FIELDS, trước "frequency":
  (r'angular\s+frequency', 'omega', _RADS),
  ```
- **"induced EMF"** — `_VERB_TARGET_MAP` (dòng 127) chưa có "electromotive force"/"emf" → thêm, map sang ký hiệu chuẩn (theo #1).
- **"intensity"** trần chưa map `E_field` (chỉ qua `_E_FIELD_PHRASE_PAT` khi kèm "electric field").

---

## 6. Đơn vị `nJ` *(LOW)*

**File:** `scripts/demo_type2.py` dòng 51 (`_EXPECTED_UNIT_SI`) — thêm `nJ`:
```python
"nJ": 1e-9, "uJ": 1e-6, "μJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
```
> `_UNIT_FACTORS` trong `regex_extract.py` cũng nên thêm `nJ` cho nhất quán.

---

## 7. Z3 structured logging (Track 1) *(LOW)*

**File:** `pipeline/type1/z3_solver.py`

`logger.debug` → `logger.warning` + JSON khi FOL parse fail; thêm log Z3 timeout:
```python
logger.warning("FOL parse failed", extra={"extra": {"fol_input": fol_str, "error": str(e)}})
# trong nhánh Unknown:
reason = str(ctx.solver.reason_unknown()).lower()
if "timeout" in reason or "canceled" in reason:
    logger.warning("Z3 timeout", extra={"extra": {"z3_timeout": True}})
```

---

## Verification

Apply xong, chạy **không `--use-llm`** trước (confirm Deterministic Solver cover), rồi bật `--use-llm`:

```bash
python scripts/demo_type2.py --csv data/physics/physics_dev.csv --limit 200
# Lọc query ID trong reports/dev_run_*.json → check CORRECT / WRONG / FALLBACK
```

Câu test trọng tâm: câu năng lượng tụ (`E`/`W` — mục #1, quan trọng nhất), câu "proportional to" (#3), `TD058`/`TD082` (`nJ` — #6).

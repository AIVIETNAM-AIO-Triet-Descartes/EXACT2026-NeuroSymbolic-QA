# Track 2 — Known Weaknesses

## 1. Coulomb Vector Problems (LD* rows) ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `vector_solver.py` strategies A–F, wired as `sympy_solver_node` fallback; còn ~20% hình học phức tạp vẫn LLM)

**Affected:** All LD* rows (multi-charge electrostatics)

**Symptom:** `source=llm_fallback`, `answer=""`

**Root cause:** LD* problems require vector superposition — compute force from each charge pair, decompose into x/y components using sin/cos, sum components, find magnitude. The scalar SymPy solver (`_solve_single`, `_solve_multi_step`) has no concept of vector direction or geometric configuration.

**Example:**
> Three charges q1, q2, q3 at corners of equilateral triangle. Find net force on q1.

SymPy can solve `F = k*q1*q2/r**2` for a single pair but cannot handle angle decomposition or superposition across multiple pairs.

**Fix needed:** Extend `sympy_solver.py` with a vector solver that:
- Detects multi-charge geometry from `parsed_physics`
- Builds coordinate system from given positions
- Computes pairwise Coulomb forces as vectors
- Sums and returns magnitude

---

## 2. Formula Database Coverage ✅ PARTIALLY RESOLVED (2026-06-03 — 20→51 formulas; domain canonical + FAISS rebuild; còn ~60% dataset chưa cover — xem TODO.md P1)

**Affected:** Any question whose formula is not in `data/rag/physics_formulas.json`

**Symptom:** `formula_rag_node` returns no candidates → SymPy has no formula → `llm_fallback`

**Root cause (original):** Formula DB had only 20 entries covering basic circuits and electrostatics. Missing: magnetic fields, AC circuits, measurement, electromagnetics.

**Fix applied (2026-06-03):** Expanded to 51 formulas. Domain canonical (magnetism→electromagnetism, alternating_current→ac_circuits, measurement_error→measurement). 6 formula LHS fixed. FAISS rebuilt (51 vectors).

**Residual gap:** TD/NL/CH/DDT prefixes still missing key formulas (~60% dataset affected). Specific formulas tracked in `docs/TODO.md P1 — Formula DB mở rộng`.

---

## 3. Variable Extraction Reliability (LLM-dependent) ✅ RESOLVED (2026-06-02)

**Affected:** ~~Full pipeline (physics_parser node)~~

**Was:** `physics_parser_node` delegated 100% to `LLMReasoner.parse_physics_question()`. Malformed JSON or a down vLLM server → `given={}` / `find=""` → confidence 0.3 → solver dead.

**Fix applied — regex pre-pass before LLM (the option from this entry):**
1. **New shared module** `pipeline/type2/regex_extract.py` — `extract_given()` + `detect_find_from_verb()`, the proven patterns lifted from `scripts/demo_type2.py` (SI conversion, scientific/bare-power notation, chained & negated-chain assignments, geometry distances).
2. **`physics_parser_node` rewritten** as two-stage: (1) deterministic regex pre-pass — runs even with the LLM server **down**; (2) LLM augment — best-effort, wrapped in try/except. Merge precedence: regex `given`/`find` win (deterministic), LLM fills gaps. Verified on TD/LD/CH samples with server OFF — `given`/`find` fully populated, `llm=0`, confidence 1.0 (previously would be `{}`/0.3).
3. **Confidence** no longer penalised for empty `find`/`given` on types that don't need them (`yes_no`, `error_calc`, `multi_answer`, `qualitative`).

**Residual (tracked, out of this fix's scope):**
- THCB phrasal values ("least count 0.2 V", "reads 5.6 V") have no `sym = value` form → regex misses them. Belongs to `error_solver.py` (Member 3, T2-15) which parses THCB directly.
- ~~`scripts/demo_type2.py` still holds a duplicate copy of the regex patterns.~~ ✅ RESOLVED (2026-06-03 — demo imports `extract_given`/`detect_find_from_verb` from `regex_extract.py`; 244 duplicate lines removed, single source).

---

## 4. Voltage Symbol Convention (U vs V) ✅ RESOLVED

**Decision (2026-06-06 — superseded the 2026-05-28 fix):** follow the Vietnamese
curriculum — `U` = **hiệu điện thế** (potential difference / voltage), `V` =
**điện thế** (electric potential, only `V = k*q/r`). The two are now DISTINCT
symbols, not aliases. The parser/regex is responsible for emitting the right one.

**Fix applied (2026-06-06):**
1. **RAG DB** — 8 voltage formulas `V*→U*` (`U=I*R`, `P=U*I`, `P=U²/R`, KVL
   `U_source/U1/U2`, divider `U_in/U_out`, `Q=C*U`, `E=½C*U²`, `E=U/d`). Kept
   `formula_019` `V=k*q/r` (điện thế). Renamed `formula_017` potential energy
   `U → W` (thế năng) to free `U` for voltage. FAISS rebuilt (51 vec). Done via
   `scripts/_uv_normalize.py` (formula_sympy + variable keys + keyword tokens;
   example/latex narration left as-is — cosmetic, units "V"/"V/m" must not break).
2. **regex_extract** — removed the old `V=U` alias hack; added a `V→U`
   normalizer (skips điện-thế context); verb map: voltage / potential
   difference → `U`, electric potential → `V`, potential energy → `W`.
3. **formula_rag** — **removed** the `U↔V` runtime alias pair from
   `_SYMBOL_ALIASES` (would re-conflate the now-distinct symbols). Kept `W↔E`,
   `t↔T`.
4. **LLM prompt** — `PHYSICS_PARSE_PROMPT` states the U/V convention + 2 few-shot
   (circuit voltage→U, point-charge potential→V).

**Residual (minor, cosmetic):** `example_cot` / `formula_latex` of the 8 reworked
formulas still show `V` in narration (not touched to avoid corrupting the unit
"V"/"V/m"). Does not affect the symbolic solver or chaining; only RAG context
text shown to the explainer LLM.

---

## 5. MULTI_STEP Chain Termination

**Affected:** Multi-step problems where intermediate variable names differ between formulas

**Symptom:** `_solve_multi_step` loops through all formulas but never accumulates `find` variable

**Root cause:** Chain propagation checks `str(unknown) == find`. If SymPy names the solved symbol differently (e.g., subscript vs plain), the check fails silently.

**Fix needed:** Add fuzzy symbol matching in `_solve_multi_step` accumulated dict lookup.

---

## 6. Classifier `target_variable` = match theo thứ tự mapping, không theo ý đồ câu hỏi ✅ ĐÃ XỬ LÝ (2026-06-02 — `detect_find_from_verb()` trong `regex_extract.py` là nguồn `find` ưu tiên trong `physics_parser`; method classifier giữ nguyên nhưng tụt xuống fallback cuối)

**Affected:** `PhysicsClassifier._detect_target_variable()` (`pipeline/type2/type2_classifier.py`)

**Symptom:** Câu "Find the net **force** on q3" trả `find=Q` thay vì `F` — vì "charges" chứa "charge" (→`Q`) đứng trước "force" (→`F`) trong dict `mapping`. First-match-by-mapping-order, không phải first-match-theo-vị-trí-trong-câu hay theo động từ hỏi.

**Root cause:** `_detect_target_variable` lặp `mapping` và trả var đầu tiên có keyword là substring của câu. Bất kỳ đại lượng nào *xuất hiện* trong đề (dù chỉ là dữ kiện cho trước) đều có thể thắng đại lượng *cần tìm*. Đây là hạn chế **tiền tồn** (có từ trước khi mở rộng enum/domain 2026-05-31), không phải regress.

**Mức ảnh hưởng:** Thấp. Đây chỉ là **prior thô** — `physics_parser_node` chỉ dùng `classified.target_variable` khi LLM bỏ sót `find` (`parsed["find"]` rỗng). Đường chính lấy `find` từ:
- `demo_type2.detect_find_from_verb()` — priority chain Angle > E-field > Force > verb-map (chính xác hơn, bám động từ hỏi)
- `LLMReasoner.parse_physics_question()` — LLM trích `find`

**Fix needed:** Gắn detection vào động từ hỏi — parse cụm sau "find/calculate/determine the **X**" để lấy đại lượng cần tìm, thay vì quét toàn câu. Hoặc port logic `detect_find_from_verb()` từ `demo_type2.py` vào classifier để thống nhất 1 nguồn.

---

## 7. YES_NO Bypass SymPy — Có thể giải symbolic nhưng rơi vào LLM fallback ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `resonance_solver.py` + dispatch guard domain/given trong `sympy_solver_node`; E2E CHLT Yes/No conf=1.0)

**Affected:** `PhysicsQuestionType.YES_NO` — hiện tại routing hoàn toàn sang LLM, không qua `sympy_solver.py`

**Symptom:** `source=llm_fallback`, `confidence=0.5–0.6` dù câu hỏi có đủ dữ kiện để kiểm tra symbolic.

**Example (physics_dev.csv index 9):**
> *"For an RLC AC circuit with R = 45 Ω, L = 1 H, and C = 4 μF, does resonance occur in the circuit at a frequency of 79.6 Hz?"*  
> Ground truth: `answer = Yes`

**Root cause:** `_detect_physics_type()` trả `YES_NO` ngay khi gặp `"resonance occur"` → pipeline routing không dispatch sang SymPy. Tuy nhiên bài này hoàn toàn giải được symbolically:

```
ω₀ = 1 / √(LC) = 1 / √(1 × 4×10⁻⁶) = 500 rad/s
ω  = 2πf = 2π × 79.6 ≈ 500 rad/s
→ ω ≈ ω₀  →  Yes, resonance occurs
```

Phép kiểm tra chỉ cần 2 substitution + so sánh — không cần LLM reasoning.

**Mức ảnh hưởng:** Trung bình. Mọi câu dạng YES/NO cộng hưởng (`CHLT` prefix) đều bị ép `confidence ≤ 0.6` dù kết quả hoàn toàn deterministic.

**Fix needed:** Thêm nhánh symbolic trong routing cho `YES_NO`, nhưng **phải kết hợp 2 điều kiện** để tránh over-routing:
1. Physics parser trích `R, L, C, f` từ câu hỏi.
2. SymPy tính `ω₀ = 1/√(LC)` và `ω = 2πf`, so sánh (với tolerance `≤ 1%`).
3. Nếu tính được → trả `answer="Yes"/"No"`, `confidence=1.0`, `source="sympy"`.
4. Nếu thiếu dữ kiện → fallback LLM như hiện tại.

**⚠️ Rủi ro over-routing (phát hiện 2026-06-02):** Nếu dispatch đơn giản là `q_type == YES_NO → resonance_solver`, sẽ sai với câu như:

> *"In an RLC circuit, Z_L = 70 Ω and Z_C = 50 Ω. What is the circuit's characteristic?"*  
> ground truth: `"the circuit exhibits an inductive characteristic"` — **không phải Yes/No**

Câu này bị classifier nhầm vào `YES_NO` (do dùng pattern "does/is the circuit"), nhưng thực chất là câu qualitative. `resonance_solver` sẽ trả `answer=""` (thiếu L, C, f) thay vì trả đúng đặc tính mạch.

**Dispatch đúng phải thỏa đồng thời 3 điều kiện:**
```python
if (q_type == YES_NO
        and domain == "ac_circuits"
        and all(k in given for k in ("L", "C", "f"))):
    result = solve_resonance(parsed, question)
else:
    result = llm_fallback  # qualitative YES_NO → LLM
```

Kiểm tra `given` có đủ `L, C, f` là **safety gate** quan trọng nhất — resonance_solver đã tự có fallback khi thiếu key, nhưng check sớm tại dispatch tránh gọi solver vô ích và log rõ nguyên nhân.

---

## 8. Dispatch Switch Thiếu 4 Question Type — Toàn bộ rơi về LLM Fallback

**Root cause chung:** `sympy_solver.solve_physics()` chỉ có 2 nhánh dispatch:

```python
if q_type in (SINGLE_FORMULA, CIRCUIT, ELECTROSTATIC): → _solve_single()
elif q_type == MULTI_STEP:                              → _solve_multi_step()
# ← KHÔNG có case nào cho ELECTROMAGNETIC, ERROR_CALC, MULTI_ANSWER, QUALITATIVE
```

→ 4 type này luôn rơi xuống `if not result → llm_fallback`, `confidence = 0.5`, dù nhiều câu hoàn toàn có thể giải symbolic.

> **Kiến trúc routing đã chốt (2026-06-02 — xem `track2_implementation_plan.md` §3.7/§3.8/§4):**
> - `ELECTROMAGNETIC` (DDT) → alias vào `MULTI_STEP` ngay trong `sympy_solver.py` (§8a).
> - `YES_NO` (CHLT) → **file riêng** `pipeline/type2/resonance_solver.py` — `solve_resonance()`.
> - `ERROR_CALC` + `MULTI_ANSWER` (THCB) → **file riêng** `pipeline/type2/error_solver.py` — `solve_error()`.
> - `QUALITATIVE` (NL/DDT) → LLM (§8d).
>
> `sympy_solver_node` chỉ thêm 1 nhánh dispatch gọi các solver này; logic CHLT/THCB **KHÔNG** nằm trong `sympy_solver.py`.

---

### 8a. `ELECTROMAGNETIC` — Thiếu entry trong dispatch, dùng được `MULTI_STEP` ✅ ĐÃ HOÀN THÀNH (2026-06-02 — alias vào nhánh MULTI_STEP trong `solve_physics()`, test W_L=½LI² pass)

**Affected prefix:** `DDT`

**Vấn đề:** Phần lớn bài DDT chỉ cần 1–2 công thức tuyến tính mà `_solve_multi_step` hoàn toàn xử lý được:
```
EMF = -L × (ΔI / Δt)    # solenoid cảm ứng
E   = ½ × L × I²        # năng lượng từ trường
Φ   = B × A × N         # từ thông
```

**Fix needed:** Thêm `ELECTROMAGNETIC` vào nhánh `MULTI_STEP` trong dispatch — **1 dòng thay đổi**:

```python
elif q_type in (PhysicsQuestionType.MULTI_STEP, PhysicsQuestionType.ELECTROMAGNETIC):
```

**Mức ảnh hưởng:** Cao. Toàn bộ DDT rows tính EMF, năng lượng solenoid → `confidence 0.5 → 1.0`.
DDT phức tạp (Faraday với dB/dt biến thiên) vẫn cần LLM — nhưng sẽ ít hơn đáng kể.

**Độ khó:** ⭐ Rất thấp — 1 dòng, không risk regression.

---

### 8b. `ERROR_CALC` — Công thức cố định, giải được hoàn toàn symbolic ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `error_solver.py`: ±, true-vs-measured, least count, mean; error propagation còn fallback LLM)

**Affected prefix:** `THCB`

**Vấn đề:** Sai số đo lường có công thức deterministic:
```
Sai số tuyệt đối:   ΔX = least_count
Sai số tương đối:   δX = ΔX / X_đo × 100%
```

Ví dụ thực tế (`physics_dev[41]`):
> *"The resistance measurement result is: 12.0 ± 0.2 Ω. Calculate the percentage relative uncertainty."*
> → `δR = 0.2 / 12.0 × 100% = 1.67%` — không cần LLM.

**Fix needed:** Implement trong **file riêng** `pipeline/type2/error_solver.py` — hàm `solve_error(parsed, question)` (Member 3, T2-15; xem impl_plan §3.8). **KHÔNG** nhét vào `sympy_solver.py`:
1. Trích `delta` (sai số tuyệt đối) và `X` (giá trị đo được) từ `given`.
2. Phân biệt "relative/percentage" vs "absolute" từ câu hỏi.
3. Tính và trả kết quả với `source="error_calc"`.

`sympy_solver_node` chỉ dispatch `ERROR_CALC → error_solver.solve_error()`.
Phụ thuộc: `physics_parser_node` phải parse được `delta` và `X` — hiện regex chưa bắt dạng phrasal "least count 0.2 V"/"reads 5.6 V" (xem weakness #3 residual) → `error_solver` cần parser THCB riêng.

**Mức ảnh hưởng:** Trung bình — `confidence 0.5 → 1.0` cho toàn bộ THCB single-target.

**Độ khó:** ⭐⭐ Trung bình.

---

### 8c. `MULTI_ANSWER` — Cần extend solver trả list kết quả ✅ ĐÃ HOÀN THÀNH (2026-06-02 — nhánh multi trong `error_solver.solve_error()`, nối `;` cả answer lẫn unit; E2E "0.6; 1.2" | "cm; %")

**Affected prefix:** `THCB` (câu hỏi nhiều đại lượng, answer dạng `"val1; val2"`)

**Vấn đề:** Câu `"Calculate the absolute error and the relative error"` cần 2 giá trị. `_solve_single` chỉ giải 1 `find` tại một thời điểm — trả `answer=""` với cả câu.

**Fix needed:** Xử lý **ngay trong `error_solver.py:solve_error()`** (cùng file với ERROR_CALC), **KHÔNG** ở `sympy_solver.py`. Lý do: `MULTI_ANSWER` hiện chỉ được classifier sinh cho domain `measurement` (THCB) → cùng chủ THCB với ERROR_CALC. `solve_error()` tự rẽ nhánh single vs multi và nối `"; "` cả `answer` lẫn `unit` (đúng convention dataset):

```python
targets = _detect_multiple_targets(question)  # ["delta_X", "delta_X_pct"]
results = [_compute_error(given, t, question) for t in targets]
combined_answer = "; ".join(r["answer"] for r in results if r)
combined_unit   = "; ".join(r["unit"]   for r in results if r)
```

Cần `_detect_multiple_targets()` để parse câu hỏi nhiều `find`. (Nếu sau này có prefix ngoài THCB cần multi-answer, lúc đó mới tách solver riêng — hiện `MULTI_ANSWER ≡ THCB`.)

**Mức ảnh hưởng:** Trung bình — ngăn trả chuỗi rỗng `""` cho THCB multi-target.

**Độ khó:** ⭐⭐⭐ Cao — `physics_parser` phải trích nhiều `find` cùng lúc.

---

### 8d. `QUALITATIVE` — LLM bắt buộc, nhưng có thể tăng confidence một phần

**Affected prefix:** `NL`, `DDT` (câu định tính)

**Vấn đề:** Câu dạng `"What happens to X when Y increases?"` không có numerical answer — LLM là con đường duy nhất. Tuy nhiên, một sub-case có thể giải bằng SymPy:

> *"The electric field energy in a capacitor is directly proportional to which quantity?"*  
> → `E = ½CV²` → phân tích bậc → `E ∝ V²` → answer = "U²"

**Fix needed:** Tách `QUALITATIVE` thành 2 sub-case:
- `QUALITATIVE_PROPORTIONAL` — phát hiện khi câu có `"directly proportional"` / `"proportional to"` → SymPy phân tích exponent trong công thức → `confidence = 0.8`
- `QUALITATIVE_OPEN` — câu mở, giữ LLM → `confidence = 0.5` (như hiện tại)

**Mức ảnh hưởng:** Thấp — chỉ cải thiện được sub-case proportional, câu mở vẫn cần LLM.

**Độ khó:** ⭐⭐⭐ Cao — cần SymPy phân tích đa thức để xác định bậc biến.

---

### Bảng tổng hợp ưu tiên (Weakness #7 + #8)

| # | Type | Prefix | Giải pháp | Confidence sau fix | Độ khó | Ưu tiên |
|:-:|:-----|:------:|:----------|:-----------------:|:------:|:-------:|
| 8a | `ELECTROMAGNETIC` | DDT | Alias vào `MULTI_STEP` (1 dòng) | **1.0** | ⭐ | 🔴 Cao |
| 7  | `YES_NO` | CHLT | `resonance_solver.py` — dispatch chỉ khi `domain=ac_circuits` + `given` có đủ `L,C,f` | **1.0** | ⭐ | 🔴 Cao |
| 8b | `ERROR_CALC` | THCB | file riêng `error_solver.py` → `solve_error()` + parser | **1.0** | ⭐⭐ | 🟠 Trung bình |
| 8c | `MULTI_ANSWER` | THCB | trong `error_solver.py` (nhánh multi của `solve_error()`) | **1.0** | ⭐⭐⭐ | 🟡 Thấp |
| 8d | `QUALITATIVE` | NL/DDT | Sub-case proportional → SymPy | **0.8** | ⭐⭐⭐ | 🟡 Thấp |

> **Quick win đề xuất**: Fix 8a trước (1 dòng, zero risk), sau đó 7 (YES_NO, đo accuracy CHLT ngay được).

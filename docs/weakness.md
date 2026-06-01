# Track 2 — Known Weaknesses

## 1. Coulomb Vector Problems (LD* rows)

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

## 2. Formula Database Coverage (20 formulas only)

**Affected:** Any question whose formula is not in `data/rag/physics_formulas.json`

**Symptom:** `formula_rag_node` returns no candidates → SymPy has no formula → `llm_fallback`

**Root cause:** Formula DB has only 20 entries covering basic circuits and electrostatics. Missing: magnetic fields, optics, thermodynamics, mechanics, AC circuits, etc.

**Fix needed:** Expand `physics_formulas.json` with more formulas. Each entry needs `formula_sympy`, `domain`, `variables`, `keywords` for retrieval to work.

---

## 3. Variable Extraction Reliability (LLM-dependent)

**Affected:** Full pipeline (physics_parser node)

**Symptom:** `given={}` or `find=""` → confidence drops to 0.3 → solver cannot proceed

**Root cause:** `physics_parser_node` delegates to `LLMReasoner.parse_physics_question()`. If LLM returns malformed JSON or misses variables, downstream nodes have no data to work with. Regex fallback in `demo_type2.py` shows this is fixable without LLM but covers limited patterns.

**Fix needed:** Improve `PHYSICS_PARSE_PROMPT` with more few-shot examples, or add a regex pre-pass before LLM call to extract obvious `sym = value unit` assignments.

---

## 4. Voltage Symbol Inconsistency (U vs V) ✅ RESOLVED

**Affected:** ~~Formulas using `U` for voltage (formula_012)~~

**Fix applied (2026-05-28):**
1. **DB fix** — `formula_012` normalized: `U → V` in `formula_sympy`, `variables`, `example_cot`, `keywords`. `formula_015` normalized: `E_field → E` (consistent with `formula_020`). FAISS index rebuilt.
2. **Runtime normalize** — `_inject_symbol_aliases()` added to `formula_rag.py`. After retrieval, compares `formula_doc["variables"]` against `parsed["given"]` and injects bidirectional aliases for known pairs: `U↔V` (voltage), `W↔E` (energy), `t↔T` (time). Handles Vietnamese curriculum notation without requiring DB changes.

---

## 5. MULTI_STEP Chain Termination

**Affected:** Multi-step problems where intermediate variable names differ between formulas

**Symptom:** `_solve_multi_step` loops through all formulas but never accumulates `find` variable

**Root cause:** Chain propagation checks `str(unknown) == find`. If SymPy names the solved symbol differently (e.g., subscript vs plain), the check fails silently.

**Fix needed:** Add fuzzy symbol matching in `_solve_multi_step` accumulated dict lookup.

---

## 6. Classifier `target_variable` = match theo thứ tự mapping, không theo ý đồ câu hỏi

**Affected:** `PhysicsClassifier._detect_target_variable()` (`pipeline/type2/type2_classifier.py`)

**Symptom:** Câu "Find the net **force** on q3" trả `find=Q` thay vì `F` — vì "charges" chứa "charge" (→`Q`) đứng trước "force" (→`F`) trong dict `mapping`. First-match-by-mapping-order, không phải first-match-theo-vị-trí-trong-câu hay theo động từ hỏi.

**Root cause:** `_detect_target_variable` lặp `mapping` và trả var đầu tiên có keyword là substring của câu. Bất kỳ đại lượng nào *xuất hiện* trong đề (dù chỉ là dữ kiện cho trước) đều có thể thắng đại lượng *cần tìm*. Đây là hạn chế **tiền tồn** (có từ trước khi mở rộng enum/domain 2026-05-31), không phải regress.

**Mức ảnh hưởng:** Thấp. Đây chỉ là **prior thô** — `physics_parser_node` chỉ dùng `classified.target_variable` khi LLM bỏ sót `find` (`parsed["find"]` rỗng). Đường chính lấy `find` từ:
- `demo_type2.detect_find_from_verb()` — priority chain Angle > E-field > Force > verb-map (chính xác hơn, bám động từ hỏi)
- `LLMReasoner.parse_physics_question()` — LLM trích `find`

**Fix needed:** Gắn detection vào động từ hỏi — parse cụm sau "find/calculate/determine the **X**" để lấy đại lượng cần tìm, thay vì quét toàn câu. Hoặc port logic `detect_find_from_verb()` từ `demo_type2.py` vào classifier để thống nhất 1 nguồn.

---

## 7. YES_NO Bypass SymPy — Có thể giải symbolic nhưng rơi vào LLM fallback

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

**Fix needed:** Thêm nhánh symbolic trong routing cho `YES_NO`:
1. Physics parser trích `R, L, C, f` từ câu hỏi.
2. SymPy tính `ω₀ = 1/√(LC)` và `ω = 2πf`, so sánh (với tolerance `≤ 1%`).
3. Nếu tính được → trả `answer="Yes"/"No"`, `confidence=1.0`, `source="sympy"`.
4. Nếu thiếu dữ kiện → fallback LLM như hiện tại.

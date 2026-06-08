# EXACT 2026 — Track 2 TODO & Weakness Tracker

**Mục lục (gộp từ 2 file):**
- EXACT 2026 — Track 2 TODO  *(← `TODO.md`)*
- Track 2 — Known Weaknesses  *(← `weakness.md`)*

---

## EXACT 2026 — Track 2 TODO

**Cập nhật:** 2026-06-07 · **Deadline:** 2026-06-10 (còn 3 ngày)

Trạng thái đầy đủ: `docs/track2_reference.md` (data + formula + impl plan), `docs/handoff.md` (session handoff). Weakness tracker đã gộp vào file này (phần dưới).
Nguyên tắc đánh giá: dataset có ~vài chục câu sai → implement tổng thể trước, **không** overfit sample; phân tích case sai (pipeline vs dataset) ở bước CUỐI khi đã đủ tính năng + LLM server + eval harness.
Phạm vi file này = **Track 2**. Track 1 (logic) do thành viên khác phụ trách, merge sau.

---

### ✅ Đã xong
- Core pipeline (parser 2-stage regex+LLM, formula_rag hybrid, sympy dispatch, cot, explainer, self-verifier, API wired).
- Solvers: vector A–F (LD/DT), `resonance_solver` (CHLT), `error_solver` (THCB single+multi), EM→MULTI_STEP alias, dispatch đầy đủ.
- **Multi-formula chaining** (2026-06-03): `formula_rag.build_formula_chain()` resolve dependency closure theo LHS symbol + bridge ω=2πf; `solve_physics` chain khi >1 formula. E2E RLC `Z` given {R,L,C,f} → chain [X_C, X_L, Z] → 136.85 (≈137 ✓) source=sympy.
- **Formula DB 20→51**: domain canonical (magnetism→electromagnetism, alternating_current→ac_circuits, measurement_error→measurement); 6 formula sửa LHS `=` + bỏ `%`; validate symbol-dict (N/I không bị reject — formula_rag_review Vấn đề 3) → 51/51 valid; FAISS rebuild (51 vectors).
- Classifier 5 domain + 10 type (8 prefix). LLM profile config dev/prod + health-check. Prompt 5 domain + few-shot.
- Tests 44/44. E2E CHLT/THCB/RLC-chain conf=1.0.

#### Demo full no-LLM (2026-06-03, floor bi quan): 231/335 evaluable ~69%
TD 50% · LD 80% · DT 32% · NL 100%(n6) · CH 43% · DDT 43% · **THCB 84%** (error_solver ✓) · CHLT/qual = demo không đo được (numeric-only).

---

### 🔲 Cần làm nốt

#### P1 — Coverage thật (cơ chế đã đủ, còn nghẽn extraction + retrieval)
Chaining + DB + solvers xong. Fallback còn cao trên **floor no-LLM** do:
- [ ] **Extraction nghẽn** — regex demo thiếu giá trị phrasal (X_L, ω, "at a frequency of…"). → chạy `--use-llm` để LLM lấp; KHÔNG fix từng regex.
- [ ] **Retrieval** — chọn nhầm giữa 16 formula `ac_circuits`. Cải thiện query (thêm keywords doc — formula_rag_review §2) nếu cần SAU khi đo bằng eval harness.
- [x] **Formula DB mở rộng** (2026-06-06 — list cũ STALE, DB đã 20→53). Audit lại 14 công thức P1: 12/14 ĐÃ có (Q=C*U f011, E=½CU² f012, C=εA/d f018, W_L f025, T=2π√LC f038, X_L f027, X_C f028, Z f029, P=UI·cosφ f033, B=k·n·I f021/022, L=μ₀N²A/l f023, w=B²/2μ₀ f026). Thiếu thật → **đã thêm**: `formula_052` `W=Q**2/(2*C)` (TD năng lượng tụ theo điện tích), `formula_053` `L=4π·1e-7·n**2*V` (DDT độ tự cảm theo thể tích, literal μ₀ khỏi cần given). Validate 53/53, FAISS rebuild 53 vec, solve E2E đúng (0.0018 J / 0.002513 H).
  - **Ghi chú:** F-045/F-046 trong P4 KHÔNG phải formula RAG — là feature error-propagation (đã làm trong `error_solver.py`, cố ý không dùng sympy/RAG).
  - Còn thiếu coverage dataset (~handoff §P3) là do **extraction/retrieval**, không phải thiếu công thức cơ bản — đo bằng eval harness (P2) rồi mới thêm tiếp nếu cần.

#### P2 — Eval harness ✅ ĐÃ HOÀN THÀNH (teammate, verify codebase 2026-06-07; spec `docs/teammates/handoff_teammate2.md`, log `docs/teammates/teammate2-log.md`)
- [x] `evaluation/answer_compare.py` + `evaluation/metrics.py` + `scripts/evaluate.py` + `tests/test_eval.py` — đều tồn tại trong codebase; 18 test pass.
- [x] `compare_answer` xử lý 6 kind (numeric/yes_no/multi/qualitative/unparseable + chuẩn hóa SI + LaTeX `9\sqrt{3}×10^-27`); `rel_tol=5%`. `metrics.evaluate()` gom theo prefix + kind + source; xuất report Markdown/JSON vào `reports/`.
- [x] Chạy thử demo 50 câu (`demo_type2.py --output` → `evaluate.py`): **89.66% (26/29 evaluable)**.
- [ ] **Còn lại:** đo full 1,352 bài (cần `--use-llm` full + VPS FP16) → xác nhận CHLT/THCB/DT/circuit + phân tích case sai (gắn với P5).

#### P3 — vLLM FP16 trên VPS (BẮT BUỘC trước nộp)
- [ ] VPS GPU ≥16GB → cài vLLM → tải HF safetensors `Qwen/Qwen2.5-7B-Instruct`.
- [ ] `config.yaml`: `llm.active: prod` + IP VPS. Verify `/v1/models` trả model_id thật (committee inspect). Code 0 đổi.
- [x] `openai` package đã cài trong venv (**openai 2.38.0**, verify 2026-06-07) — `--use-llm` import OK.
- Dev đang llama.cpp GGUF (alias không verify được) — không hợp lệ để nộp.

#### P4 — Vụn Track 2
- [x] Error propagation F-045/046 trong `error_solver` (2026-06-06). `_solve_propagation()` chặn TRƯỚC nhánh single-± (vốn lấy nhầm ± đầu → đáp confident sai). product/quotient `δZ=Σ(ΔAᵢ/Aᵢ)`, sum/diff `ΔZ=ΣΔAᵢ`; op detect = formula RHS (`*`/`/` vs `+`/`-`) hoặc keyword (series/power); `Z` = sympify(locals) hoặc Πval; unit `{V,A}`→`Ω`(chia)/`W`(nhân). 4/4 THCB003/005/008/009 đúng (1.0Ω/4.21%/0.19W/1.5Ω), 48/48 test.
- [x] `error_solver` — `wants_abs` keyword miss (2026-06-06 — mở rộng pattern: `absolute\s+(error|uncertainty|and)` + `find/calculate absolute`; fix 1 dòng tại dòng 128).
- **Mạch multi-answer + measurement multi-answer trong THCB** — eval harness (no-LLM floor, full 1352) ngày 2026-06-07 chia 4 nhóm:
  - [x] **A. Measurement: mean + sai số** (THCB088/094/098…): `_LIST_PAT` mới bắt list ≥3 giá trị có unit + "and"; mean branch trả multi `mean; error`; `"random error"`=max deviation (THCB007 CoT), `"mean absolute"`=mean. ✓
  - [x] **B. Measurement: abs + rel** (THCB090/093/100…): nới `_TRUE_PAT` ("actual weight"), `_MEASURED_PAT` ("measured result is"/"measured a height of"); classifier thêm cue domain measurement (`random error`/`standard deviation`/`mean absolute`) fix THCB007 misroute. ✓
  - **→ Kết quả A+B (2026-06-07):** accuracy tổng 67.2%→**71.2%** (+17 câu); **THCB 63.3%→92.3%** (48/52); multi-kind 20%→**76%**; 48/48 test. Edge còn sai: THCB110 (wording reference khác), THCB128 (mean lệch — có thể lỗi dataset). KHÔNG overfit 2 sample này.
  - [x] **C. Circuit song song** (2026-06-07 — `pipeline/type2/circuit_solver.py` mới). Quan hệ: `I_i=U/R_i`, `R_p=1/Σ(1/R_i)`, `I_total=ΣI` (hoặc U/R_p), `P=U·I`/`ΣP_i`/chia đều, KCL. (a) multi-find xử lý LOCAL trong solver (detect "each"/"total"/"equivalent"→list `;`), KHÔNG sửa `detect_find_from_verb` toàn cục. (b) dispatch `domain=="circuits"`→circuit_solver, None→solve_physics (Ohm single-formula nguyên). **Guard: chỉ fire khi có `parallel/lamp/bulb`** (tránh hijack CH series). n-detection lamp giống nhau ("two lamps"→2). PAL-aligned (chỉ làm toán). **Kết quả:** no-LLM floor 4/4 extractable (066/069/076/078), simulate-augmented 9/9 (068/072/074/075/077/079/080/082/084 — khi LLM augment lấp given); circuit src 4/4 đúng (0 regression); 56/56 test. (c) regex phrasal Ω/V vẫn optional — LLM augment lấp given cho phrasal cases.
  - [ ] **D. Circuit định tính** (THCB071/073/081/083) → weakness #8d (LLM).
  - [ ] **Classifier misroute CH→circuits** (phát hiện 2026-06-07 qua eval): CH226-245 (mạch AB series R1+R2+inductor, "LCω²=1") bị classify `domain=circuits` thay vì `ac_circuits` (thiếu keyword AC mạnh trong câu). circuit_solver đã guard nên KHÔNG hijack (revert fallback), nhưng đúng ra nên route ac_circuits. Đây là CH phức tạp (series RLC + điều kiện) — kể cả route đúng vẫn nhiều khả năng cần LLM. Ưu tiên thấp; cân nhắc thêm cue "in series ... inductor"/"segment MB"/"LCω" → ac_circuits.
- [x] Weakness #5: MULTI_STEP symbol mismatch + **đổi reactance X_L→Z_L, X_C→Z_C** (2026-06-07 — chuẩn VN: Z_L cảm kháng, Z_C dung kháng, Z tổng trở). Giải **deterministic-only** (không LLM fuzzy): (1) DB formula_027/028/029/035 `X_*→Z_*` + FAISS rebuild 53; (2) prompt flip rule + few-shot; (3) `regex_extract` canonicalize `X_L→Z_L`/`X_C→Z_C` + verb map `inductive/capacitive reactance→Z_L/Z_C`; (4) `_SYMBOL_ALIASES` thêm `Z_L↔X_L`, `Z_C↔X_C` (2 chiều, cùng đại lượng). E2E chain Z=136.85 ✓, alias foreign X_L→Z_L ✓, 48/48 test. **Cách 2 (LLM fuzzy trong `_solve_multi_step`) — KHÔNG implement** (YAGNI: parser đã canonicalize + alias tĩnh phủ tập hữu hạn; residual ngoài bảng hiếm → nếu eval lộ thì THÊM vào bảng alias, không gọi LLM).
  - **Minor cần để ý:** verb map generic `"reactance"→Z_L` là đoán mặc định (câu "find the reactance" không nói rõ loại → mặc định cảm kháng). Hiếm gặp; đo eval rồi chỉnh nếu sai.
- [ ] Weakness #8d: qualitative proportional (ưu tiên thấp).
- [x] TD U/V alias bug (2026-06-06 — **đổi hướng**: chuẩn hóa `U`=hiệu điện thế, `V`=điện thế theo chương trình VN). RAG DB: 8 formula `V*→U*` (Ohm/P=UI/P=U²R/KVL/divider/Q=CU/E=½CU²/E=U/d), giữ `V=k*q/r` (điện thế), `U=k*q1*q2/r` thế năng→`W` (tránh clash). `regex_extract`: bỏ alias hack, normalize `V→U` trừ context điện thế, verb map voltage/pot.diff→`U`. LLM prompt: rule + 2 few-shot. FAISS rebuild 51 vec, 44/44 test. (bonus: fix crash `float("0.8.")` trailing-dot trong `_ASSIGN_PAT`).
- [x] Tech debt: `demo_type2.py` import `regex_extract` (2026-06-03 — xóa 244 dòng copy, single source; demo 44/44 test ✓).
- [x] LD030 vector solver (2026-06-07 — verify: KHÔNG có bug). Strategy C (q0 tại tâm O tam giác đều, 3 charge ở đỉnh) → `0.0007192 N` ≈ gold `7.2×10⁻⁴ N` (rel ~0.1%), source=vector_solver. Memory cũ "chưa test" đã stale.

#### P5 — Housekeeping
- [ ] Commit cụm thay đổi 2026-06-02/03 (solvers, dispatch, classifier, regex_extract, prompt, formula DB, chaining, docs).
- [ ] Sau P1+P2+P3: chạy `--use-llm` full → eval harness → phân tích case sai (pipeline vs dataset).

---

## Track 2 — Known Weaknesses

### 1. Coulomb Vector Problems (LD* rows) ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `vector_solver.py` strategies A–F, wired as `sympy_solver_node` fallback; còn ~20% hình học phức tạp vẫn LLM)

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

### 2. Formula Database Coverage ✅ PARTIALLY RESOLVED (2026-06-03 — 20→51 formulas; domain canonical + FAISS rebuild; còn ~60% dataset chưa cover — xem TODO.md P1)

**Affected:** Any question whose formula is not in `data/rag/physics_formulas.json`

**Symptom:** `formula_rag_node` returns no candidates → SymPy has no formula → `llm_fallback`

**Root cause (original):** Formula DB had only 20 entries covering basic circuits and electrostatics. Missing: magnetic fields, AC circuits, measurement, electromagnetics.

**Fix applied (2026-06-03):** Expanded to 51 formulas. Domain canonical (magnetism→electromagnetism, alternating_current→ac_circuits, measurement_error→measurement). 6 formula LHS fixed. FAISS rebuilt (51 vectors).

**Residual gap:** TD/NL/CH/DDT prefixes still missing key formulas (~60% dataset affected). Specific formulas tracked in `docs/TODO.md P1 — Formula DB mở rộng`.

---

### 3. Variable Extraction Reliability (LLM-dependent) ✅ RESOLVED (2026-06-02)

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

### 4. Voltage Symbol Convention (U vs V) ✅ RESOLVED

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

### 5. MULTI_STEP Chain Termination ✅ RESOLVED (2026-06-07 — deterministic canonicalization, không LLM fuzzy)

**Affected:** Multi-step problems where intermediate variable names differ between formulas

**Symptom:** `_solve_multi_step` loops through all formulas but never accumulates `find` variable

**Root cause:** Chain propagation checks `str(unknown) == find`. If the symbol notation differs (e.g. international `X_L` vs VN `Z_L`), the check fails silently.

**Fix applied (2026-06-07) — 2 lớp deterministic + chuẩn hóa reactance VN:**
1. **Canonical = Z_L (cảm kháng) / Z_C (dung kháng) / Z (tổng trở)** theo chương trình VN. DB formula_027/028/029/035 đổi `X_*→Z_*`; prompt + few-shot flip; FAISS rebuild 53.
2. **Canonicalize tại parse** — `regex_extract` đổi `X_L→Z_L`, `X_C→Z_C` + verb map `inductive/capacitive reactance → Z_L/Z_C`.
3. **Alias tĩnh tại solve** — `_SYMBOL_ALIASES` thêm `Z_L↔X_L`, `Z_C↔X_C` (2 chiều an toàn — cùng đại lượng, khác U/V). Bắt residual path LLM-augment nhả X_L + input ngoại.
4. **Chain** (`build_formula_chain`) match exact LHS — chạy đúng khi DB+given đều canonical. E2E chain Z=136.85 ✓.

**KHÔNG làm (proposals.md Cách 2 — LLM fuzzy match):** YAGNI. Variant là tập hữu hạn đã biết → 2 lớp deterministic phủ hết. Residual ngoài bảng (LLM nhả ký hiệu lạ) hiếm → xử lý đúng = THÊM vào `_SYMBOL_ALIASES` (đo qua eval), KHÔNG gọi LLM mỗi lần kẹt. Giữ làm last-resort note nếu eval lộ miss thật.

---

### 6. Classifier `target_variable` = match theo thứ tự mapping, không theo ý đồ câu hỏi ✅ ĐÃ XỬ LÝ (2026-06-02 — `detect_find_from_verb()` trong `regex_extract.py` là nguồn `find` ưu tiên trong `physics_parser`; method classifier giữ nguyên nhưng tụt xuống fallback cuối)

**Affected:** `PhysicsClassifier._detect_target_variable()` (`pipeline/type2/type2_classifier.py`)

**Symptom:** Câu "Find the net **force** on q3" trả `find=Q` thay vì `F` — vì "charges" chứa "charge" (→`Q`) đứng trước "force" (→`F`) trong dict `mapping`. First-match-by-mapping-order, không phải first-match-theo-vị-trí-trong-câu hay theo động từ hỏi.

**Root cause:** `_detect_target_variable` lặp `mapping` và trả var đầu tiên có keyword là substring của câu. Bất kỳ đại lượng nào *xuất hiện* trong đề (dù chỉ là dữ kiện cho trước) đều có thể thắng đại lượng *cần tìm*. Đây là hạn chế **tiền tồn** (có từ trước khi mở rộng enum/domain 2026-05-31), không phải regress.

**Mức ảnh hưởng:** Thấp. Đây chỉ là **prior thô** — `physics_parser_node` chỉ dùng `classified.target_variable` khi LLM bỏ sót `find` (`parsed["find"]` rỗng). Đường chính lấy `find` từ:
- `demo_type2.detect_find_from_verb()` — priority chain Angle > E-field > Force > verb-map (chính xác hơn, bám động từ hỏi)
- `LLMReasoner.parse_physics_question()` — LLM trích `find`

**Fix needed:** Gắn detection vào động từ hỏi — parse cụm sau "find/calculate/determine the **X**" để lấy đại lượng cần tìm, thay vì quét toàn câu. Hoặc port logic `detect_find_from_verb()` từ `demo_type2.py` vào classifier để thống nhất 1 nguồn.

---

### 7. YES_NO Bypass SymPy — Có thể giải symbolic nhưng rơi vào LLM fallback ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `resonance_solver.py` + dispatch guard domain/given trong `sympy_solver_node`; E2E CHLT Yes/No conf=1.0)

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

### 8. Dispatch Switch Thiếu 4 Question Type — Toàn bộ rơi về LLM Fallback

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

#### 8a. `ELECTROMAGNETIC` — Thiếu entry trong dispatch, dùng được `MULTI_STEP` ✅ ĐÃ HOÀN THÀNH (2026-06-02 — alias vào nhánh MULTI_STEP trong `solve_physics()`, test W_L=½LI² pass)

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

#### 8b. `ERROR_CALC` — Công thức cố định, giải được hoàn toàn symbolic ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `error_solver.py`: ±, true-vs-measured, least count, mean; error propagation còn fallback LLM)

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

#### 8c. `MULTI_ANSWER` — Cần extend solver trả list kết quả ✅ ĐÃ HOÀN THÀNH (2026-06-02 — nhánh multi trong `error_solver.solve_error()`, nối `;` cả answer lẫn unit; E2E "0.6; 1.2" | "cm; %")

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

#### 8d. `QUALITATIVE` — LLM bắt buộc, nhưng có thể tăng confidence một phần

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

#### Bảng tổng hợp ưu tiên (Weakness #7 + #8)

| # | Type | Prefix | Giải pháp | Confidence sau fix | Độ khó | Ưu tiên |
|:-:|:-----|:------:|:----------|:-----------------:|:------:|:-------:|
| 8a | `ELECTROMAGNETIC` | DDT | Alias vào `MULTI_STEP` (1 dòng) | **1.0** | ⭐ | 🔴 Cao |
| 7  | `YES_NO` | CHLT | `resonance_solver.py` — dispatch chỉ khi `domain=ac_circuits` + `given` có đủ `L,C,f` | **1.0** | ⭐ | 🔴 Cao |
| 8b | `ERROR_CALC` | THCB | file riêng `error_solver.py` → `solve_error()` + parser | **1.0** | ⭐⭐ | 🟠 Trung bình |
| 8c | `MULTI_ANSWER` | THCB | trong `error_solver.py` (nhánh multi của `solve_error()`) | **1.0** | ⭐⭐⭐ | 🟡 Thấp |
| 8d | `QUALITATIVE` | NL/DDT | Sub-case proportional → SymPy | **0.8** | ⭐⭐⭐ | 🟡 Thấp |

> **Quick win đề xuất**: Fix 8a trước (1 dòng, zero risk), sau đó 7 (YES_NO, đo accuracy CHLT ngay được).

# EXACT 2026 — Track 2 TODO

**Cập nhật:** 2026-06-03 · **Deadline:** 2026-06-10 (còn 7 ngày)

Trạng thái đầy đủ: `docs/track2_implementation_plan.md`, `docs/weakness.md`, `docs/handoff.md`.
Nguyên tắc đánh giá: dataset có ~vài chục câu sai → implement tổng thể trước, **không** overfit sample; phân tích case sai (pipeline vs dataset) ở bước CUỐI khi đã đủ tính năng + LLM server + eval harness.
Phạm vi file này = **Track 2**. Track 1 (logic) do thành viên khác phụ trách, merge sau.

---

## ✅ Đã xong
- Core pipeline (parser 2-stage regex+LLM, formula_rag hybrid, sympy dispatch, cot, explainer, self-verifier, API wired).
- Solvers: vector A–F (LD/DT), `resonance_solver` (CHLT), `error_solver` (THCB single+multi), EM→MULTI_STEP alias, dispatch đầy đủ.
- **Multi-formula chaining** (2026-06-03): `formula_rag.build_formula_chain()` resolve dependency closure theo LHS symbol + bridge ω=2πf; `solve_physics` chain khi >1 formula. E2E RLC `Z` given {R,L,C,f} → chain [X_C, X_L, Z] → 136.85 (≈137 ✓) source=sympy.
- **Formula DB 20→51**: domain canonical (magnetism→electromagnetism, alternating_current→ac_circuits, measurement_error→measurement); 6 formula sửa LHS `=` + bỏ `%`; validate symbol-dict (N/I không bị reject — formula_rag_review Vấn đề 3) → 51/51 valid; FAISS rebuild (51 vectors).
- Classifier 5 domain + 10 type (8 prefix). LLM profile config dev/prod + health-check. Prompt 5 domain + few-shot.
- Tests 44/44. E2E CHLT/THCB/RLC-chain conf=1.0.

### Demo full no-LLM (2026-06-03, floor bi quan): 231/335 evaluable ~69%
TD 50% · LD 80% · DT 32% · NL 100%(n6) · CH 43% · DDT 43% · **THCB 84%** (error_solver ✓) · CHLT/qual = demo không đo được (numeric-only).

---

## 🔲 Cần làm nốt

### P1 — Coverage thật (cơ chế đã đủ, còn nghẽn extraction + retrieval)
Chaining + DB + solvers xong. Fallback còn cao trên **floor no-LLM** do:
- [ ] **Extraction nghẽn** — regex demo thiếu giá trị phrasal (X_L, ω, "at a frequency of…"). → chạy `--use-llm` để LLM lấp; KHÔNG fix từng regex.
- [ ] **Retrieval** — chọn nhầm giữa 16 formula `ac_circuits`. Cải thiện query (thêm keywords doc — formula_rag_review §2) nếu cần SAU khi đo bằng eval harness.
- [x] **Formula DB mở rộng** (2026-06-06 — list cũ STALE, DB đã 20→53). Audit lại 14 công thức P1: 12/14 ĐÃ có (Q=C*U f011, E=½CU² f012, C=εA/d f018, W_L f025, T=2π√LC f038, X_L f027, X_C f028, Z f029, P=UI·cosφ f033, B=k·n·I f021/022, L=μ₀N²A/l f023, w=B²/2μ₀ f026). Thiếu thật → **đã thêm**: `formula_052` `W=Q**2/(2*C)` (TD năng lượng tụ theo điện tích), `formula_053` `L=4π·1e-7·n**2*V` (DDT độ tự cảm theo thể tích, literal μ₀ khỏi cần given). Validate 53/53, FAISS rebuild 53 vec, solve E2E đúng (0.0018 J / 0.002513 H).
  - **Ghi chú:** F-045/F-046 trong P4 KHÔNG phải formula RAG — là feature error-propagation (đã làm trong `error_solver.py`, cố ý không dùng sympy/RAG).
  - Còn thiếu coverage dataset (~handoff §P3) là do **extraction/retrieval**, không phải thiếu công thức cơ bản — đo bằng eval harness (P2) rồi mới thêm tiếp nếu cần.

### P2 — Eval harness — teammate (`docs/handoff_teammate2.md`)
- [ ] `evaluation/answer_compare.py` + `metrics.py` + `scripts/evaluate.py` + `tests/test_eval.py`.
- [ ] Đo accuracy full 1,352 bài theo prefix + answer-type.
- [ ] **Bắt buộc** để chấm CHLT (Yes/No) + qualitative mà demo numeric-only không đo được; xác nhận CHLT/THCB/DT sau solver mới.

### P3 — vLLM FP16 trên VPS (BẮT BUỘC trước nộp)
- [ ] VPS GPU ≥16GB → cài vLLM → tải HF safetensors `Qwen/Qwen2.5-7B-Instruct`.
- [ ] `config.yaml`: `llm.active: prod` + IP VPS. Verify `/v1/models` trả model_id thật (committee inspect). Code 0 đổi.
- [ ] **`openai` package chưa install trong venv** — blocking LLM path: `.venv\Scripts\pip install openai` (handoff.md §5; hiện chạy no-LLM pass nhưng `--use-llm` sẽ fail import).
- Dev đang llama.cpp GGUF (alias không verify được) — không hợp lệ để nộp.

### P4 — Vụn Track 2
- [x] Error propagation F-045/046 trong `error_solver` (2026-06-06). `_solve_propagation()` chặn TRƯỚC nhánh single-± (vốn lấy nhầm ± đầu → đáp confident sai). product/quotient `δZ=Σ(ΔAᵢ/Aᵢ)`, sum/diff `ΔZ=ΣΔAᵢ`; op detect = formula RHS (`*`/`/` vs `+`/`-`) hoặc keyword (series/power); `Z` = sympify(locals) hoặc Πval; unit `{V,A}`→`Ω`(chia)/`W`(nhân). 4/4 THCB003/005/008/009 đúng (1.0Ω/4.21%/0.19W/1.5Ω), 48/48 test.
- [x] `error_solver` — `wants_abs` keyword miss (2026-06-06 — mở rộng pattern: `absolute\s+(error|uncertainty|and)` + `find/calculate absolute`; fix 1 dòng tại dòng 128).
- [ ] **Mạch multi-answer trong THCB** (~23/80 THCB KHÔNG có `±`, thực ra là bài mạch — đèn parallel/series): tính I/P từng nhánh + tổng. **Routing đã ĐÚNG** — verify 2026-06-07: classify `domain=circuits qtype=circuit` → nhánh `CIRCUIT` trong `solve_physics` (loop `_solve_single`), KHÔNG chạm `error_solver` (chỉ vào đó khi `ERROR_CALC`/`MULTI_ANSWER`). Fallback do **3 nguyên nhân**, không chỉ multi-find:
  1. **Multi-find** — `find` là 1 chuỗi, không chứa nổi list đáp (`I_D1; I_D2; I_total`). VD THCB066 ra được `I=1` (source=sympy, đúng dòng 1 đèn qua `U=I*R`) nhưng kẹt vì không xuất được 3 đáp + thiếu bước tổng `I_total=I_D1+I_D2`.
  2. **Extraction phrasal** — giá trị mạch hay viết "8Ω lamp"/"voltage of 8V" (không dạng `SYM=value`) → regex bỏ sót → `given={}` (THCB068/074). `--use-llm` (LLM augment) lấp được nên **không phải lo gấp**; muốn chắc chắn đầy đủ (no-LLM floor) thì bổ sung regex phrasal cho Ω/V trong `regex_extract`.
  3. **Topology logic** — quy tắc song song/nối tiếp: map nhánh→R (R1↔đèn1…), `R_parallel=(R1*R2)/(R1+R2)`, `I_total=ΣI`, "mỗi đèn"→dòng từng nhánh. Cần cả retrieval đúng formula song song (THCB074 không lấy được `formula_003`) lẫn logic ghép.
  Vài câu **định tính** (THCB071, THCB073) thuộc weakness #8d. **Cần (theo thứ tự):** (a) nâng `detect_find_from_verb` → trả list các target thay vì 1 chuỗi; (b) `circuit_multi_solver` giải từng biến trong list + topology song song/nối tiếp, ghép kết quả bằng `;`; (c) [optional] regex phrasal Ω/V cho no-LLM floor. Đo bằng eval harness (P2) trước khi làm để tránh overfit.
- [ ] Weakness #5: MULTI_STEP fuzzy symbol match (chaining đã giảm áp lực, vẫn cần khi tên biến lệch).
- [ ] Weakness #8d: qualitative proportional (ưu tiên thấp).
- [x] TD U/V alias bug (2026-06-06 — **đổi hướng**: chuẩn hóa `U`=hiệu điện thế, `V`=điện thế theo chương trình VN). RAG DB: 8 formula `V*→U*` (Ohm/P=UI/P=U²R/KVL/divider/Q=CU/E=½CU²/E=U/d), giữ `V=k*q/r` (điện thế), `U=k*q1*q2/r` thế năng→`W` (tránh clash). `regex_extract`: bỏ alias hack, normalize `V→U` trừ context điện thế, verb map voltage/pot.diff→`U`. LLM prompt: rule + 2 few-shot. FAISS rebuild 51 vec, 44/44 test. (bonus: fix crash `float("0.8.")` trailing-dot trong `_ASSIGN_PAT`).
- [x] Tech debt: `demo_type2.py` import `regex_extract` (2026-06-03 — xóa 244 dòng copy, single source; demo 44/44 test ✓).
- [x] LD030 vector solver (2026-06-07 — verify: KHÔNG có bug). Strategy C (q0 tại tâm O tam giác đều, 3 charge ở đỉnh) → `0.0007192 N` ≈ gold `7.2×10⁻⁴ N` (rel ~0.1%), source=vector_solver. Memory cũ "chưa test" đã stale.

### P5 — Housekeeping
- [ ] Commit cụm thay đổi 2026-06-02/03 (solvers, dispatch, classifier, regex_extract, prompt, formula DB, chaining, docs).
- [ ] Sau P1+P2+P3: chạy `--use-llm` full → eval harness → phân tích case sai (pipeline vs dataset).

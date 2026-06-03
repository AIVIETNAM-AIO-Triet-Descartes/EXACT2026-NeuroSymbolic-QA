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

### P2 — Eval harness — teammate (`docs/handoff_teammate2.md`)
- [ ] `evaluation/answer_compare.py` + `metrics.py` + `scripts/evaluate.py` + `tests/test_eval.py`.
- [ ] Đo accuracy full 1,352 bài theo prefix + answer-type.
- [ ] **Bắt buộc** để chấm CHLT (Yes/No) + qualitative mà demo numeric-only không đo được; xác nhận CHLT/THCB/DT sau solver mới.

### P3 — vLLM FP16 trên VPS (BẮT BUỘC trước nộp)
- [ ] VPS GPU ≥16GB → cài vLLM → tải HF safetensors `Qwen/Qwen2.5-7B-Instruct`.
- [ ] `config.yaml`: `llm.active: prod` + IP VPS. Verify `/v1/models` trả model_id thật (committee inspect). Code 0 đổi.
- Dev đang llama.cpp GGUF (alias không verify được) — không hợp lệ để nộp.

### P4 — Vụn Track 2
- [ ] Error propagation F-045/046 trong `error_solver` (đang fallback LLM).
- [ ] Weakness #5: MULTI_STEP fuzzy symbol match (chaining đã giảm áp lực, vẫn cần khi tên biến lệch).
- [ ] Weakness #8d: qualitative proportional (ưu tiên thấp).
- [ ] TD U/V alias bug: `extract_given` inject `V=U` → find=V tưởng đã giải → fallback (demo-path, tiền tồn); đôi khi retrieve sai formula (TD002 lấy `E=V/d`).
- [x] Tech debt: `demo_type2.py` import `regex_extract` (2026-06-03 — xóa 244 dòng copy, single source; demo 44/44 test ✓).
- [ ] Xác nhận LD030 vector solver bug (memory cũ ghi "chưa test").

### P5 — Housekeeping
- [ ] Commit cụm thay đổi 2026-06-02/03 (solvers, dispatch, classifier, regex_extract, prompt, formula DB, chaining, docs).
- [ ] Sau P1+P2+P3: chạy `--use-llm` full → eval harness → phân tích case sai (pipeline vs dataset).

# HANDOFF — EXACT 2026 Track 2 Physics Pipeline

**Branch:** `feature/triet/structure`  
**Last updated:** 2026-06-07  
**Competition deadline:** **June 12, 2026** (gia hạn — Submission Guide §7; trước đó May 30 → Jun 10 → Jun 12)

> Đây là file **session handoff** — đọc TRƯỚC khi nối tiếp việc qua chat session mới.
> Worklist sống ở `docs/TODO.md`; reference Track-2 ở `docs/track2_reference.md`.

---

## 0. TỔNG HỢP TOÀN CẢNH (2026-06-07) — đọc cái này TRƯỚC

> Nguồn trạng thái chuẩn = §0 này + `docs/TODO.md` (worklist chi tiết + weakness tracker).
> §1–7 bên dưới là handoff CŨ (2026-05-29), giữ làm lịch sử — đừng tin số liệu cũ ở đó.

### ✅ ĐÃ LÀM ĐƯỢC (Track 2 pipeline đầy đủ + evaluable, no-LLM chạy được)

**Solvers (dispatch đầy đủ trong `sympy_solver_node`):**
- `vector_solver` A–F — LD/DT Coulomb + E-field (verify LD030 ✓).
- `resonance_solver` — CHLT Yes/No (f₀=1/(2π√LC)), guard domain+L/C/f.
- `error_solver` — THCB sai số: ±, true-vs-measured, least-count, mean/random (max-dev), **error propagation** (product/quotient δZ=ΣδAᵢ, sum/diff ΔZ=ΣΔAᵢ), **measurement multi-answer** (mean+error, abs+rel → `;`).
- `circuit_solver` (MỚI) — mạch song song: I_i=U/R_i, R_p, I_total=ΣI, P, KCL; multi-find local; guard `parallel/lamp/bulb` (tránh hijack CH series).
- `_solve_multi_step` + `formula_rag.build_formula_chain()` — chain đa công thức (closure theo LHS + bridge ω=2πf). E2E RLC Z=136.85 ✓.

**Symbol convention (chuẩn chương trình VN):**
- `U`=hiệu điện thế, `V`=điện thế (V=k*q/r); `Z_L`=cảm kháng, `Z_C`=dung kháng, `Z`=tổng trở. Áp ở DB + `regex_extract` (canonicalize) + prompt + `_SYMBOL_ALIASES` (Z_L↔X_L, Z_C↔X_C cho input ngoại).

**Knowledge + classifier:**
- Formula DB **53** (5 domain canonical), FAISS rebuild, 53/53 valid.
- Classifier 5 domain + 10 question-type; cue `"resona"` route CH resonance đúng ac_circuits (CH ac 200→231, CHLT 14→20).
- LLM profile dev(llama.cpp)/prod(vLLM) qua `config.yaml` + `llm_server_available()` health-check. `openai 2.38.0` đã cài.

**Eval harness (P2, teammate):** `evaluation/` + `scripts/evaluate.py` + `tests/test_eval.py`. Chạy: `demo_type2.py --output X.json` → `evaluate.py --pred X --truth <csv>` → `reports/`.

**Kết quả eval no-LLM floor (full 1352, 2026-06-07):** Accuracy **72.06%** (276/383 evaluable). By-prefix: LD 80% · THCB **96%** · CH 62% · CHLT 25% · DT/TD/DDT thấp (extraction/LLM). Tests **56/56** (`tests/test_type2.py`). *(no-LLM = sàn bi quan; nhiều câu chờ LLM lấp given.)*

### 🔲 CHƯA LÀM
- **🚨 [CRITICAL] Rebuild API layer theo spec chính thức BTC** — endpoint `POST /predict` (1 endpoint, route bằng field `type`), response là **JSON list** `{query_id, answer, unit(ASCII), explanation, premises_used, reasoning}`. Code `api/` hiện tại theo schema CŨ, KHÔNG khớp. **Đọc `docs/official_spec_gaps.md`** (phân tích đầy đủ từ `docs/context/` PDF). Deadline **12/06** (không phải 10/06).
- **vLLM FP16 trên VPS — BẮT BUỘC trước nộp.** Dev đang llama.cpp GGUF (alias không verify được → không hợp lệ). Setup ở §4-P1. → rồi mới chạy được bản nộp.
- **Đo eval full `--use-llm`** (mới đo no-LLM floor + subset 50 câu LLM). Cần sau khi vLLM lên.
- **Qualitative (#8d)** — NL/DDT/THCB định tính (THCB071/073/081/083…) → LLM, chưa xử lý.
- **CH226-245** (mạch AB series, LCω²=1) — route đúng ac_circuits rồi nhưng cần reasoning "Z_L=Z_C triệt tiêu" → vẫn cần LLM.
- **Commit** — toàn bộ thay đổi 2026-06-02…07 còn ở working tree (user tự commit).

### 🎯 MUỐN CẢI TIẾN (next, ưu tiên giảm dần)
1. **Chạy full `--use-llm` + eval** sau khi có vLLM → đo "bung" thật (routing CH/CHLT + circuit phrasal kỳ vọng tăng mạnh khi LLM lấp given).
2. **Circuit phrasal extraction** (regex Ω/V cho "8Ω lamp", "voltage of 8V") — cứng-hóa no-LLM floor cho ~10 câu THCB circuit (hiện given={} không LLM). Optional vì LLM augment che.
3. **Retrieval P1** — query FAISS chọn nhầm giữa 16 formula ac_circuits; thêm keywords doc (formula_rag_review §2). Đo bằng eval harness trước.
4. **2 unit-eval scripts** (teammate, spec `docs/teammates/evaluation_scripts_proposal.md`): `evaluate_rag.py` + `evaluate_classifier.py` — khoanh vùng lỗi RAG vs classifier vs solver.
5. **Edge nhỏ** (KHÔNG overfit): THCB110/128 (wording/mean lệch — có thể lỗi dataset), verb-map generic "reactance"→Z_L mặc định.

### Nguyên tắc làm việc (giữ xuyên suốt)
- Dataset có ~vài chục câu sai → **implement tổng thể, KHÔNG overfit từng sample**; phân tích case sai (pipeline vs dataset) ở bước cuối.
- LLM chỉ **trích (parser) + fallback (CoT/code)** — KHÔNG để LLM tự tính (PAL: symbolic lo phép toán).
- Mọi cải tiến lớn: **đo eval trước/sau** để xác nhận net gain + 0 regression.

---

## 1. Tổng quan kiến trúc

```
Question
  → PhysicsClassifier (type2_classifier.py)
  → regex extract_given() + detect_find_from_verb()     ← demo_type2.py
  → [LLM augment nếu regex không đủ]                   ← --use-llm
  → FormulaRAG (formula_rag.py, FAISS)
  → SymPy solver (sympy_solver.py)
  → vector_solver fallback (vector_solver.py)           ← Strategies A–F
  → [LLM CoT fallback nếu cả hai fail]                 ← --use-llm
  → [LLM sinh explanation]                              ← --use-llm
  → CoT builder (cot_builder.py)
```

LLM gọi qua **vLLM OpenAI-compatible server** (HTTP), không load trực tiếp.

---

## 2. Đã làm xong

### 2.1 vector_solver.py — 6 strategies cho LD/DT problems

| Strategy | Mô tả |
|----------|-------|
| A | FORCE+ANGLE: F1, F2, θ → parallelogram law |
| B | GEOMETRY: coordinate-based Coulomb vector sum (triangle/collinear) |
| C | CENTER: charge tại centroid tam giác đều |
| D | BISECTOR: perpendicular bisector geometry |
| E | INVERSE_ANGLE: cos(θ) = (F²−F1²−F2²)/(2·F1·F2) |
| F | E-FIELD: `_net_efield_at_point()`, `_build_target_pos()`, `_solve_efield_geometry()` |

Accuracy (demo `--limit 100`): **37/47 = 78.7%** trên subset evaluable.

### 2.2 demo_type2.py — extraction fixes

- `_normalize_superscripts()`: ⁻⁸ → -8
- `_BARE_POWER_PAT`: "q1 = 10^-8 C" (không có ×10)
- `_NEG_CHAIN_PAT`: "q1 = -q2 = 10^-7 C" → q1=+1e-7, q2=-1e-7
- `_E_FIELD_PHRASE_PAT`: detect E-field questions trước FORCE
- `_ANGLE_PHRASE_PAT`: detect "find the angle" → find="angle"
- `_BISECTOR_DIST_PAT`: "X cm away from AB" → `given["d_perp"]`
- `detect_find_from_verb()`: priority chain Angle > E-field > Force > verb map
- `_EXPECTED_UNIT_SI`: thêm `"kV/m": 1e3`, `"MV/m": 1e6`, `"degree": 1.0`

### 2.3 LLM integration trong demo_type2.py (`--use-llm`)

3 integration points:
1. **`_llm_augment_parse()`** — sau regex, LLM bổ sung `find`/`given` còn thiếu
2. **`_llm_fallback_solve()`** — gọi `solve_physics_cot()` khi SymPy fail
3. **`_llm_explain()`** — sinh explanation NL sau khi có đáp án

### 2.4 LLMReasoner refactor (vLLM-ready)

**File:** `llm/llm_reasoner.py`

Đã chuyển từ llama-cpp-python (load GGUF trực tiếp) sang **OpenAI client** gọi vLLM server:

```python
# Cũ — load GGUF trực tiếp, không verify được với committee
self.llm = Llama(model_path="./models/qwen.gguf", ...)
output = self.llm.create_chat_completion(messages=[...])

# Mới — OpenAI client → vLLM server
self._client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
response = self._client.chat.completions.create(model="Qwen/Qwen2.5-7B-Instruct", ...)
```

Methods mới thêm:
- `check_server()`: GET /v1/models để verify server reachable
- `_get_client()`: lazy init OpenAI client
- `solve_physics_cot()`: physics CoT solver với `PHYSICS_COT_PROMPT`

**File:** `llm/prompt_templates.py` — thêm `PHYSICS_COT_PROMPT` (3 few-shot examples: numeric/Yes-No/Coulomb)

**File:** `configs/config.yaml` — đổi llm section:
```yaml
llm:
  api_base: "http://localhost:8000/v1"
  api_key: "not-needed"
  model_name: "Qwen/Qwen2.5-7B-Instruct"
  temperature: 0.1
  max_tokens: 1024
```

**File:** `requirements.txt` — thay `llama-cpp-python` bằng `openai>=1.30.0`

---

## 3. Đang làm dở / Chưa test được

### 3.1 vLLM server chưa set up

Code đã refactor xong hoàn toàn để gọi vLLM API. Nhưng **vLLM server chưa chạy** vì:
- vLLM không support Windows native — cần **WSL2**
- CUDA Toolkit chưa cài trong WSL2

**Lý do dùng vLLM thay llama-cpp-python:**
Ban tổ chức yêu cầu: *"committee can inspect /v1/models endpoint to confirm which model is loaded"*. llama-cpp-python server trả về model name tự đặt (không verifiable). vLLM load HF weights trực tiếp → `model_id = "Qwen/Qwen2.5-7B-Instruct"` lấy từ `config.json` thật.

### 3.2 Model HF format chưa download

Hiện có: GGUF model (`models/qwen2.5-7b-instruct-q4_k_m-*.gguf` — 2 shards, ~4.5GB)  
Cần thêm: HF safetensors format (~14GB) cho vLLM  
Lưu ý: GGUF không dùng nữa sau khi vLLM setup xong.

---

## 4. Các bước trước mắt (theo thứ tự ưu tiên)

### P1 — Setup vLLM (urgent, cần trước khi test LLM)

```powershell
# Bước 1: Enable WSL2 (nếu chưa có)
wsl --install
# Reboot

# Bước 2: Trong Ubuntu WSL2 — cài CUDA Toolkit for WSL
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update && sudo apt-get install -y cuda-toolkit-12-4

# Bước 3: Install vLLM + openai trong WSL2
pip install vllm openai

# Bước 4: Download HF model (~14GB)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir ~/models/qwen2.5-7b

# Bước 5: Serve
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --model ~/models/qwen2.5-7b \
  --port 8000 --host 0.0.0.0

# Verify từ Windows PowerShell
curl http://localhost:8000/v1/models
```

### P2 — Test pipeline với LLM ✅ ĐÃ HOÀN THÀNH (2026-05-30 — qua llama.cpp server Q4_K_M thay vLLM, demo --use-llm 77.8%, xem docs/run_demo_llm_local.md)

```powershell
# Trong Windows venv (vLLM server đang chạy trong WSL2)
.venv\Scripts\pip install openai
.venv\Scripts\python scripts/demo_type2.py --limit 50 --use-llm
```

Expect: FALLBACK giảm, `source=llm_cot` xuất hiện, explanation section in ra.

### P3 — Expand physics_formulas.json (tăng coverage không cần LLM)

Formulas còn thiếu (ảnh hưởng ~60% dataset):

| Prefix | Công thức cần thêm |
|--------|-------------------|
| TD | `Q=C*U`, `W=C*U**2/2`, `W=Q**2/(2*C)`, `C=epsilon*S/d` |
| NL | `W_C=C*U**2/2`, `W_L=L*I**2/2`, `T=2*pi*sqrt(L*C)` |
| CH | `XL=omega*L`, `XC=1/(omega*C)`, `Z=sqrt(R**2+(XL-XC)**2)`, `P=U*I*cos_phi` |
| DDT | `B=mu0*n*I`, `L=mu0*n**2*V`, `w=B**2/(2*mu0)` |

File: `data/rag/physics_formulas.json`, rebuild FAISS index sau khi thêm.

### P4 — CHLT Yes/No solver (20 bài, 100% gap) ✅ ĐÃ HOÀN THÀNH (2026-06-02 — `pipeline/type2/resonance_solver.py` + dispatch guard trong `sympy_solver_node`, E2E conf=1.0)

```python
# pipeline/type2/resonance_solver.py
f0 = 1 / (2 * math.pi * math.sqrt(L * C))
return "Yes" if abs(f - f0) / f0 < 0.01 else "No"
```

Cần route CHLT prefix vào solver này.

### P5 — DT prefix routing ✅ ĐÃ HOÀN THÀNH (verified 2026-06-03 — route ngầm qua `find=="E_field"` gate trong `solve_vector_problem` (Strategy F); DT001→0 ✓ khớp ground truth. Accuracy toàn subset DT đo sau bằng eval harness)

Strategy F trong `vector_solver.py` đã xử lý được E-field geometry.  
DT* rows chưa được route vào `solve_vector_problem()`. Cần thêm DT vào dispatch condition.

### P6 — Commit tất cả changes ✅ ĐÃ HOÀN THÀNH (các commit 5075bd9…bff1373; thay đổi 2026-06-02 — solvers/classifier/regex — đang chờ đợt commit mới)

Chưa commit gì từ session này. Tất cả thay đổi đang ở working tree.

```
git add pipeline/type2/vector_solver.py
git add pipeline/type2/sympy_solver.py
git add scripts/demo_type2.py
git add llm/llm_reasoner.py
git add llm/prompt_templates.py
git add llm/__init__.py
git add configs/config.yaml
git add requirements.txt
git commit -m "feat: add vector solver strategies A-F, LLM integration via vLLM API"
```

---

## 5. Thông tin môi trường

| | |
|--|--|
| OS | Windows 11 Home 10.0.26200 |
| GPU | NVIDIA driver 566.24, CUDA 12.7 |
| Python venv | `d:\EXACT2026-NeuroSymbolic-QA\.venv\Scripts\python` |
| Model GGUF | `models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` (3808MB) + shard 2 (658MB) |
| Model HF | Chưa download — cần `Qwen/Qwen2.5-7B-Instruct` (~14GB) trong WSL2 |
| CUDA Toolkit | **Chưa cài** (driver có, toolkit không có → cudart64_12.dll missing) |
| WSL2 | Chưa setup |
| vLLM | Chưa install |
| openai package | ✅ Đã cài (openai 2.38.0) |

---

## 6. Files quan trọng

```
pipeline/type2/vector_solver.py    ← Strategies A–F (core solver)
pipeline/type2/sympy_solver.py     ← Wires vector_solver as fallback
scripts/demo_type2.py              ← Main demo + LLM integration points
llm/llm_reasoner.py                ← OpenAI client wrapper (vLLM-ready)
llm/prompt_templates.py            ← PHYSICS_COT_PROMPT + all prompts
configs/config.yaml                ← vLLM server endpoint config
data/rag/physics_formulas.json     ← Formula DB (cần expand)
docs/TODO.md                       ← Worklist + Known weaknesses tracker (gộp)
docs/track2_reference.md           ← Data analysis + formula format + gaps + impl plan (gộp)
```

---

## 7. Test commands

```powershell
# No LLM (SymPy + vector_solver only)
.venv\Scripts\python scripts/demo_type2.py --limit 100

# Với LLM (vLLM server phải đang chạy)
.venv\Scripts\python scripts/demo_type2.py --limit 100 --use-llm

# Run tests
.venv\Scripts\python -m pytest tests/ -v
```

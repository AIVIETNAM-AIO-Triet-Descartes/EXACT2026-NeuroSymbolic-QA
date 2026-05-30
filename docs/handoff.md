# HANDOFF — EXACT 2026 Track 2 Physics Pipeline

**Branch:** `feature/triet/structure`  
**Last updated:** 2026-05-29  
**Competition deadline:** June 10, 2026 (dời từ May 30)

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

### P2 — Test pipeline với LLM

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

### P4 — CHLT Yes/No solver (20 bài, 100% gap)

```python
# pipeline/type2/resonance_solver.py
f0 = 1 / (2 * math.pi * math.sqrt(L * C))
return "Yes" if abs(f - f0) / f0 < 0.01 else "No"
```

Cần route CHLT prefix vào solver này.

### P5 — DT prefix routing

Strategy F trong `vector_solver.py` đã xử lý được E-field geometry.  
DT* rows chưa được route vào `solve_vector_problem()`. Cần thêm DT vào dispatch condition.

### P6 — Commit tất cả changes

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
| openai package | Chưa install trong venv (cần `.venv\Scripts\pip install openai`) |

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
docs/weakness.md                   ← Known weaknesses tracker
docs/track2_data_info.md           ← Dataset analysis (1352 problems, 8 prefixes)
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

# Chạy Track 2 demo với LLM (local, Q4_K_M + llama.cpp)

Runbook nhập tay cho dev loop trên máy Windows (8GB VRAM). Backend = GGUF Q4_K_M
phục vụ qua `llama-server.exe` (OpenAI-compatible API). Không sửa code/config — chỉ
trỏ `config.yaml` vào `http://localhost:8000/v1` (đã set sẵn).

## Thành phần (đã cài 1 lần, không phải làm lại)

- `openai` trong venv: `.venv\Scripts\pip install "openai>=1.30.0"`
- `llama-server.exe` + CUDA dll: `D:\llama.cpp`
- Model GGUF: `models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` (+ shard 2)
- FAISS index: `data\formula_index\` (đã build)

## Bước 1 — Khởi động LLM server (Terminal 1)

```powershell
cd D:\llama.cpp
.\llama-server.exe `
  -m "D:\EXACT2026-NeuroSymbolic-QA\models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf" `
  -ngl -1 --port 8000 --host 0.0.0.0 -c 4096 --alias Qwen/Qwen2.5-7B-Instruct
```

- `-ngl -1` = offload hết layer lên GPU (Q4 ~4.7GB vừa 8GB VRAM).
- `--alias Qwen/Qwen2.5-7B-Instruct` = `/v1/models` trả đúng id khớp `config.yaml`.
- `-c 4096` = context length. Tăng nếu prompt dài hơn (cẩn thận VRAM).
- Để terminal này MỞ suốt lúc chạy demo.

## Bước 2 — Verify server (Terminal 2)

```powershell
curl http://localhost:8000/v1/models
```

Phải thấy `"id": "Qwen/Qwen2.5-7B-Instruct"`. Nếu lỗi connection → server chưa load
xong, đợi thêm vài giây.

## Bước 3 — Chạy demo (Terminal 2)

```powershell
cd D:\EXACT2026-NeuroSymbolic-QA

# Có LLM (augment + fallback + explanation)
.\.venv\Scripts\python.exe scripts/demo_type2.py --limit 10 --use-llm
.\.venv\Scripts\python.exe scripts/demo_type2.py --limit 50 --use-llm

# Không LLM (chỉ SymPy + vector_solver) — không cần server
.\.venv\Scripts\python.exe scripts/demo_type2.py --limit 50
```

## Bước 4 — Dừng server

Terminal 1: `Ctrl+C`. Hoặc kill theo cổng:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## Ghi chú

- Q4_K_M < FP16 về chất lượng → accuracy demo là "sàn bi quan". Lên VPS FP16 + vLLM
  sẽ tốt hơn; lúc đó chỉ đổi `llm.active: dev` → `prod` trong `config.yaml` (và sửa
  `profiles.prod.api_base` thành IP VPS), không sửa code.
- Vài ký tự hiện `?`/`�` trên console là do code page Windows, không ảnh hưởng logic.
- Bản chạy nộp thi PHẢI dùng vLLM + FP16 (model_id verify được qua `/v1/models`).
  GGUF alias chỉ dùng cho dev.

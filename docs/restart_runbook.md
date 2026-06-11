# Restart Runbook — bật server trước giờ Evaluate (RunPod)

Bản hướng dẫn copy-paste để bật lại hệ thống trước giờ chấm. Có 2 kịch bản:
- **A. Stop/Start cùng pod** (bình thường — pod cũ còn slot GPU).
- **B. Failover** — 3090 hết slot → tạo pod mới + attach lại network volume.

> **Hằng số dự án** (điền sẵn):
> - Network Volume: **`electoral_amaranth_vole_volume`** · 50GB · DC **`EU-CZ-1`**
> - Repo trên volume: **`/workspace/exact2026`** (đã có sẵn `.venv` + model cached, KHỎI tải lại)
> - Image (PHẢI dùng đúng để `.venv` tương thích): **`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`**
> - Container disk: **30GB** · HTTP ports: **8000** (API public) + **8888** (Jupyter)
> - serve.sh mặc định: model **Qwen/Qwen2.5-7B-Instruct**, vLLM **:8002** (nội bộ), API **:8000** (public)
> - Bật **SỚM 1–2 tiếng** trước giờ chấm. Test 60s/câu, no-retry → server phải ấm + verify xong trước giờ G.

---

## A. Stop/Start CÙNG pod (pod cũ start được)

POD_ID **không đổi** → `urls.txt` giữ nguyên.

1. RunPod → pod **fine_tomato_quelea** → **Start** → chờ "Running".
2. Mở **Jupyter Lab** (port 8888) → **New → Terminal**. Dán:

```bash
cd /workspace/exact2026 && bash scripts/serve.sh
```

3. Chờ ~3–5 phút (model cached). Kiểm tra server lên (dán):

```bash
sleep 180; curl -s http://127.0.0.1:8002/v1/models; echo; curl -s http://127.0.0.1:8000/health; echo
```

→ thấy `id: Qwen/Qwen2.5-7B-Instruct` + `{"status":"ok"}` là OK. Sang **mục VERIFY** bên dưới.

---

## B. FAILOVER — 3090 hết slot (Migrate HOẶC tạo pod mới)

> ⚠️ **CẢ HAI cách đều ĐỔI POD_ID → đổi proxy URL.** Đã xác nhận thực tế: RunPod **Migrate** tạo pod tên `*-migration` với **id MỚI** (không giữ id cũ). Vậy dù Migrate hay tạo pod mới → **bắt buộc cập nhật `urls.txt` + báo BTC** (trừ khi đã dùng reverse-proxy URL cố định — xem mục cuối).
> - **Migrate**: RunPod tự dời volume sang pod mới → nhanh, khỏi cấu hình lại volume. Chọn khi RunPod offer lúc Start fail.
> - **Tạo pod mới + attach volume**: khi không migrate được. Các bước B1–B4 bên dưới.
> Sau Migrate: bỏ qua B1–B2 (volume đã theo), nhảy tới **B3** (bật server) + **B5** (đổi URL).

Volume persist toàn bộ (repo + venv + model) → pod mới/migrate **khỏi setup lại**, chỉ chạy `serve.sh`.

### B1. Tạo pod mới
RunPod → **Deploy Pod**:
- **Network Volume**: chọn **`electoral_amaranth_vole_volume`** (sẽ tự lọc GPU trong DC `EU-CZ-1`).
- **GPU**: bất kỳ **≥24GB** còn slot (RTX 4090 / A5000 / A6000 / L4 / 3090...).
- **Container image**: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`  ⚠️ **dùng đúng image này** (khác image → `.venv` có thể vỡ → phải pip install lại, xem B4).
- **Container disk**: 30GB.
- **HTTP ports**: thêm **8000** và **8888**.
- **Volume mount path**: `/workspace`.
- Deploy → chờ "Running".

### B2. Verify volume đã attach (Jupyter terminal — port 8888)
```bash
ls /workspace/exact2026 && du -sh /workspace/hf/hub/* 2>/dev/null
```
→ phải thấy repo + thư mục model `models--Qwen--Qwen2.5-7B-Instruct` (15G). Nếu `/workspace` rỗng → volume CHƯA attach đúng → dừng, gắn lại.

### B3. Bật server
```bash
cd /workspace/exact2026 && bash scripts/serve.sh
sleep 180; curl -s http://127.0.0.1:8002/v1/models; echo; curl -s http://127.0.0.1:8000/health; echo
```
→ `id: Qwen/Qwen2.5-7B-Instruct` + `{"status":"ok"}` → OK.

### B4. (CHỈ khi đổi image / `.venv` vỡ) cài lại deps
Triệu chứng: serve.sh báo lỗi import torch/vllm, hoặc `vllm: command not found`.
```bash
cd /workspace/exact2026
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install vllm
bash scripts/serve.sh
```

### B5. ⚠️ POD_ID MỚI → cập nhật urls.txt
Pod mới/migrate = proxy URL mới. RunPod → pod đang chạy → **Connect** → copy link **Port 8000**. Sửa `submission/urls.txt`:
```
https://<POD_ID_MỚI>-8000.proxy.runpod.net/predict
https://<POD_ID_MỚI>-8000.proxy.runpod.net/v1/models
```
**Báo BTC URL mới** nếu đã nộp urls cũ. *(Bỏ qua bước này nếu đã dùng reverse-proxy URL cố định — xem mục cuối.)*

---

## VERIFY (từ laptop — bắt buộc trước giờ chấm)

Thay `<BASE>` bằng proxy URL của pod đang chạy (Connect → Port 8000). Hiện tại (nếu cùng pod):
`https://w6x7x15q3s8nsb-8000.proxy.runpod.net`

```bash
BASE=https://<POD_ID>-8000.proxy.runpod.net

# 1. Health + model verify (committee dùng /v1/models)
curl -s $BASE/health; echo
curl -s $BASE/v1/models; echo

# 2. Type 2 symbolic (kỳ vọng answer "5" unit "A")
curl -s -X POST $BASE/predict -H 'Content-Type: application/json' \
  -d '{"query_id":"T2_1","type":"type2","query":"Two resistors R1 = 4 ohm and R2 = 6 ohm in parallel across U = 12 V. Find the total current.","premises":[],"options":[]}'; echo

# 3. Type 2 cần LLM (kỳ vọng answer ~"0.045" unit "J")
curl -s -X POST $BASE/predict -H 'Content-Type: application/json' \
  -d '{"query_id":"T2_2","type":"type2","query":"A capacitor charged to 30 V with capacitance 100 uF. Find the stored energy.","premises":[],"options":[]}'; echo

# 4. Type 1 LLM CoT
curl -s -X POST $BASE/predict -H 'Content-Type: application/json' \
  -d '{"query_id":"T1_1","type":"type1","query":"Does it follow that John graduates?","premises":["All students graduate.","John is a student."],"options":[]}'; echo
```

**Pass khi**: `/v1/models` ra đúng id · mỗi `/predict` trả **List JSON** đúng schema (`query_id/answer/unit/explanation/premises_used/reasoning`) · answer không rỗng · phản hồi < 60s.

---

## TROUBLESHOOTING (copy-paste theo lỗi)

| Triệu chứng | Lệnh xử lý |
|-------------|-----------|
| `tmux: command not found` | serve.sh tự cài; nếu vẫn lỗi: `apt-get update && apt-get install -y tmux` rồi chạy lại serve.sh |
| Port 8002 `Address already in use` | `fuser -k 8002/tcp; sleep 3; bash scripts/serve.sh` |
| vLLM tmux `[exited]` khi attach | chạy foreground xem lỗi: `source .venv/bin/activate; export HF_HOME=/workspace/hf; vllm serve Qwen/Qwen2.5-7B-Instruct --host 127.0.0.1 --port 8002 --dtype auto --gpu-memory-utilization 0.9` |
| `CUDA out of memory` lúc load | hạ util/context: thêm `VLLM_EXTRA="--max-model-len 8192" VLLM_PORT=8002` hoặc sửa serve.sh `--gpu-memory-utilization 0.85` |
| VRAM còn bám sau kill | `tmux kill-server; sleep 5; nvidia-smi` (phải ~0) rồi `bash scripts/serve.sh` |
| Volume gần đầy (>90%) | `du -sh /workspace/hf/hub/* /workspace/exact2026/.venv`; xóa model thừa: `rm -rf /workspace/hf/hub/models--<org>--<thừa>` |
| `/v1/models` 503 từ laptop | uvicorn (tmux api) chưa lên / vLLM chưa "startup complete" → `tmux attach -t api` và `-t vllm` kiểm tra |
| Browser mở URL gốc `/` ra `{"detail":"Not Found"}` | BÌNH THƯỜNG (không có route `/`); test bằng `/health`, `/v1/models`, hoặc POST `/predict` |

---

## Lệnh nền tảng (ghi nhớ)

```bash
# Bật toàn bộ (Qwen2.5, mặc định)
cd /workspace/exact2026 && bash scripts/serve.sh

# Xem log server
tmux attach -t vllm        # detach: Ctrl-b rồi d   (ĐỪNG Ctrl-c)
tmux attach -t api

# Tắt server (không tắt pod)
tmux kill-session -t vllm; tmux kill-session -t api
```

> **Tắt pod**: dùng **Stop** (giữ /workspace + POD_ID). **KHÔNG Terminate** (mất pod; volume vẫn còn nhưng phải tạo pod mới → đổi URL).

---

## URL CỐ ĐỊNH (reverse-proxy) — tránh đổi urls.txt mỗi lần failover

**Vấn đề**: mỗi lần Migrate / tạo pod mới → POD_ID đổi → proxy URL đổi → phải sửa urls.txt + báo BTC. Rủi ro lúc gấp.

**Giải pháp**: 1 lớp trung gian có URL **cố định** đứng trước, forward sang pod RunPod hiện tại. BTC chỉ thấy URL cố định; failover chỉ cần repoint upstream (không đổi URL committee). 2 cách:

### Cách 1 — VPS static-IP + reverse-proxy (đúng ý team)
VPS rẻ **không GPU**, IP/domain tĩnh, luôn bật. Chạy Caddy/nginx forward `/predict` + `/v1/models` → RunPod proxy URL hiện tại.

Caddy (auto-HTTPS) — `/etc/caddy/Caddyfile`:
```
your-domain.com {
    reverse_proxy https://<POD_ID>-8000.proxy.runpod.net {
        header_up Host {upstream_hostport}   # SNI/Host đúng để RunPod route tới pod
    }
}
```
Failover → sửa `<POD_ID>` → `caddy reload`. **URL committee (`your-domain.com`) giữ nguyên.**

- ✅ Team kiểm soát hoàn toàn, URL bất biến.
- ⚠️ VPS phải **luôn up** (cheap ~$4-6/mo, no-GPU). Thêm 1 hop (latency vài chục–trăm ms, không sao với 60s budget). Phải set **Host/SNI** đúng tới `*.proxy.runpod.net` (test kỹ).

### Cách 2 — Cloudflare Tunnel trên pod (nhẹ hơn, KHÔNG cần VPS)
`cloudflared` chạy ngay trên pod, named tunnel + token lưu ở `/workspace` (persist). Expose hostname cố định `https://exact.<domain>` → `localhost:8000`.
```bash
# token lưu /workspace → sống qua migrate/restart
cloudflared tunnel --no-autoupdate run --token <TOKEN>   # thêm vào serve.sh / chạy kèm
```
Failover → pod mới chạy lại cloudflared (token trên volume) → **cùng hostname**. Không cần VPS, HTTPS free.

- ✅ Không tốn VPS riêng, URL cố định, HTTPS sẵn.
- ⚠️ Phụ thuộc Cloudflare account + domain. Phải nhúng cloudflared vào quy trình bật (serve.sh).

### Khuyến nghị
Ý tưởng **đúng + nên làm** — URL cố định gỡ hẳn nỗi lo đổi link giữa cuộc thi. Cách 2 (Cloudflare Tunnel) gọn hơn (khỏi VPS); Cách 1 (VPS proxy) nếu team muốn tự chủ hạ tầng.

🚨 **BẮT BUỘC test full chain TRƯỚC ngày thi**: BTC-URL → proxy → RunPod pod → vLLM, đo end-to-end < 60s, thử cả sau khi failover (repoint → URL vẫn chạy). **Đừng** dựng last-minute chưa test — thêm 1 mắt xích = thêm điểm fail.

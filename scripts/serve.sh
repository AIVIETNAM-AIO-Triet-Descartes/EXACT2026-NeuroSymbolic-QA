#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Production serve script — RunPod (or any single GPU box ≥24GB).
# Starts vLLM (internal) + FastAPI (public) in two tmux sessions, idempotently.
#
# Usage:
#   bash scripts/serve.sh                 # defaults: vLLM :8002, API :8000
#   VLLM_PORT=8002 API_PORT=8000 bash scripts/serve.sh
#
# Why 8002 (not 8001): the RunPod template's nginx often holds :8001. 8002 dodges it.
# After running, wait ~3-5 min for weights to load, then verify:
#   curl http://127.0.0.1:$VLLM_PORT/v1/models
#   curl http://127.0.0.1:$API_PORT/health
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="${ROOT:-/workspace/exact2026}"
VLLM_PORT="${VLLM_PORT:-8002}"
API_PORT="${API_PORT:-8000}"
MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
# Extra vLLM flags. For a reasoning model (DeepSeek-R1 / Qwen3 thinking) set e.g.
#   VLLM_EXTRA="--reasoning-parser deepseek_r1 --max-model-len 16384"
# so <think> blocks land in reasoning_content and message.content stays clean for
# our answer extractors. Leave empty for a plain instruct model (Qwen2.5-7B).
VLLM_EXTRA="${VLLM_EXTRA:-}"
export HF_HOME="${HF_HOME:-/workspace/hf}"      # model cache on the persistent volume
export VLLM_BASE="http://127.0.0.1:${VLLM_PORT}"  # /v1/models proxy target (api/main.py)

# tmux is an apt package → wiped on pod restart; reinstall if missing.
command -v tmux >/dev/null 2>&1 || { apt-get update && apt-get install -y tmux; }

# Pin config to prod + the chosen vLLM port + model_name (LLM client reads all from here).
sed -i 's/active: dev/active: prod/' "$ROOT/configs/config.yaml"
sed -i -E "s#(api_base: \"http://localhost:)80[0-9]{2}#\1${VLLM_PORT}#g" "$ROOT/configs/config.yaml"
sed -i -E "s#(model_name: \")[^\"]+(\")#\1${MODEL}\2#g" "$ROOT/configs/config.yaml"

# Restart cleanly (kill stale sessions so ports free up).
tmux kill-session -t vllm 2>/dev/null || true
tmux kill-session -t api  2>/dev/null || true

tmux new -d -s vllm \
  "export HF_HOME='${HF_HOME}'; source '${ROOT}/.venv/bin/activate'; \
   vllm serve '${MODEL}' --host 127.0.0.1 --port ${VLLM_PORT} \
   --dtype auto --gpu-memory-utilization 0.9 ${VLLM_EXTRA}"

tmux new -d -s api \
  "cd '${ROOT}'; source '${ROOT}/.venv/bin/activate'; \
   export VLLM_BASE='${VLLM_BASE}'; \
   uvicorn api.main:app --host 0.0.0.0 --port ${API_PORT}"

# Optional: Auto-register with AWS Proxy
PROXY_IP="${PROXY_IP:-}"
PROXY_SECRET="${PROXY_SECRET:-exact2026_secret}"
RUNPOD_PUBLIC_URL="${RUNPOD_PUBLIC_URL:-}"

if [ -n "$PROXY_IP" ] && [ -n "$RUNPOD_PUBLIC_URL" ]; then
    echo "Registering dynamic RunPod URL ($RUNPOD_PUBLIC_URL) with AWS Proxy ($PROXY_IP)..."
    (
        sleep 10
        curl -s -X POST "http://${PROXY_IP}:8000/register_pod" \
             -H "Content-Type: application/json" \
             -d "{\"url\": \"${RUNPOD_PUBLIC_URL}\", \"secret\": \"${PROXY_SECRET}\"}"
        echo "AWS Proxy registration completed."
    ) &
fi

echo "vLLM → tmux 'vllm' (port ${VLLM_PORT}); API → tmux 'api' (port ${API_PORT})."
echo "Weights load ~3-5 min. Verify: curl http://127.0.0.1:${VLLM_PORT}/v1/models"
echo "Attach a session: tmux attach -t vllm    (detach: Ctrl-b then d)"

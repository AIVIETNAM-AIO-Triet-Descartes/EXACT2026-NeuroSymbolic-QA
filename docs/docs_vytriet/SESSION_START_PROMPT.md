# Session Start Prompt

Copy-paste đoạn dưới vào đầu chat session Claude Code mới để nạp đúng context mới nhất.

---

```
Trước khi làm gì, đọc theo THỨ TỰ này để nắm trạng thái mới nhất (đừng tin số liệu/schema rải rác ở docs khác nếu mâu thuẫn):

1. CLAUDE.md — quy ước repo + API Schema OFFICIAL (binding). Đọc kỹ "API Schema — OFFICIAL" + "LLM Backend".
2. docs/official_spec_gaps.md — SoT cho YÊU CẦU BTC (API /predict, deadline 12/06, luật ≤8B, dataset, notation CSV).
3. docs/docs_vytriet/handoff.md §0 — SoT cho TRẠNG THÁI. **Đọc block "🔄 CẬP NHẬT 2026-06-11" TRƯỚC** (mới nhất); block 06-07 là solver Track 2 (vẫn đúng); §1–7 là lịch sử 05-29 (bỏ qua số liệu).
4. docs/docs_vytriet/TODO.md — worklist + weakness tracker.
5. docs/deployment_plan.md + docs/restart_runbook.md — deploy RunPod + quy trình bật lại / failover (URL đổi khi migrate).
6. docs/docs_vytriet/track2_reference.md — reference data/formula Track 2 (ưu tiên official_spec_gaps khi mâu thuẫn).

Nguồn chuẩn theo mảng:
- Yêu cầu BTC  → docs/context/*.pdf → docs/official_spec_gaps.md
- Convention/kiến trúc → CLAUDE.md
- Trạng thái → docs/docs_vytriet/handoff.md §0 (block 2026-06-11) + docs/docs_vytriet/TODO.md
- Deploy/vận hành → docs/deployment_plan.md + docs/restart_runbook.md

Bối cảnh ngắn (2026-06-11): Track 2 đầy đủ (no-LLM floor 72%, 91 test pass). API ĐÃ rebuild đúng spec /predict; LLM backend = OpenAI client → vLLM (đổi vLLM = flip config llm.active 1 dòng); Type 1 đã wired vào /predict (LLM CoT trên NL). ĐÃ DEPLOY RunPod (Qwen2.5-7B, verify chạy) — vLLM nội bộ :8002, FastAPI :8000, network volume persist. CÒN LẠI: (a) 🚨 premises_used Type 1 LIVE vẫn [] = 50% điểm Type 1 (đồng đội lo — cần CoT báo chỉ số premise hoặc NL→FOL); (b) eval full --use-llm scale; (c) URL ổn định khi failover (migrate đổi POD_ID → đổi urls.txt; tính reverse-proxy). DeepSeek-R1-8B đã thử + LOẠI (luôn-reasoning → 60s risk + parse câm).

Nguyên tắc: implement tổng thể KHÔNG overfit sample · LLM chỉ trích+fallback, symbolic lo phép toán (PAL) · cải tiến lớn đo eval trước/sau (0 regression) · feedback tiếng Việt, xưng bạn–mình.

Sau khi đọc xong, tóm tắt lại cho tôi trạng thái + việc ưu tiên tiếp theo rồi chờ tôi xác nhận.
```

---

## Ghi chú nhanh (cho người dùng, không nằm trong prompt)
- File "chuẩn nhất hiện tại": **CLAUDE.md, docs/official_spec_gaps.md, docs/docs_vytriet/handoff.md §0 (block 2026-06-11), docs/docs_vytriet/TODO.md**.
- Deploy/vận hành: **docs/deployment_plan.md, docs/restart_runbook.md** (RunPod, serve.sh, failover, URL).
- File có banner ⚠️ STALE: **docs/SYSTEM.md** (§6 API + §"API Submission Format" — API thật giờ là `/predict` List schema).
- ⚠️ Docs Vytriet đã move vào **`docs/docs_vytriet/`** (handoff/TODO/track2_reference/proposals). CLAUDE.md còn vài đường dẫn cũ `docs/handoff.md` → đọc ở `docs/docs_vytriet/`.
- Reconcile: spec→`official_spec_gaps.md`, trạng thái→`handoff.md §0`+`TODO.md`, convention→`CLAUDE.md`, deploy→`restart_runbook.md`.

# Session Start Prompt

Copy-paste đoạn dưới vào đầu chat session Claude Code mới để nạp đúng context mới nhất.

---

```
Trước khi làm gì, đọc theo THỨ TỰ này để nắm trạng thái mới nhất (đừng tin số liệu/schema rải rác ở docs khác nếu mâu thuẫn):

1. CLAUDE.md — quy ước repo + API Schema OFFICIAL (binding). Đọc kỹ mục "API Schema — OFFICIAL".
2. docs/official_spec_gaps.md — SoT cho YÊU CẦU BTC (API /predict, deadline 12/06, luật ≤8B, dataset, notation CSV). Mọi chỗ docs khác sai về spec → sửa theo file này.
3. docs/handoff.md §0 — SoT cho TRẠNG THÁI (đã làm / chưa làm / muốn cải tiến). Chỉ §0 là current; §1–7 là lịch sử cũ 2026-05-29 (đừng tin số liệu trong đó).
4. docs/TODO.md — worklist chi tiết + weakness tracker (current).
5. docs/track2_reference.md — reference data/formula/impl Track 2 (một phần số liệu cũ; ưu tiên official_spec_gaps khi mâu thuẫn).

Nguồn chuẩn theo mảng:
- Yêu cầu BTC  → docs/context/*.pdf (gốc) → docs/official_spec_gaps.md (chắt lọc)
- Convention/kiến trúc → CLAUDE.md
- Trạng thái/worklist → docs/handoff.md §0 + docs/TODO.md

Bối cảnh ngắn: Track 2 (physics) pipeline đã đầy đủ + evaluable (no-LLM floor 72.06%, 56/56 test). Việc CRITICAL chưa làm: (a) REBUILD tầng api/ theo schema /predict chính thức (hiện code api/ theo schema CŨ, KHÔNG khớp); (b) vLLM FP16 trên VPS (bắt buộc trước nộp). Pipeline solver Type 2 giữ nguyên — chỉ cần ASCII-hóa unit + bọc theo schema mới.

Nguyên tắc: implement tổng thể KHÔNG overfit sample · LLM chỉ trích+fallback, symbolic lo phép toán (PAL) · mọi cải tiến lớn đo eval trước/sau (0 regression).

Sau khi đọc xong, tóm tắt lại cho tôi trạng thái + việc ưu tiên tiếp theo rồi chờ tôi xác nhận.
```

---

## Ghi chú nhanh (cho người dùng, không nằm trong prompt)
- File "chuẩn nhất hiện tại": **CLAUDE.md, docs/official_spec_gaps.md, docs/handoff.md §0, docs/TODO.md**.
- File có banner ⚠️ STALE đã cắm sẵn: **docs/SYSTEM.md** (§6 API + §"API Submission Format").
- Khi reconcile docs còn lại: spec→`official_spec_gaps.md`, trạng thái→`handoff.md §0`+`TODO.md`, convention→`CLAUDE.md`.

# Official Spec Gaps — codebase vs BTC (2026-06-07)

> Nguồn: `docs/context/QA.pdf` (Official Q&A, cập nhật 2026-05-12), `docs/context/EXACT 2026 - Submission Guide.pdf`, `docs/context/EXACT2026_Notation_Mapping_Template.csv`.
> Mục đích: liệt kê những chỗ codebase hiện tại **lệch** spec chính thức → việc cần làm trước khi nộp. Đọc cùng `docs/handoff.md` §0 + `docs/TODO.md`.

---

## 🚨 CRITICAL — API contract phải rebuild

Tầng API hiện tại (`api/main.py`, `api/schemas.py`, `api/response_builder.py`, `api/router.py`) viết theo schema CŨ tự giả định, **không khớp** Submission Guide. Phải làm lại:

| Mục | Hiện tại (codebase) | Spec chính thức (Submission Guide §2–4) |
|-----|---------------------|------------------------------------------|
| Endpoint | `POST /query` | **`POST /predict`** — MỘT endpoint cho cả Type 1 + Type 2 |
| Request | `{query, premises}` | `{query_id, type, query, premises, options}` (mọi field luôn có; rỗng `""`/`[]` nếu không áp dụng) |
| Routing | keyword classifier `api/router.py` | **đọc field `type`** (`"type1"`/`"type2"`) — committee gửi sẵn. Router keyword **thừa** cho việc chia type (có thể giữ làm fallback nội bộ nhưng KHÔNG phải nguồn chính) |
| Response | 1 object | **JSON LIST** (1 phần tử/query, kể cả 1 query) |
| Response fields | `{answer, explanation, fol, cot, premises, confidence}` | `{query_id, answer, unit, explanation, premises_used, reasoning}` |
| `query_id` | — | **BẮT BUỘC echo** đúng input. (Khác `idx` bị cấm — `query_id` hợp lệ và bắt buộc.) |
| `answer` (Type 2) | đôi chỗ kèm unit | **số THUẦN**; unit ở field riêng |
| `unit` | emit `Ω` / `μF` / `V/m` | **ASCII**: `ohm`, `uF`, `nC`, `V/m`, `A`, `W`, `J`… → cần lớp convert unit khi build response |
| `explanation` | required | required, **non-empty** — nhưng **KHÔNG chấm** ở round này |
| `premises_used` | `premises` (list text) | **list int** index 0-based premise đã dùng (Type 1); `[]` cho Type 2 |
| `reasoning` | tách `fol` + `cot` | **object** `{"type": "fol"|"cot"|"proof", "steps": [...]}`; `null` nếu không có (optional, tính cho P3 sau) |
| `confidence` | có trong response | **KHÔNG có** trong schema chính thức → chỉ giữ NỘI BỘ (set fallback path), không xuất ra |

**Ví dụ output chuẩn (Type 2):**
```json
[{ "query_id":"T2_0001", "answer":"5", "unit":"A",
   "explanation":"Two resistors in parallel give 2.4 ohm; 12V/2.4 = 5 A.",
   "premises_used":[], "reasoning":{"type":"cot","steps":["1/Req=1/4+1/6","Req=2.4 ohm","I=12/2.4=5 A"]} }]
```

**Tác động pipeline:** solver Type 2 hầu như GIỮ NGUYÊN (đã tách answer/unit). Chỉ cần (1) **ASCII-hóa unit**, (2) bọc kết quả theo schema mới + `query_id` + `reasoning` object. Internal `confidence`/`source` vẫn dùng để chọn fallback, chỉ không xuất.

---

## 🟠 MEDIUM

### Notation Mapping CSV (nộp kèm — Submission Guide §5)
- File: `docs/context/EXACT2026_Notation_Mapping_Template.csv` — 3 cột `canonical_latex, meaning, your_notation`. Điền `your_notation` chỗ nào ta KHÁC canonical; để TRỐNG = dùng canonical. Committee **regex-replace** notation trong đề sang dạng ta khai TRƯỚC khi gửi.
- **Quan trọng:** CSV chỉ gồm **operator / greek / unit / prefix LaTeX** (`\times`, `\frac`, `\sqrt{}`, `\times 10^{n}`, `\mu`, `\Omega`, `V`, `ohm`, `uF`…) — **KHÔNG có biến vật lý** (U/V/Z_L/Z_C). → Quy ước symbol VN của ta (U=hiệu điện thế, Z_L=cảm kháng…) là **NỘI BỘ**, không khai ở đây.
- **Hành động:** phần lớn để TRỐNG (chấp nhận canonical). Nhưng **phải verify parser đọc được canonical**: `\times`, `\cdot`, `\frac{a}{b}`, `\sqrt{}`, `a^b`, `a_b`, `\times 10^{n}` (scientific), `\mu`/`\Omega` (đơn vị). `regex_extract` hiện xử lý `×10^`, superscript, `^` — **cần test thêm dạng `\frac`, `\sqrt{}`, `\times 10^{n}` LaTeX thuần**.

### Type 1 MCQ (Submission Guide §3–4) — vùng Track 1 (member khác)
- `options` non-empty → câu chọn; `answer` phải **đúng 1 option**. `options=[]` → free-form (số/text).
- `premises_used` = index premise đã dùng (chấm **50%** điểm Type 1 ở round này — P2).
- Response builder dùng chung → cần thống nhất schema với Track 1.

---

## 🟡 LOW / INFO (cập nhật con số + luật)

- **Deadline GIA HẠN → 12/06/2026** (codebase/handoff đang ghi 10/06 — cần sửa).
- **Test round (live API) = 50 câu**: 25 Type 1 + 25 Type 2. **60s/query**, **no retry** (fail/timeout = sai), tuần tự 1 team/slot 1 giờ.
- **Speed bonus +10%** chỉ tính trên câu ĐÚNG; **Dataset-issue bonus +10%** (report Discord #dataset-issue-report).
- **Dataset:** QA-prefix (401 câu) = lỗi annotation → **PHẢI filter** (`id` bắt đầu "QA"). ✅ Data ta đã sạch (0 QA trong mọi file). Type 2 hiệu lực ~**1354** (ta có 1352, lệch nhỏ — có thể version). Type 1 = **411 record / 808 câu** (CONTEXT cũ ghi 464/913 → stale).
- **Models ≤8B:** nominal 8B-class OK (8.19B vẫn được); MoE tính TỔNG param (Qwen3-30B-A3B KHÔNG hợp lệ). Được dùng model khác nhau cho Type1/Type2 (sequential) hoặc nhiều model parallel miễn TỔNG ≤8B. **Cấm third-party inference API** (Together/Groq/HF Inference…) — phải **tự host vLLM**.
- **Tools/solver/RAG/code-exec/internet retrieval = OK** (không tính param), miễn KHÔNG wrap closed-source LLM. Tool call phải hiện trong CoT/explanation. → kiến trúc neuro-symbolic + PAL của ta hợp lệ.
- **Synthetic data từ closed-source** chỉ để TRAIN (khai báo); cấm gọi inference. **Data Disclosure Document** bắt buộc nộp (liệt kê mọi dataset/RAG corpus/crawl/synthetic).
- **Verify model:** committee query `/v1/models` (vLLM auto-expose) → `id` phải khớp model khai trong solution.pdf. Có thể inspect GPU mem ở Public Test Day.
- **Notation eval:** `√2` ≡ `\sqrt{2}` (normalize) — không bị phạt style; nhưng unit field PHẢI ASCII.

---

## ✅ Việc cần làm (đề xuất, ưu tiên giảm dần)
1. **[CRITICAL] Rebuild API layer** theo `/predict` unified schema (request `{query_id,type,query,premises,options}` → response LIST `{query_id,answer,unit,explanation,premises_used,reasoning}`). Route bằng `type`. ASCII-hóa unit. `reasoning` object. Bỏ `confidence` khỏi output.
2. **[CRITICAL] vLLM FP16 trên VPS** (đã có trong TODO P3 — bắt buộc, dev llama.cpp không hợp lệ).
3. **[MEDIUM] Verify parser canonical LaTeX** (`\frac`, `\sqrt{}`, `\times 10^{n}`) + điền `notation_mapping.csv`.
4. **[MEDIUM] Thống nhất schema response builder với Track 1** (Type 1 MCQ + premises_used).
5. **[ADMIN] Chuẩn bị submission package**: `<team>.zip` = solution.pdf (1 trang, kèm model param ≤8B + datasets) + source_code.zip + urls.txt (predict URL + mọi /v1/models) + notation_mapping.csv. Data Disclosure Document.
6. **[LOW] Sửa con số stale** trong docs (deadline 12/06, Type1 411/808).

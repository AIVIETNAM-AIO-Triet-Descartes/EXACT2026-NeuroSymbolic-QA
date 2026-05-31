# Handoff — Eval & Reporting Harness (Track 2)

**Người nhận:** Member (eval owner)
**Ngày giao:** 2026-05-31 · **Deadline cạnh tranh:** 2026-06-10
**Mức độ độc lập:** 🟢 Cao — chỉ tạo file mới, **không sửa** pipeline/solver/classifier/llm.

---

## 1. Mục tiêu

Hiện `scripts/demo_type2.py` chỉ eval thô trên một subset (so sánh 2% tolerance, in ra console). Cần một **bộ đo lường chuẩn** cho toàn bộ 1,352 bài Track 2:

- Accuracy tổng + **theo từng prefix** (LD/CH/NL/TD/DDT/THCB/DT/CHLT).
- Tách theo **answer-type**: numeric / yes_no / qualitative / multi-answer.
- So sánh đáp án **robust**: số + đơn vị (chuẩn hóa SI), multi-answer (dấu `;`), Yes/No, LaTeX (`9\sqrt{3}×10^-27`).
- Xuất report Markdown + JSON, liệt kê bài sai/bỏ qua kèm `id` để soi.

Vì sao việc này độc lập: nó **đọc artifact** (predictions JSON + dataset CSV), không gọi pipeline. Chạy song song với team đang làm solver/formula DB mà không đụng file nhau.

---

## 2. Phạm vi file (TẤT CẢ đều tạo mới — 0 collision)

```
evaluation/__init__.py
evaluation/answer_compare.py    # so khớp 1 đáp án (số/unit/multi/yes-no/latex/text)
evaluation/metrics.py           # gom nhóm theo prefix + answer-type → số liệu
scripts/evaluate.py             # CLI glue: đọc input → gọi metrics → ghi report
tests/test_eval.py              # unit test cho answer_compare
reports/eval_report.md          # output (generated)
reports/eval_report.json        # output (generated)
```

❌ **KHÔNG sửa:** `pipeline/`, `llm/`, `api/`, `configs/`, `scripts/demo_type2.py`, `scripts/run_pipeline.py`.
Nếu thấy cần đổi 1 trong các file đó → báo lại, đừng tự sửa (tránh đụng nhánh team khác).

---

## 3. Hợp đồng dữ liệu (input — cố định)

### 3.1 Ground truth — `data/train/Physics_Problems_Text_Only.csv`
Cột: `id, question, cot, answer, unit`. Prefix lấy từ `id` (regex `^[A-Z]+`): LD, CH, NL, TD, DDT, THCB, DT, CHLT.
- `answer` có thể là số, "Yes"/"No", chuỗi định tính, hoặc **multi-answer** ngăn bằng `;` (vd `0.6; 1.2`).
- `unit` tương ứng, cũng có thể multi (`cm; %`), hoặc `-`/`—` (định tính/không đơn vị).

### 3.2 Predictions — JSON (artifact từ `scripts/run_pipeline.py`)
Danh sách object, **khớp theo `id`**:
```json
[
  {"id": "TD401", "answer": "0.045", "unit": "J", "confidence": 1.0, "source": "sympy"},
  {"id": "CHLT001", "answer": "No", "confidence": 1.0, "source": "resonance"}
]
```
- `id` BẮT BUỘC để map với ground truth. ⚠️ Đây là metadata **eval-only** — KHÔNG liên quan field `idx` bị cấm trong API response (xem CLAUDE.md). API response không có `id`; file predictions offline thì có.
- `unit`, `confidence`, `source` optional. Nếu predictions hiện tại chưa có `id`/`unit`, viết adapter nhỏ trong `scripts/evaluate.py` (map theo thứ tự dòng) và ghi rõ giả định — **không** sửa run_pipeline.

---

## 4. `evaluation/answer_compare.py` — lõi so khớp

Hàm chính:
```python
def compare_answer(pred: str, gold: str, gold_unit: str = "", *,
                   rel_tol: float = 0.02) -> dict:
    """
    Trả về: {"correct": bool, "kind": str, "detail": str}
      kind ∈ {"numeric","yes_no","multi","qualitative","unparseable"}
    """
```

Quy tắc theo `kind` (xác định kind từ gold trước):

| kind | Cách so |
|------|---------|
| `yes_no` | gold ∈ {Yes,No} → so case-insensitive exact |
| `multi` | gold chứa `;` → split, so **từng phần theo thứ tự**, tất cả phải đúng (mỗi phần đệ quy compare) |
| `numeric` | parse số 2 vế → chuẩn hóa về SI theo `unit` → `abs(p-g)/abs(g) <= rel_tol` |
| `qualitative` | gold là chuỗi chữ → normalize (lower/strip/bỏ dấu câu) + token-overlap ≥ ngưỡng → đánh dấu `needs_review=True` (không tính vào accuracy cứng) |
| `unparseable` | không parse được → `correct=False`, log để soi |

Helper bắt buộc:
```python
def parse_number(s: str) -> float | None
    # "5.0", "4.5e-2", "4.5 × 10^-2", "4.5x10^-2", "9\\sqrt{3} × 10^-27", "0.707"
    # xử lý: ×/x/*, ^, 10^, \sqrt{...}, \times, dấu khoảng trắng
def to_si(value: float, unit: str) -> float
    # bảng prefix→hệ số: pF/nF/μF/mF, mΩ/kΩ/MΩ, μA/mA, mV/kV, mJ/μJ/kJ, nC/μC/mC,
    # mH/μH, N/C, V/m, kV/m, MV/m ... (seed từ _EXPECTED_UNIT_SI trong demo_type2.py)
def split_multi(s: str) -> list[str]   # tách theo ";", strip
```

> Module **tự sở hữu bảng đơn vị** (copy giá trị từ `demo_type2._EXPECTED_UNIT_SI`) để độc lập — đừng import từ scripts.

---

## 5. `evaluation/metrics.py` — gom số liệu

```python
def evaluate(predictions: list[dict], truth: list[dict]) -> dict:
    """
    Join theo id. Với mỗi cặp gọi compare_answer.
    Trả về dict:
    {
      "overall": {"total":N, "evaluable":E, "correct":C, "accuracy":C/E},
      "by_prefix": {"LD": {...}, "CH": {...}, ...},
      "by_kind":   {"numeric":{...}, "yes_no":{...}, "qualitative":{...}, "multi":{...}},
      "by_source": {"sympy":{...}, "resonance":{...}, "llm_cot":{...}, ...},   # nếu có
      "wrong":   [{"id","gold","pred","kind"}...],
      "skipped": [{"id","reason"}...],   # qualitative needs_review, unparseable, missing pred
    }
    """
```
- `evaluable` = numeric + yes_no + multi (loại qualitative khỏi accuracy cứng, báo riêng).
- `by_source` chỉ tính nếu predictions có `source`.

---

## 6. `scripts/evaluate.py` — CLI

```bash
python scripts/evaluate.py \
  --pred output/predictions.json \
  --truth data/train/Physics_Problems_Text_Only.csv \
  --out reports/eval_report.md
```
Việc: load CSV + JSON → `evaluate()` → render:
- `reports/eval_report.md`: bảng overall, by_prefix, by_kind, (by_source), + danh sách wrong/skipped (kèm id, gold, pred).
- `reports/eval_report.json`: dump nguyên dict (cho việc so sánh giữa các lần chạy / regression).
- In tóm tắt accuracy ra stdout.

Mẫu bảng by_prefix trong report:
```
| Prefix | Total | Evaluable | Correct | Acc%  |
|--------|-------|-----------|---------|-------|
| LD     | 397   | 393       | 312     | 79.4% |
| CHLT   | 20    | 20        | 18      | 90.0% |
...
```

---

## 7. `tests/test_eval.py` — bắt buộc

Tối thiểu các case cho `compare_answer`/`parse_number`:
- numeric trong tol: `("5.00","5.0")` → correct; ngoài tol: `("5.5","5.0")` → wrong.
- scientific + ký hiệu nhân: `("4.5e-2","4.5 × 10^-2")` → correct.
- LaTeX: `parse_number("9\\sqrt{3} × 10^-27")` ≈ `1.5588e-26`.
- unit SI: `("100","0.1","mJ"...)` đúng sau chuẩn hóa (vd gold `100 mJ` vs pred `0.1 J`).
- multi-answer: `("0.6; 1.2","0.6; 1.2")` correct; sai thứ tự/1 phần lệch → wrong.
- yes_no: `("yes","Yes")` correct; `("No","Yes")` wrong.
- unparseable: `("upward parabola","downward parabola")` → kind=qualitative, needs_review.

Chạy: `.venv\Scripts\python -m pytest tests/test_eval.py -v`.

---

## 8. Acceptance criteria (Definition of Done)

- [ ] `python scripts/evaluate.py` chạy được trên predictions hiện có, sinh `reports/eval_report.md` + `.json`.
- [ ] Report tách đúng accuracy theo **8 prefix** + theo answer-type.
- [ ] `compare_answer` xử lý đúng cả 6 kind ở §4 (có test phủ).
- [ ] LaTeX `9\sqrt{3}×10^-27` parse ra số (case LD005 hiện đang SKIP trong demo).
- [ ] Multi-answer THCB (`;`) so khớp theo thứ tự.
- [ ] 0 thay đổi ngoài 7 file ở §2. `pytest tests/` toàn bộ vẫn xanh.

---

## 9. Gợi ý thứ tự làm

1. `answer_compare.py` + `tests/test_eval.py` (TDD — viết test trước, đây là phần lõi).
2. `metrics.py` (join + gom nhóm).
3. `scripts/evaluate.py` (glue + render report).
4. Chạy trên predictions thật, soi danh sách `wrong`/`skipped`, tinh chỉnh `rel_tol` và parser.

## 10. Tham chiếu

- `docs/track2_data_info.md` — phân bố prefix, answer-type, ví dụ multi-answer (THCB087), Yes/No (CHLT).
- `scripts/demo_type2.py` — `_EXPECTED_UNIT_SI`, `TOLERANCE=0.02`, logic so khớp hiện tại (tham khảo, đừng import).
- `CLAUDE.md` — API response schema; quy ước confidence; cấm field `idx`.
- `pipeline/state.py` — `SolverResult` (field `source`, `confidence`).

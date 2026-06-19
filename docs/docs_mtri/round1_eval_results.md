# Round 1 Eval — Kết quả chấm BTC + Re-run sau Fix

Ghi lại kết quả vòng chấm chính thức (Jun-14) và lần re-run trên server sau khi vá lỗi,
dùng để theo dõi cải thiện. Test harness: `scripts/eval_server.py` + `scripts/build_eval_set.py`.

---

## 1. Bộ test & công cụ

- **`data/eval/btc_round1.json`** — 50 câu BTC đã chấm vòng 1 (25 type1 + 25 type2),
  trích từ `docs/exact_eval_round1_Cay_Nha_La_Vuon.json`. Mỗi record có `gold_answer`,
  `gold_aliases`, `gold_unit`, `gold_premises_used` (0-based, từ field `idx` của dataset gốc).
- **`scripts/eval_server.py`** — bắn cả 2 track vào `/predict`, 1 report gộp. Scorer
  committee-faithful:
  - **prefix-normalize**: `uF↔F`, `uJ↔J`, `mH↔H`… (so giá trị SI, không so chuỗi).
  - **scientific notation**: parse `"3.38 × 10^-3"` = `0.003384`.
  - **single-letter exact**: MCQ `"C"` không khớp bậy vào text option chứa chữ `c`.
  - **unit symbol khác nhau vẫn sai**: `V/m ≠ N/C` (đúng như BTC chấm).
- Chạy **tuần tự** (`--workers 1`) để khớp competition; `--workers >1` đè 1 GPU →
  Type1 (CoT+Z3) timeout giả >60s.

```bash
python scripts/build_eval_set.py            # nếu cần build lại bộ tổng
python scripts/eval_server.py --url http://<host>:9000 \
    --input data/eval/btc_round1.json --workers 1 --timeout 70 \
    --output output/btc_round1_seq.json
```

---

## 2. Điểm chính thức Jun-14 (submission #28)

| Hạng mục | Giá trị |
|---|---|
| Total score | **39.38** (base 36.62 + time bonus 2.75) |
| Sample avg | 73.25% |
| Type1 | 19.62 / 25 — answer 17/25 (68%), premises Jaccard ~0.89 |
| Type2 | 17.0 / 25 — answer+unit 17/25 (68%) |

---

## 3. Re-run sau Fix (server đã redeploy code mới, tuần tự, 0 error)

| | Jun-14 (chấm) | NOW (re-run) | Δ |
|---|---|---|---|
| Latency | — | avg **11.3s**, max 27.7s, 0 câu >60s | an toàn timeout |
| Type1 answer | 17/25 (68%) | **20/25 (80%)** | **+3** |
| Type1 est score | 78.5% | **~83%** (prem 87%) | +4.5đ |
| Type2 full (ans+unit) | 17/25 (68%) | **18/25 (72%)** | +1 |
| **Base ước tính** | 36.62 | **~38.9** | **+2.3** |

### Fix 1 (Z3 override) — verified LIVE, deterministic
3 câu Jun-14 trả `Uncertain` (do Z3=Unknown đè CoT) nay trả đúng:

| query | câu | Jun-14 | NOW | gold |
|---|---|---|---|---|
| T1_0034 | Azure Reef no-take zone | Uncertain | **Yes ✓** | Yes |
| T1_0042 | Asha active contributor | Uncertain | **Yes ✓** | Yes |
| T1_0016 | Robot Kappa requirements | Uncertain | **No ✓** | No |
| T1_0032 | River Codex safe release | Uncertain | Yes ✗ | No (CoT tự sai) |

> ⚠️ Lần đầu phân tích nhầm Type1 = 92% do bug scorer (lenient substring cho MCQ 1 ký tự).
> Sau khi vá → **80%, recover đúng 3 câu Fix-1** (không có inflation từ LLM variance).

### Type2 — 2 câu improve sẵn trong code mới (ngoài session Fix 1)
- T2_0007 (energy `P=U²/R·t`): 43200 → **1800 ✓**
- T2_0013 (braking `v²=v₀²+2as`): 0 (crash) → **50 ✓**

---

## 4. Còn sai gì (mục tiêu phía trước)

### Type1 (5 câu answer sai — CoT reasoning, KHÔNG phải Fix 1)
`T1_0007` (C/B), `T1_0024` (Yes/No), `T1_0025` (B/C), `T1_0032` (Yes/No), `T1_0035` (B/D).
→ Lỗi suy luận LLM CoT / chọn sai option. Cần cải thiện prompt hoặc Z3 codegen tin cậy.

### Type2 full-wrong (7 câu) — phân loại
| query | vấn đề | loại |
|---|---|---|
| T2_0006 | series capacitor `8.1e-5` vs `3.6e-5` | **multi-step solver (P1)** |
| T2_0039 | resistivity `1000` vs `1` ohm | **unit conversion mm² sai** |
| T2_0003 | `-1.5` vs `1.5` N | dấu (force magnitude) |
| T2_0004 | `V/m` vs `N/C` | unit convention E-field |
| T2_0011 | thiếu unit (`Z_L` không emit `ohm`) | unit emission |
| T2_0020 | optics `0.6` (m) vs `60` cm | scale/unit |
| T2_0001 | unit rỗng (BTC vẫn chấm correct) | borderline |

**Nhận xét quan trọng:** domain mới BTC thêm (kinematics T2_0012-0016, thermo T2_0017-0019)
**phần lớn ĐÃ đúng** qua PAL fallback. Gap thật hẹp hơn lo ngại:
1. **Unit emission/convention** (T2_0004, T2_0011, T2_0020, T2_0001) — quick win, ~4 câu.
2. **Multi-step** (T2_0006 series) — Forward Chaining (P1).
3. **Unit-scale bug** (T2_0039 mm²) — fix conversion.

---

## 5. Tổng kết

Session này (Fix 1 + z3 py3.12 compat) đóng góp **+3 Type1 answer** (deterministic, verified)
và hưởng **+2 Type2** từ code mới đã deploy → base ~36.62 → ~38.9, total ~39.4 → ~41.6.
Đòn bẩy lớn tiếp theo: **unit emission/convention Type2** (quick) + **multi-step P1** +
**Type1 CoT reasoning**.

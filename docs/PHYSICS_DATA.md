# PHYSICS_DATA.md — Yêu cầu Data Vật Lý cho Formula RAG

> **Người nhận:** Người phụ trách tìm kiếm và chuẩn bị data vật lý
> **Mục đích:** Build Vector DB (FAISS) phục vụ node ④b Formula RAG trong pipeline EXACT 2026
> **Ưu tiên:** Hoàn thành tối thiểu 20–30 documents trước khi demo pipeline

---

## Bối cảnh

Dataset Type 2 của cuộc thi gồm **5,520 bài toán vật lý** tập trung vào:
- Mạch điện (electric circuits): resistance, voltage, current, power
- Tĩnh điện (electrostatics): capacitance, electric fields, energy, charge

Trong pipeline, node **Formula RAG** nhận câu hỏi từ Physics Parser, tìm trong Vector DB công thức phù hợp, rồi trả về cho SymPy Solver tính toán. **Data chất lượng kém = RAG trả về sai công thức = toàn bộ track Type 2 sai.**

---

## Format mỗi document

Mỗi công thức vật lý = 1 document JSON theo đúng format sau:

```json
{
  "id": "formula_001",
  "topic": "capacitor_energy",
  "domain": "electrostatics",
  "formula_natural": "Energy stored in a capacitor",
  "formula_sympy": "E = 0.5 * C * U**2",
  "formula_latex": "E = \\frac{1}{2}CV^2",
  "variables": {
    "E": {"description": "Energy stored", "unit": "J"},
    "C": {"description": "Capacitance", "unit": "F"},
    "U": {"description": "Voltage across capacitor", "unit": "V"}
  },
  "unit_conversions": ["μF → 1e-6 F", "mJ → 1e-3 J"],
  "example_question": "Calculate the energy stored in capacitor C when C = 100 μF and U = 30 V.",
  "example_cot": "Step 1: Identify C = 100 μF = 1e-4 F, U = 30 V.\nStep 2: Apply E = 0.5 * C * U^2.\nStep 3: E = 0.5 × 1e-4 × 900 = 0.045 J = 45 mJ.",
  "example_answer": "45",
  "example_unit": "mJ",
  "keywords": ["capacitor", "energy", "capacitance", "voltage", "stored energy"]
}
```

---

## Mô tả từng field

| Field | Bắt buộc | Mô tả |
|---|:---:|---|
| `id` | ✅ | ID duy nhất, format `formula_XXX` |
| `topic` | ✅ | Tên ngắn gọn của công thức, dùng underscore |
| `domain` | ✅ | Một trong: `circuits` hoặc `electrostatics` |
| `formula_natural` | ✅ | Mô tả công thức bằng tiếng Anh tự nhiên — dùng để embedding và retrieval |
| `formula_sympy` | ✅ | Công thức viết đúng Python/SymPy syntax — **xem lưu ý quan trọng bên dưới** |
| `formula_latex` | ❌ | LaTeX — optional, dùng cho documentation |
| `variables` | ✅ | Dict mô tả từng biến số: description + unit SI chuẩn |
| `unit_conversions` | ✅ | List các conversion thường gặp trong bài toán |
| `example_question` | ✅ | 1 câu hỏi mẫu sát với dạng bài trong training data |
| `example_cot` | ✅ | Chain-of-thought giải mẫu, format `Step N: ...` |
| `example_answer` | ✅ | Đáp số (chỉ số, không kèm unit) |
| `example_unit` | ✅ | Unit của đáp số |
| `keywords` | ✅ | List từ khóa để retrieval — càng đa dạng càng tốt |

---

## Lưu ý quan trọng về `formula_sympy`

Đây là field quan trọng nhất — SymPy Solver sẽ dùng trực tiếp để tính toán.

**✅ Đúng:**
```
"formula_sympy": "E = 0.5 * C * U**2"
"formula_sympy": "V = I * R"
"formula_sympy": "P = V * I"
"formula_sympy": "Q = C * V"
```

**❌ Sai — những lỗi thường gặp:**
```
"formula_sympy": "E = ½CV²"          # ký tự Unicode — SymPy không đọc được
"formula_sympy": "E = 1/2 * C * U^2" # dấu ^ không phải Python — phải dùng **
"formula_sympy": "E = (1/2)CV²"      # thiếu dấu * giữa các biến
"formula_sympy": "E = 0.5C * U²"     # viết tắt không hợp lệ
```

**Quy tắc viết `formula_sympy`:**
- Lũy thừa dùng `**` không dùng `^`
- Nhân dùng `*` không bỏ trống
- Không dùng ký tự Unicode (², ½, μ...)
- Biến số dùng chữ cái Latin đơn giản (E, C, U, R, I, P, Q...)

---

## Danh sách topics cần cover

### Domain: circuits (mạch điện)

| Topic | Công thức cần có |
|---|---|
| Ohm's law | `V = I * R` |
| Series resistance | `R_total = R1 + R2 + R3` |
| Parallel resistance | `1/R_total = 1/R1 + 1/R2` |
| Power (voltage-current) | `P = V * I` |
| Power (current-resistance) | `P = I**2 * R` |
| Power (voltage-resistance) | `P = V**2 / R` |
| KVL (Kirchhoff Voltage Law) | tổng điện áp vòng kín = 0 |
| KCL (Kirchhoff Current Law) | tổng dòng điện tại nút = 0 |
| Voltage divider | `V_out = V_in * R2 / (R1 + R2)` |
| Current divider | `I1 = I_total * R2 / (R1 + R2)` |

### Domain: electrostatics (tĩnh điện)

| Topic | Công thức cần có |
|---|---|
| Capacitor charge | `Q = C * V` |
| Capacitor energy | `E = 0.5 * C * V**2` |
| Series capacitance | `1/C_total = 1/C1 + 1/C2` |
| Parallel capacitance | `C_total = C1 + C2` |
| Electric field | `E_field = V / d` |
| Coulomb's law | `F = k * q1 * q2 / r**2` |
| Electric potential energy | `U = k * q1 * q2 / r` |
| Capacitor with dielectric | `C = epsilon * A / d` |

---

## Yêu cầu về `keywords`

Keywords là thứ RAG dùng để match câu hỏi → công thức. Cần cover đủ các cách diễn đạt:

```json
// Ví dụ tốt cho Ohm's law
"keywords": [
  "resistance", "voltage", "current",
  "Ohm's law", "Ohm", "ohm",
  "V = IR", "V=IR",
  "calculate resistance", "find voltage", "find current",
  "resistor", "R", "I", "V"
]

// Ví dụ thiếu — không đủ để retrieval
"keywords": ["resistance"]
```

**Nguyên tắc:**
- Tối thiểu 5 keywords mỗi document
- Include cả tên đầy đủ lẫn ký hiệu (`resistance` và `R`)
- Include các dạng câu hỏi phổ biến (`calculate`, `find`, `determine`)
- Include tên định luật nếu có (`Ohm's law`, `Kirchhoff`)

---

## Yêu cầu về `unit_conversions`

Liệt kê tất cả conversion thường gặp cho các biến trong công thức:

```json
// Ví dụ cho công thức capacitor
"unit_conversions": [
  "μF → 1e-6 F",
  "mF → 1e-3 F",
  "nF → 1e-9 F",
  "mJ → 1e-3 J",
  "kV → 1e3 V",
  "mV → 1e-3 V"
]
```

Các prefix thường xuất hiện trong dataset: `m` (milli), `k` (kilo), `M` (mega), `μ` (micro), `n` (nano)

---

## Nguồn data gợi ý

Theo thứ tự ưu tiên:

1. **Training data của cuộc thi** — field `cot` chứa các bước giải có ghi rõ công thức dùng. Đây là nguồn sát nhất với dạng bài thi.

2. **Source materials từ BTC** — ban tổ chức hứa công bố tại kick-off workshop (04/05). Nếu chưa nhận được, email `ura.hcmut@gmail.com` để hỏi lại.

3. **Giáo trình vật lý điện học** — chương mạch điện và tĩnh điện của bất kỳ giáo trình đại cương nào. Chỉ cần lấy công thức, không cần toàn bộ nội dung.

---

## Tiêu chí tối thiểu để demo

Không cần đầy đủ ngay — chỉ cần đủ để pipeline không crash trong demo:

- [ ] **20–30 documents** cover các công thức phổ biến nhất
- [ ] Mỗi document có đủ 3 field bắt buộc quan trọng nhất: `formula_sympy`, `keywords`, `variables`
- [ ] `formula_sympy` của mỗi document test được bằng đoạn code sau trước khi commit:

```python
from sympy import symbols, sympify
try:
    expr = sympify("0.5 * C * U**2")  # thay bằng formula_sympy cần test
    print("✅ Valid")
except Exception as e:
    print(f"❌ Invalid: {e}")
```

- [ ] Phủ được ít nhất 1 công thức cho mỗi topic trong danh sách bên trên

---

## Output cần giao

1. **`data/rag/physics_formulas.json`** — file JSON chứa list tất cả documents theo format trên
2. **`data/rag/README.md`** — ghi rõ: số documents, topics đã cover, nguồn tham khảo (bắt buộc theo rules cuộc thi)

---

## Liên hệ

Nếu có câu hỏi về format hoặc cần ví dụ thêm, liên hệ người phụ trách pipeline (Người 3 — Type 2 Track theo DEMO_PLAN.md).

# Track 2 — Reference (Data · Formula Format · Gaps · Implementation Plan)

**Mục lục (gộp từ 4 file):**
- Track 2 — Physics Dataset Analysis  *(← `track2_data_info.md`)*
- PHYSICS_DATA.md — Yêu cầu Data Vật Lý cho Formula RAG  *(← `PHYSICS_DATA.md`)*
- Track 2 — Formula Gap Analysis  *(← `track2_formula_gaps.md`)*
- Track 2 — Physics Pipeline: Implementation Plan  *(← `track2_implementation_plan.md`)*

---

## Track 2 — Physics Dataset Analysis
> **File:** `Physics_Problems_Text_Only.csv`  
> **Mục đích:** SSOT mô tả cấu trúc, phân loại, và các đặc điểm kỹ thuật của dataset Type 2 — phục vụ thiết kế `physics_formulas.json`, `PhysicsClassifier`, `SympySolver`, và routing logic.

---

### 1. Tổng quan

| Chỉ số | Giá trị |
|--------|---------|
| **Tổng số bài toán** | 1,352 |
| **Columns** | `id`, `question`, `cot`, `answer`, `unit` |
| **Đáp án dạng số** | 1,256 (92.9%) |
| **Đáp án định tính / text** | 96 (7.1%) |
| **Đáp án Yes/No** | 21 (1.6%) |
| **Bài có nhiều đáp án** | 25 (1.8%) — dấu `;` phân tách trong `unit` |
| **Bài có yếu tố vector** | 276 (20.4%) |

**Cấu trúc ID:** Prefix chữ cái → phân loại topic. Không có field `idx` — chỉ dùng `id`.

---

### 2. Phân loại theo Prefix ID

#### 2.1 LD — Lực Coulomb & Điện trường (397 bài, 29.4%)

**Nội dung:** Tính lực tương tác tĩnh điện giữa các điện tích điểm (Coulomb), tính cường độ điện trường tại một điểm do nhiều điện tích gây ra.

**Đặc điểm kỹ thuật:**
- **232/397 bài có yếu tố vector** — cần cộng vector 2D (hướng lực, góc, hình học tam giác ABC)
- Công thức cốt lõi: `F = k|q1·q2|/r²`, `E = k|q|/r²`
- Bài phức tạp: 3 điện tích đặt tại 3 đỉnh tam giác → tính hợp lực trên q3
- Đáp án số: 393/397 | Định tính: 4

**Units chủ yếu:** N (245), V/m (139), N/C (3)

**Ví dụ:**
```
[LD001] Two charges q1=6×10⁻⁸C and q2=-6×10⁻⁸C at A,B (8 cm apart).
        q3=6×10⁻⁸C at C (CA=5cm, CB=3cm). Determine force on q3.
        → Answer: 0.05 N
```

---

#### 2.2 CH — Mạch RLC xoay chiều (290 bài, 21.4%)

**Nội dung:** Mạch điện AC với điện trở R, cuộn cảm L, tụ điện C. Tính trở kháng Z, công suất P, hệ số công suất cosφ, dòng/áp hiệu dụng.

**Sub-topics:**

| Sub-topic | Số bài | Ghi chú |
|-----------|--------|---------|
| Capacitor trong AC (XC, Q) | 96 | Bài phổ biến nhất |
| Điện áp (URL, UR, UL, UC) | 86 | |
| Cộng hưởng (resonance) | 28 | Giao nhau với CHLT |
| Impedance (Z) | 24 | |
| Dòng điện (I) | 24 | |
| Công suất (P, cosφ) | 12 | |
| Khác | 20 | Đồ thị, hệ số nhân ω |

**Đặc điểm:** Tất cả 290 bài đều có đáp án số (kể cả cosφ = 0.707 hay 1 vẫn là số).

**Units chủ yếu:** W (51), Ω (50), `-` (41 — cosφ không đơn vị), A (34), V (33)

**Ví dụ:**
```
[CH001] Resonant RLC circuit, impedance Z=40Ω. Determine pure resistance R.
        → Answer: 40 Ω
[CH152] u=200√2·cos(100πt) V, R=100Ω, L=1/π H, C=10⁻⁴/2π F. Find cosφ.
        → Answer: 0.707
```

---

#### 2.3 NL — Năng lượng điện từ (190 bài, 14.1%)

**Nội dung:** Năng lượng tích trữ trong tụ điện (WC), cuộn cảm (WL), mạch dao động LC. Tính điện dung, độ tự cảm, điện áp từ năng lượng.

**Đặc điểm kỹ thuật:**
- **26/190 bài định tính** — câu hỏi khái niệm về LC oscillation, năng lượng chuyển hóa
- Bài định tính thường hỏi: "khi I=0 thì năng lượng ở đâu?", "năng lượng tỉ lệ với đại lượng nào?"
- Có bài hàm theo thời gian: `U(t) = 120sin(2000t)` → tính `W_max`
- Đáp án số: 164/190 | Định tính: 26

**Units chủ yếu:** J (59), mJ (32), H (19), `-`/`—` (38 — định tính), V (13)

**Ví dụ định lượng:**
```
[NL001] C=20μF, U=100V. Calculate energy stored (mJ).
        → Answer: 100.00 mJ
```
**Ví dụ định tính:**
```
[NL025] LC circuit, when current is maximum, where is energy stored?
        → Answer: "all energy is entirely stored in the magnetic field of the inductor"
[NL305] Shape of graph: energy in capacitor vs voltage U?
        → Answer: "upward parabola"
```

---

#### 2.4 TD — Tụ điện cơ bản (177 bài, 13.1%)

**Nội dung:** Các bài toán cơ bản về tụ điện: tính điện tích Q, điện dung C, hiệu điện thế U, năng lượng W. Đơn giản hơn NL — chủ yếu áp công thức 1 bước.

**Công thức cốt lõi:** `Q = C·U`, `W = ½·C·U²`, `W = Q²/(2C)`, `C = ε·S/d`

**Đặc điểm:** Dùng đơn vị nhỏ (nano, pico) — cần unit conversion. 2 bài có multi-answer.

**Units chủ yếu:** nC (40), pF (40), nJ (35), V (16), μJ (10)

**Ví dụ:**
```
[TD401] C=100μF, U=30V. Calculate energy stored.
        → Answer: 0.045 J
[TD402] Q=3mC, U=30V. Calculate capacitance C.
        → Answer: 100 μF
```

---

#### 2.5 DDT — Điện từ cảm ứng (130 bài, 9.6%)

**Nội dung:** Solenoid, từ trường, suất điện động cảm ứng (EMF), thông lượng từ, tự cảm, mạch RLC có cuộn cảm.

**Sub-topics:**

| Sub-topic | Số bài | Ghi chú |
|-----------|--------|---------|
| Mạch RLC / Inductance | 43 | Z, I, P với L,C,R |
| Solenoid (từ trường) | 38 | B, n, I, l |
| Suất điện động cảm ứng | 23 | EMF, Faraday, flux |
| Khác | 21 | Năng lượng từ trường, định tính |
| Hệ số công suất | 5 | cosφ của mạch có L |

**Đặc điểm kỹ thuật:**
- **27/130 bài định tính** — đặc điểm của solenoid lý tưởng, quy tắc Lenz, ứng dụng
- CoT dài nhất dataset: **trung bình 6.8 bước**
- Bài tính mật độ năng lượng từ trường: `w = B²/(2μ₀)` (đơn vị J/m³)
- Có bài tính mật độ vòng dây: `n = N/l` (đơn vị turns/m)

**Units chủ yếu:** `—` (27 — định tính), V (14), Ω (12), T (10), Wb (10), mH (16), turns/m (7), J/m³ (4)

**Ví dụ:**
```
[DDT131] Solenoid: l=0.5m, N=1000 turns, I=2A. Calculate B inside.
         → Answer: 0.005 T
[DDT136] Magnetic field inside solenoid is proportional to? (qualitative)
         → Answer: "Number of turns density and current intensity"
```

---

#### 2.6 THCB — Sai số đo lường (80 bài, 5.9%) ⚠️ Ngoài dự kiến

**Nội dung:** Xử lý sai số trong thí nghiệm vật lý: sai số tuyệt đối, sai số tương đối, truyền sai số qua phép tính (R=U/I, P=UI, R_series...).

**Đặc điểm kỹ thuật — QUAN TRỌNG:**
- **23/80 bài có nhiều đáp án** (dấu `;` trong `answer` và `unit`) — nhóm multi-answer lớn nhất
- Công thức riêng biệt: `ΔR/R = ΔU/U + ΔI/I`, `ΔP/P = ΔU/U + ΔI/I`
- Sai số tuyệt đối của tổng: `Δ(R1+R2) = ΔR1 + ΔR2`
- Có bài kết hợp: vừa tính trị số vừa tính sai số → multi-answer
- Nhóm này **không dùng SymPy giải phương trình** — chỉ tính công thức tường minh

**Units chủ yếu:** `%` (32), `A` (12), `cm; %` (7), `Ω` (5), đơn vị kết hợp nhiều loại

**Ví dụ single-answer:**
```
[THCB001] Ammeter range=2A, least count=0.1A. Absolute error?
          → Answer: 0.1 A
[THCB002] Voltmeter: 0.2V least count, reads 5.6V. Relative error?
          → Answer: 3.57 %
```
**Ví dụ multi-answer:**
```
[THCB087] True value=50.0cm, measured=49.4cm.
          Calculate absolute error AND relative error.
          → Answer: 0.6; 1.2 | Unit: cm; %
[THCB066] U=9V, 2 lamps R=9Ω in parallel. Find I each lamp and total I.
          → Answer: I_D₁=1.0; I_D₂=1.0; I_total=2.0 | Unit: A; A; A
```

---

#### 2.7 DT — Điện trường tại điểm (68 bài, 5.0%)

**Nội dung:** Tính cường độ điện trường E tại một điểm M do nhiều điện tích gây ra. Tương tự LD nhưng tập trung vào E-field thay vì lực F.

**Đặc điểm kỹ thuật:**
- **25/68 bài có yếu tố vector** — cộng vector E₁ và E₂ tại điểm M
- Bài đặc biệt: tính vị trí điểm có E=0 → `find` là tọa độ (đơn vị cm)
- Đáp án số: 64/68 | Định tính: 4

**Units chủ yếu:** V/m (31), N/C (12), C (9), cm (8 — vị trí), N (3)

**Ví dụ:**
```
[DT001] q1=q2=16×10⁻⁸C tại A,B (10cm). Find E tại trung điểm.
        → Answer: 0 V/m   (đối xứng → triệt tiêu)
[DT002] Same setup. Find E tại N (NA=NB=10cm).
        → Answer: 640000 V/m
```

---

#### 2.8 CHLT — Cộng hưởng RLC Yes/No (20 bài, 1.5%)

**Nội dung:** Cho mạch RLC (R, L, C) và tần số f. Hỏi: có cộng hưởng không?

**Đặc điểm kỹ thuật:**
- **Toàn bộ 20 bài đều trả lời Yes / No** — không có đáp án số
- Logic: tính `f₀ = 1/(2π√(LC))`, so sánh với f đề bài → Yes nếu bằng nhau
- CoT dài nhất dataset: **trung bình 8.8 bước** (kiểm tra kỹ từng điều kiện)
- Cần routing đặc biệt: không dùng SymPy `solve()` — chỉ so sánh giá trị

**Units chủ yếu:** `-` (20 — tất cả)

**Ví dụ:**
```
[CHLT001] R=50Ω, L=0.5H, C=20μF, f=40Hz. Resonance?
          → f₀ = 1/(2π√(0.5×20×10⁻⁶)) ≈ 50.3 Hz ≠ 40 Hz → Answer: No
[CHLT002] R=10Ω, L=0.4H, C=50μF, f=35.6Hz. Resonance?
          → f₀ ≈ 35.6 Hz ≈ f → Answer: Yes
```

---

### 3. Ma trận tổng hợp

| Prefix | Bài | % | Số | Định tính | Yes/No | Multi-ans | Vector | CoT avg |
|--------|-----|---|----|-----------|--------|-----------|--------|---------|
| LD | 397 | 29.4% | 393 | 4 | 0 | 0 | **232** | 5.2 |
| CH | 290 | 21.4% | 290 | 0 | 0 | 0 | 19 | 4.2 |
| NL | 190 | 14.1% | 164 | **26** | 0 | 0 | 0 | 4.8 |
| TD | 177 | 13.1% | 173 | 4 | 0 | 2 | 0 | 4.1 |
| DDT | 130 | 9.6% | 103 | **27** | 1 | 0 | 0 | **6.8** |
| THCB | 80 | 5.9% | 69 | 11 | 0 | **23** | 0 | 4.0 |
| DT | 68 | 5.0% | 64 | 4 | 0 | 0 | 25 | 5.2 |
| CHLT | 20 | 1.5% | 0 | 0 | **20** | 0 | 0 | **8.8** |
| **Tổng** | **1,352** | 100% | **1,256** | **76** | **21** | **25** | **276** | — |

---

### 4. Danh sách đơn vị (units) trong dataset

```
Số học:    Ω, A, V, W, N, J, T, H, C, Hz
Nhỏ:       mJ, mH, mT, mN, mC, nC, nJ, nF, pF, μC, μF, μJ, μWb, kV/m
Tỉ lệ:    %, turns/m, J/m³, rad, rad/s
Vị trí:   cm, mm, m, degree
Không đơn vị: - , — (cosφ, định tính)
Kết hợp (multi-answer): cm; %, A; A, μC; μJ, V; V, ...
Đặc biệt: lần (số lần thay đổi), times
```

---

### 5. Tác động đến Implementation

#### 5.1 Routing cần bổ sung

```python
# Hiện tại (SYSTEM.md) chỉ có:
PHYSICS_KEYWORDS = {"calculate", "resistance", "voltage", ...}

# Cần thêm keywords cho các nhóm mới:
COULOMB_KEYWORDS = {"charge", "coulomb", "electric force", "q1", "q2", "placed at"}
INDUCTION_KEYWORDS = {"solenoid", "flux", "induced", "emf", "faraday", "self-inductance"}
ERROR_KEYWORDS = {"absolute error", "relative error", "least count", "uncertainty", "measured"}
RESONANCE_KEYWORDS = {"resonance", "resonant", "does the circuit experience"}
```

#### 5.2 Answer-type detection

Cần detect loại answer trước khi gọi SymPy:

```python
def detect_answer_type(question: str, parsed: dict) -> str:
    q_lower = question.lower()
    # Yes/No
    if any(kw in q_lower for kw in ["does the circuit", "is the circuit", "does it", "will it"]):
        return "yes_no"
    # Định tính
    if any(kw in q_lower for kw in ["where is", "what happens", "which of", "shape of graph",
                                      "directly proportional", "characteristic"]):
        return "qualitative"
    # Multi-answer
    if any(kw in q_lower for kw in ["calculate the", "find both", "and the"]):
        return "multi_numeric"  # cần verify
    return "numeric"
```

#### 5.3 Vector solving (LD + DT — 257 bài)

SymPy cần module riêng cho vector:

```python
from sympy.vector import CoordSys3D
# Hoặc đơn giản hơn: dùng sympy.sqrt và sympy.atan2
# F_net = sqrt(F1x + F2x)² + (F1y + F2y)²)
```

Cần xác định hình học (tam giác, góc α) từ CoT — đây là phần phức tạp nhất.

#### 5.4 Multi-answer format

Khi `answer` chứa `;`, response API cần format:
```json
{
  "answer": "0.6 cm; 1.2%",
  "explanation": "Absolute error = 0.6 cm. Relative error = 1.2%.",
  "cot": ["Step 1: ...", "Step 2: ..."]
}
```

#### 5.5 Công thức cần có trong `physics_formulas.json`

| Nhóm | Công thức ưu tiên |
|------|------------------|
| LD/DT | Coulomb, E-field, vector superposition |
| CH | Z = √(R²+(XL-XC)²), XL=ωL, XC=1/ωC, P=UI·cosφ, cosφ=R/Z |
| NL | WC=½CU², WL=½LI², Q=C·U |
| TD | Q=C·U, W=½CU²=Q²/2C, C=ε·S/d |
| DDT | B=μ₀·n·I, EMF=ΔΦ/Δt, L=μ₀·n²·V, w=B²/2μ₀ |
| THCB | ΔR/R=ΔU/U+ΔI/I, Δ(A+B)=ΔA+ΔB, δ=Δx/x·100% |
| CHLT | f₀=1/(2π√(LC)), condition: f == f₀ |

#### 5.6 PhysicsQuestionType — cần mở rộng enum

```python
class PhysicsQuestionType(Enum):
    SINGLE_FORMULA   = "single_formula"   # TD, NL đơn giản
    MULTI_STEP       = "multi_step"        # CH, DDT nhiều bước
    CIRCUIT          = "circuit"           # CH mạch RLC
    ELECTROSTATIC    = "electrostatic"     # LD lực Coulomb, DT điện trường
    VECTOR           = "vector"            # LD/DT có cộng vector ← MỚI
    YES_NO           = "yes_no"            # CHLT ← MỚI
    QUALITATIVE      = "qualitative"       # NL/DDT định tính ← MỚI
    MULTI_ANSWER     = "multi_answer"      # THCB ← MỚI
    ERROR_CALC       = "error_calc"        # THCB sai số ← MỚI
    ELECTROMAGNETIC  = "electromagnetic"   # DDT cảm ứng ← MỚI
```

---

### 6. Mức độ khó theo nhóm (để ưu tiên implement)

| Nhóm | Khó | Lý do | Ưu tiên |
|------|-----|-------|---------|
| TD | ⭐ | Công thức thẳng, 1 bước | P1 — làm trước |
| NL (numeric) | ⭐⭐ | Có unit conversion, đôi khi 2 bước | P1 |
| CHLT | ⭐⭐ | Logic Yes/No đơn giản nhưng cần detect | P1 |
| CH (impedance/power) | ⭐⭐ | Công thức RLC rõ ràng | P2 |
| DDT (solenoid) | ⭐⭐ | Công thức B solenoid thẳng | P2 |
| THCB | ⭐⭐ | Công thức đơn nhưng multi-answer phức | P2 |
| LD/DT (no vector) | ⭐⭐ | Coulomb 2 điện tích thẳng | P2 |
| NL (qualitative) | ⭐⭐⭐ | Cần LLM reasoning, không dùng SymPy | P3 |
| DDT (qualitative) | ⭐⭐⭐ | Idem | P3 |
| LD/DT (vector) | ⭐⭐⭐⭐ | Cộng vector 2D, hình học tam giác | P3 |
| CH (graph/ratio) | ⭐⭐⭐ | Trả lời dạng text mô tả đồ thị | P3 |

---

## PHYSICS_DATA.md — Yêu cầu Data Vật Lý cho Formula RAG

> **Người nhận:** Người phụ trách tìm kiếm và chuẩn bị data vật lý
> **Mục đích:** Build Vector DB (FAISS) phục vụ node ④b Formula RAG trong pipeline EXACT 2026
> **Ưu tiên:** Hoàn thành tối thiểu 20–30 documents trước khi demo pipeline

---

### Bối cảnh

Dataset Type 2 của cuộc thi gồm **5,520 bài toán vật lý** tập trung vào:
- Mạch điện (electric circuits): resistance, voltage, current, power
- Tĩnh điện (electrostatics): capacitance, electric fields, energy, charge

Trong pipeline, node **Formula RAG** nhận câu hỏi từ Physics Parser, tìm trong Vector DB công thức phù hợp, rồi trả về cho SymPy Solver tính toán. **Data chất lượng kém = RAG trả về sai công thức = toàn bộ track Type 2 sai.**

---

### Format mỗi document

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

### Mô tả từng field

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

### Lưu ý quan trọng về `formula_sympy`

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

### Danh sách topics cần cover

#### Domain: circuits (mạch điện)

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

#### Domain: electrostatics (tĩnh điện)

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

### Yêu cầu về `keywords`

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

### Yêu cầu về `unit_conversions`

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

### Nguồn data gợi ý

Theo thứ tự ưu tiên:

1. **Training data của cuộc thi** — field `cot` chứa các bước giải có ghi rõ công thức dùng. Đây là nguồn sát nhất với dạng bài thi.

2. **Source materials từ BTC** — ban tổ chức hứa công bố tại kick-off workshop (04/05). Nếu chưa nhận được, email `ura.hcmut@gmail.com` để hỏi lại.

3. **Giáo trình vật lý điện học** — chương mạch điện và tĩnh điện của bất kỳ giáo trình đại cương nào. Chỉ cần lấy công thức, không cần toàn bộ nội dung.

---

### Tiêu chí tối thiểu để demo

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

### Output cần giao

1. **`data/rag/physics_formulas.json`** — file JSON chứa list tất cả documents theo format trên
2. **`data/rag/README.md`** — ghi rõ: số documents, topics đã cover, nguồn tham khảo (bắt buộc theo rules cuộc thi)

---

### Liên hệ

Nếu có câu hỏi về format hoặc cần ví dụ thêm, liên hệ người phụ trách pipeline (Người 3 — Type 2 Track theo DEMO_PLAN.md).

---

## Track 2 — Formula Gap Analysis
> So sánh `physics_formulas.json` hiện tại (20 công thức) với toàn bộ dataset 1,352 bài toán.  
> Mục đích: xác định chính xác những công thức cần bổ sung để đạt coverage tối đa.

---

### 1. Tình trạng hiện tại

**File hiện có: 20 công thức — 2 domain:**

| Domain | Số công thức | Topics |
|--------|-------------|--------|
| `circuits` | 10 | ohms_law, series/parallel_resistance, power (×3), kvl, kcl, voltage_divider, current_divider |
| `electrostatics` | 10 | capacitor_charge/energy/dielectric, series/parallel_capacitance, electric_field_uniform, coulombs_law, electric_potential_energy/point, electric_field_point |

**Coverage ước tính với 20 công thức hiện tại:**

| Nhóm | Bài | Đã cover | Còn thiếu |
|------|-----|----------|-----------|
| TD (tụ điện cơ bản) | 177 | ~80% | ~35 bài |
| LD (Coulomb + E-field) | 397 | ~50% | ~199 bài |
| DT (điện trường điểm) | 68 | ~50% | ~34 bài |
| NL (năng lượng EM) | 190 | ~50% | ~95 bài |
| CH (RLC xoay chiều) | 290 | **0%** | 290 bài |
| CHLT (cộng hưởng) | 20 | **0%** | 20 bài |
| DDT (điện từ cảm ứng) | 130 | **0%** | 130 bài |
| THCB (sai số) | 80 | **0%** | 80 bài |
| **Tổng** | **1,352** | **~34.7%** | **~883 bài** |

> ⚠️ Với database hiện tại, pipeline chỉ giải được ~35% dataset. Cần bổ sung **32 công thức** mới (F-021…F-052). Sau khi đồng bộ tên domain với codebase (§5): chỉ **`ac_circuits`** là domain thật sự mới; `electromagnetism` và `measurement` codebase đã có (commit classifier 2026-05-31); `lc_oscillation` đã gộp vào `electromagnetism`.

---

### 2. Danh sách công thức cần bổ sung

#### DOMAIN MỚI: `ac_circuits` — Mạch RLC xoay chiều (cho CH + CHLT)
> ✅ **Review verdict:** HỢP LÝ giữ là domain mới. AC (trở kháng, dung/cảm kháng, cosφ)
> khác bản chất DC `circuits` (R thuần, ohm/KVL/KCL) → tách giúp retrieval không lẫn.
> ✅ **Đã đồng bộ codebase (2026-06-02):** `_detect_domain()` đã route CH/CHLT →
> `ac_circuits` (kw: impedance/reactance/rlc/alternating/power factor/resonance). CHLT
> thêm type `YES_NO`. Layer-1 retrieval sẽ khớp khi formula DB nhập `domain="ac_circuits"`.

##### F-021 | `inductive_reactance`
```
formula_sympy: X_L = omega * L
formula_latex:  X_L = \omega L = 2\pi f L
variables:      X_L (Ω), omega (rad/s), L (H), f (Hz)
unit_conversions: mH → 1e-3 H, μH → 1e-6 H, Hz → rad/s (×2π)
```
*Dùng cho:* CH bài tính X_L khi biết L và f. Là thành phần trong Z.

---

##### F-022 | `capacitive_reactance`
```
formula_sympy: X_C = 1 / (omega * C)
formula_latex:  X_C = \frac{1}{\omega C} = \frac{1}{2\pi f C}
variables:      X_C (Ω), omega (rad/s), C (F)
unit_conversions: μF → 1e-6 F, nF → 1e-9 F, pF → 1e-12 F
```
*Dùng cho:* CH tính X_C, tiền đề tính Z.

---

##### F-023 | `rlc_impedance`
```
formula_sympy: Z = sqrt(R**2 + (X_L - X_C)**2)
formula_latex:  Z = \sqrt{R^2 + (X_L - X_C)^2}
variables:      Z (Ω), R (Ω), X_L (Ω), X_C (Ω)
```
*Dùng cho:* CH tính tổng trở mạch RLC nối tiếp. **Công thức trung tâm của nhóm CH.**  
*Lưu ý:* Khi cộng hưởng X_L = X_C → Z = R.

---

##### F-024 | `ac_current_rms`
```
formula_sympy: I = U / Z
formula_latex:  I = \frac{U}{Z}
variables:      I (A), U (V), Z (Ω)
```
*Dùng cho:* CH tính dòng điện hiệu dụng từ U và Z.

---

##### F-025 | `ac_power_factor`
```
formula_sympy: cos_phi = R / Z
formula_latex:  \cos\varphi = \frac{R}{Z}
variables:      cos_phi (dimensionless), R (Ω), Z (Ω)
```
*Dùng cho:* CH tính hệ số công suất. Khi cộng hưởng cos_phi = 1.

---

##### F-026 | `ac_active_power`
```
formula_sympy: P = U * I * cos_phi
formula_latex:  P = UI\cos\varphi = I^2 R
variables:      P (W), U (V), I (A), cos_phi (dimensionless), R (Ω)
alternative:    P = I**2 * R
```
*Dùng cho:* CH tính công suất tiêu thụ mạch AC. Hai dạng tương đương.

---

##### F-027 | `rlc_voltage_components`
```
formula_sympy: U_R = I * R;  U_L = I * X_L;  U_C = I * X_C
formula_latex:  U_R = IR,\; U_L = IX_L,\; U_C = IX_C
variables:      U_R, U_L, U_C (V), I (A), R, X_L, X_C (Ω)
```
*Dùng cho:* CH tính điện áp thành phần trên từng phần tử.  
*Lưu ý:* U ≠ U_R + U_L + U_C (cộng vector, không cộng đại số).

---

##### F-028 | `rlc_resonance_frequency`
```
formula_sympy: f_0 = 1 / (2 * pi * sqrt(L * C))
formula_latex:  f_0 = \frac{1}{2\pi\sqrt{LC}}
alternative:    omega_0 = 1 / sqrt(L * C)
variables:      f_0 (Hz), L (H), C (F), omega_0 (rad/s)
```
*Dùng cho:* **CH** tính tần số cộng hưởng khi biết L và C.  
*Dùng cho:* **CHLT** — so sánh f_0 với f đề bài → Yes/No.  
*Logic CHLT:* `abs(f - f_0) < tolerance` → "Yes", else "No".

---

##### F-029 | `ac_resonance_condition`
```
formula_sympy: X_L == X_C  →  resonance (Z = R, cos_phi = 1, I_max)
logic:         f_resonance = 1 / (2 * pi * sqrt(L * C))
               is_resonance = abs(f - f_resonance) < 0.5
```
*Dùng cho:* **CHLT** (toàn bộ 20 bài Yes/No). Đây là "formula" dạng điều kiện, không phải phương trình giải.

---

##### F-030 | `capacitance_from_resonance`
```
formula_sympy: C = 1 / (omega**2 * L)
formula_latex:  C = \frac{1}{\omega_0^2 L}
variables:      C (F), omega (rad/s), L (H)
```
*Dùng cho:* CH bài tính C cần thiết để đạt cộng hưởng tại f cho trước (CH063, CH092).

---

#### DOMAIN `electromagnetism` — Điện từ: cảm ứng + năng lượng (cho DDT + NL)
> ✅ Tên khớp codebase (`type2_classifier._detect_domain`). Domain này gộp luôn cả
> nhóm LC oscillation bên dưới (xem §5 verdict). DDT (cảm ứng) + NL (năng lượng EM/LC).

##### F-031 | `solenoid_magnetic_field`
```
formula_sympy: B = mu_0 * n * I
formula_latex:  B = \mu_0 n I,\; n = N/l
variables:      B (T), mu_0 = 4π×10⁻⁷ (H/m), n (turns/m), I (A)
derived:        n = N / l  (turn density từ N turns, length l)
unit_conversions: cm → 1e-2 m, mT → 1e-3 T
```
*Dùng cho:* DDT tính từ trường trong lòng solenoid — **38 bài DDT**.

---

##### F-032 | `solenoid_turn_density`
```
formula_sympy: n = N / l
formula_latex:  n = \frac{N}{l}
variables:      n (turns/m), N (số vòng), l (m)
```
*Dùng cho:* DDT135 và các bài tính mật độ vòng dây trước khi dùng F-031.

---

##### F-033 | `magnetic_flux`
```
formula_sympy: Phi = B * A * cos(theta)
formula_latex:  \Phi = BA\cos\theta
variables:      Phi (Wb), B (T), A (m²), theta (rad) — thường theta=0 → cos=1
unit_conversions: cm² → 1e-4 m², μWb → 1e-6 Wb
```
*Dùng cho:* DDT tính từ thông qua 1 vòng dây hoặc toàn solenoid (DDT141, DDT213, DDT383).

---

##### F-034 | `induced_emf_self_induction`
```
formula_sympy: EMF = -L * (dI / dt)
formula_sympy_approx: EMF = L * delta_I / delta_t   (khi ΔI/Δt đều)
formula_latex:  \mathcal{E} = -L \frac{dI}{dt}
variables:      EMF (V), L (H), delta_I (A), delta_t (s)
```
*Dùng cho:* DDT tính suất điện động tự cảm khi biết L và tốc độ biến thiên dòng — **DDT142, 144, 148, 154** và nhiều bài tương tự.  
*Lưu ý:* Dấu âm chỉ chiều, bài toán thường hỏi magnitude → dùng `abs()`.

---

##### F-035 | `induced_emf_faraday`
```
formula_sympy: EMF = -N * delta_Phi / delta_t
formula_sympy_approx: EMF = delta_Phi / delta_t   (N=1 vòng)
formula_latex:  \mathcal{E} = -N\frac{\Delta\Phi}{\Delta t}
variables:      EMF (V), N (vòng), delta_Phi (Wb), delta_t (s)
```
*Dùng cho:* DDT150 tính EMF từ biến thiên từ thông.

---

##### F-036 | `solenoid_inductance`
```
formula_sympy: L = mu_0 * (N**2 / l) * A
formula_latex:  L = \mu_0 \frac{N^2}{l} A = \mu_0 n^2 V
variables:      L (H), mu_0 = 4π×10⁻⁷, N (vòng), l (m), A (m²)
unit_conversions: cm² → 1e-4 m², mH → 1e-3 H
```
*Dùng cho:* DDT133 tính độ tự cảm solenoid từ kích thước hình học.

---

##### F-037 | `inductor_energy`
```
formula_sympy: W_L = 0.5 * L * I**2
formula_latex:  W_L = \frac{1}{2}LI^2
variables:      W_L (J), L (H), I (A)
unit_conversions: mJ → 1e-3 J, μJ → 1e-6 J
```
*Dùng cho:* DDT134, DDT147, DDT151 và toàn bộ nhóm **NL (inductor energy) — ~95 bài**.  
> ⚡ Đây là công thức thiếu có impact lớn nhất: cover cả DDT lẫn NL.

---

##### F-038 | `magnetic_energy_density`
```
formula_sympy: w = B**2 / (2 * mu_0)
formula_latex:  w = \frac{B^2}{2\mu_0}
variables:      w (J/m³), B (T), mu_0 = 4π×10⁻⁷
```
*Dùng cho:* DDT139, DDT379 tính mật độ năng lượng từ trường trong solenoid.

---

#### ~~DOMAIN MỚI `lc_oscillation`~~ → GỘP VÀO `electromagnetism` — Mạch dao động LC (cho NL + DDT)
> ⚠️ **Review verdict:** KHÔNG tạo domain riêng `lc_oscillation`. Lý do: (1) trùng
> vật lý với `electromagnetism` (cuộn cảm + năng lượng từ), (2) F-040 trùng hệt F-028
> (`f = 1/(2π√(LC))`). Các công thức dưới đây gán `domain = electromagnetism`. Cân nhắc
> BỎ F-040 (dùng lại F-028) để tránh 1 công thức nằm 2 domain.

##### F-039 | `lc_total_energy`
```
formula_sympy: W_total = 0.5 * C * U_max**2
formula_sympy_alt: W_total = 0.5 * L * I_max**2
formula_latex:  W = \frac{1}{2}CU_{max}^2 = \frac{1}{2}LI_{max}^2
variables:      W_total (J), C (F), U_max (V), L (H), I_max (A)
```
*Dùng cho:* NL024 và các bài tính tổng năng lượng dao động LC.

---

##### F-040 | `lc_oscillation_frequency`
```
formula_sympy: f = 1 / (2 * pi * sqrt(L * C))
formula_sympy_alt: omega = 1 / sqrt(L * C)
formula_latex:  f = \frac{1}{2\pi\sqrt{LC}},\; \omega = \frac{1}{\sqrt{LC}}
variables:      f (Hz), omega (rad/s), L (H), C (F)
```
*Dùng cho:* NL tính tần số dao động LC (nếu hỏi). Dùng chung công thức với F-028.

---

##### F-041 | `lc_energy_partition`
```
formula_sympy: W_C = 0.5 * C * u**2;  W_L = 0.5 * L * i**2;  W_C + W_L = W_total
formula_latex:  W_C + W_L = const
logic:          khi i=0 → W_L=0 → W_C=W_total (tất cả ở tụ)
                khi u=0 → W_C=0 → W_L=W_total (tất cả ở cuộn)
```
*Dùng cho:* NL định tính — câu hỏi "khi I=0 năng lượng ở đâu?" → W_L = 0, W_C = W_total.  
*Lưu ý:* Đây là "formula" kết hợp với logic, không phải phương trình giải thông thường.

---

##### F-042 | `lc_current_at_equal_energy`
```
formula_sympy: i = I_max / sqrt(2)  (khi W_C = W_L = W_total/2)
formula_latex:  i = \frac{I_{max}}{\sqrt{2}} \approx 0.707 I_{max}
```
*Dùng cho:* NL030 — tính i khi W_C = W_L (70.7% dòng cực đại).

---

#### DOMAIN `measurement` — Sai số đo lường (cho THCB)
> ✅ Tên khớp codebase (`type2_classifier._detect_domain`).

##### F-043 | `absolute_error_instrument`
```
formula_sympy: delta_x = least_count / 2   (hoặc = least_count nếu đề cho trực tiếp)
formula_natural: Sai số dụng cụ = ½ độ chia nhỏ nhất
variables:      delta_x, least_count (cùng đơn vị đo)
```
*Dùng cho:* THCB001, THCB002 — sai số tuyệt đối từ độ chia nhỏ nhất dụng cụ.

---

##### F-044 | `relative_error`
```
formula_sympy: delta_rel = (delta_x / x) * 100
formula_latex:  \delta = \frac{\Delta x}{x} \times 100\%
variables:      delta_rel (%), delta_x (sai số tuyệt đối), x (giá trị đo)
```
*Dùng cho:* THCB002, THCB010, THCB122, THCB124, THCB132 — tính sai số tương đối.

---

##### F-045 | `error_propagation_product`
```
formula_sympy: delta_rel_Z = delta_rel_A + delta_rel_B   (Z = A * B hoặc Z = A / B)
formula_latex:  \frac{\Delta Z}{Z} = \frac{\Delta A}{A} + \frac{\Delta B}{B}
variables:      delta_rel_Z, delta_rel_A, delta_rel_B (%)
example:        R = U/I → ΔR/R = ΔU/U + ΔI/I
```
*Dùng cho:* THCB003, THCB005, THCB008 — truyền sai số qua nhân/chia.

---

##### F-046 | `error_propagation_sum`
```
formula_sympy: delta_Z = delta_A + delta_B   (Z = A + B hoặc Z = A - B)
formula_latex:  \Delta Z = \Delta A + \Delta B
variables:      delta_Z, delta_A, delta_B (cùng đơn vị)
example:        R_total = R1 + R2 → ΔR_total = ΔR1 + ΔR2
```
*Dùng cho:* THCB009 — sai số tổng điện trở nối tiếp.

---

##### F-047 | `mean_absolute_error`
```
formula_sympy: x_mean = sum(x_i) / n
               delta_mean = sum(abs(x_i - x_mean)) / n
formula_latex:  \bar{x} = \frac{\sum x_i}{n},\; \overline{\Delta x} = \frac{\sum|x_i - \bar{x}|}{n}
```
*Dùng cho:* THCB007, THCB023, THCB118, THCB123 — tính trung bình và sai số ngẫu nhiên từ nhiều lần đo.

---

##### F-048 | `absolute_error_from_true`
```
formula_sympy: delta_x = abs(x_measured - x_true)
formula_latex:  \Delta x = |x_{measured} - x_{true}|
```
*Dùng cho:* THCB006, THCB087 — sai số tuyệt đối khi biết giá trị thực.

---

#### BỔ SUNG VÀO DOMAIN `electrostatics` — Cho LD + DT vector

##### F-049 | `coulomb_force_vector_superposition`
```
formula_sympy: F_net = sqrt(F1**2 + F2**2 + 2*F1*F2*cos(alpha))
formula_latex:  F_{net} = \sqrt{F_1^2 + F_2^2 + 2F_1F_2\cos\alpha}
variables:      F_net (N), F1, F2 (N), alpha (rad) — góc giữa hai lực
special_cases:
  alpha=0   → F_net = F1 + F2            (cùng chiều)
  alpha=π   → F_net = abs(F1 - F2)       (ngược chiều)
  alpha=π/2 → F_net = sqrt(F1²+F2²)     (vuông góc)
  alpha=π/3 (60°) → F_net = sqrt(F1²+F2²+F1·F2)
```
*Dùng cho:* LD008–LD013 và đa số bài LD/DT có 2+ điện tích — **232 bài vector**.  
> ⚡ Công thức impact lớn thứ 2 sau F-037.

---

##### F-050 | `electric_field_superposition`
```
formula_sympy: E_net = sqrt(E1**2 + E2**2 + 2*E1*E2*cos(alpha))
formula_latex:  E_{net} = \sqrt{E_1^2 + E_2^2 + 2E_1E_2\cos\alpha}
variables:      E_net (V/m), E1, E2 (V/m), alpha (rad)
```
*Dùng cho:* DT bài tính E tổng tại điểm M do nhiều điện tích gây ra.

---

##### F-051 | `zero_field_position`
```
formula_natural: Điểm có E=0 nằm trên đường nối hai điện tích
formula_sympy:   k*q1/x**2 = k*q2/(d-x)**2  → solve for x
                 x: khoảng cách từ q1 đến điểm cần tìm
                 d: khoảng cách q1-q2
variables:       x (m), d (m), q1, q2 (C)
condition:       cùng dấu → điểm giữa; trái dấu → ngoài đoạn
```
*Dùng cho:* DT bài tìm vị trí điểm có E=0 (đơn vị cm).

---

##### F-052 | `capacitor_energy_from_charge`
```
formula_sympy: W = Q**2 / (2 * C)
formula_latex:  W = \frac{Q^2}{2C}
variables:      W (J), Q (C), C (F)
```
*Dùng cho:* TD bài cho Q, hỏi W — dạng thứ 3 của công thức năng lượng tụ điện (F-012 cho C,V; F-052 cho Q,C).

---

### 3. Tổng hợp — 32 công thức cần thêm

| ID | Topic | Domain | Impact (bài) | Ưu tiên |
|----|-------|--------|-------------|---------|
| F-021 | inductive_reactance | ac_circuits | CH ~290 | 🔴 P1 |
| F-022 | capacitive_reactance | ac_circuits | CH ~290 | 🔴 P1 |
| F-023 | rlc_impedance | ac_circuits | CH ~290 | 🔴 P1 |
| F-024 | ac_current_rms | ac_circuits | CH ~150 | 🔴 P1 |
| F-025 | ac_power_factor | ac_circuits | CH ~80 | 🔴 P1 |
| F-026 | ac_active_power | ac_circuits | CH ~60 | 🔴 P1 |
| F-027 | rlc_voltage_components | ac_circuits | CH ~100 | 🔴 P1 |
| F-028 | rlc_resonance_frequency | ac_circuits | CH+CHLT ~80 | 🔴 P1 |
| F-029 | ac_resonance_condition | ac_circuits | CHLT 20 | 🔴 P1 |
| F-030 | capacitance_from_resonance | ac_circuits | CH ~20 | 🟡 P2 |
| F-031 | solenoid_magnetic_field | electromagnetism | DDT ~38 | 🔴 P1 |
| F-032 | solenoid_turn_density | electromagnetism | DDT ~15 | 🟡 P2 |
| F-033 | magnetic_flux | electromagnetism | DDT ~20 | 🟡 P2 |
| F-034 | induced_emf_self_induction | electromagnetism | DDT ~40 | 🔴 P1 |
| F-035 | induced_emf_faraday | electromagnetism | DDT ~10 | 🟡 P2 |
| F-036 | solenoid_inductance | electromagnetism | DDT ~10 | 🟡 P2 |
| F-037 | inductor_energy | electromagnetism | DDT+NL ~130 | 🔴 P1 |
| F-038 | magnetic_energy_density | electromagnetism | DDT ~10 | 🟢 P3 |
| F-039 | lc_total_energy | electromagnetism | NL ~30 | 🟡 P2 |
| F-040 | lc_oscillation_frequency | electromagnetism | NL/DDT ~20 | 🟡 P2 |
| F-041 | lc_energy_partition | electromagnetism | NL ~26 (qualitative) | 🟡 P2 |
| F-042 | lc_current_at_equal_energy | electromagnetism | NL ~5 | 🟢 P3 |
| F-043 | absolute_error_instrument | measurement | THCB ~30 | 🔴 P1 |
| F-044 | relative_error | measurement | THCB ~35 | 🔴 P1 |
| F-045 | error_propagation_product | measurement | THCB ~20 | 🔴 P1 |
| F-046 | error_propagation_sum | measurement | THCB ~10 | 🟡 P2 |
| F-047 | mean_absolute_error | measurement | THCB ~15 | 🟡 P2 |
| F-048 | absolute_error_from_true | measurement | THCB ~10 | 🟡 P2 |
| F-049 | coulomb_force_vector_superposition | electrostatics | LD ~232 | 🔴 P1 |
| F-050 | electric_field_superposition | electrostatics | DT ~25 | 🟡 P2 |
| F-051 | zero_field_position | electrostatics | DT ~10 | 🟢 P3 |
| F-052 | capacitor_energy_from_charge | electrostatics | TD ~20 | 🟡 P2 |

**Tổng: 32 công thức cần thêm** (20 hiện có + 32 mới = **52 công thức**)

---

### 4. Coverage sau khi bổ sung

| Nhóm | Trước | Sau | Ghi chú |
|------|-------|-----|---------|
| TD | ~80% | ~95% | F-052 thêm dạng W=Q²/2C |
| LD | ~50% | ~80% | F-049 vector; vẫn còn ~20% bài hình học phức tạp |
| DT | ~50% | ~80% | F-050, F-051 |
| NL | ~50% | ~90% | F-037 inductor_energy là key |
| CH | 0% | ~85% | F-021 đến F-030 |
| CHLT | 0% | ~100% | F-028, F-029 đủ giải toàn bộ |
| DDT | 0% | ~75% | F-031–F-038; ~25% còn là định tính (LLM) |
| THCB | 0% | ~85% | F-043–F-048 |
| **Tổng** | **~35%** | **~85%** | Còn ~15% cần LLM fallback (định tính, vector phức tạp) |

---

### 5. Domain chuẩn (canonical) — đồng bộ với codebase

> Tên domain trong file này đã chỉnh để **khớp `type2_classifier._detect_domain()`**.
> `electromagnetism` và `measurement` **không còn là "mới"** — codebase đã có sau commit
> classifier (2026-05-31). Chỉ `ac_circuits` là domain thật sự mới cần thêm vào classifier.

```python
# Canonical domain set (5) — formula_rag matchs doc["domain"] == parsed["domain"]
CANONICAL_DOMAINS = [
    "circuits",          # DC: R thuần, ohm/KVL/KCL, series/parallel   — codebase ✅
    "ac_circuits",       # RLC AC: X_L/X_C/Z/cosφ/resonance (CH, CHLT)  — MỚI, cần thêm vào classifier
    "electrostatics",    # Coulomb, E-field, tụ điện (LD, DT, TD)       — codebase ✅ (mở rộng F-049..F-052)
    "electromagnetism",  # cảm ứng + năng lượng EM/LC (DDT, NL)         — codebase ✅ (gồm cả lc_oscillation)
    "measurement",       # sai số đo lường (THCB)                       — codebase ✅
]
```

#### ⚠️ Cảnh báo nhất quán cho người thu thập data

1. ✅ **LLM parser đã emit đủ 5 domain (2026-06-02).** `PHYSICS_PARSE_PROMPT`
   (`llm/prompt_templates.py`) đã liệt kê `circuits | ac_circuits | electrostatics |
   electromagnetism | measurement` + 5 few-shot examples. Ngoài ra `physics_parser_node`
   đã có regex pre-pass deterministic + classifier prior (5 domain) → `parsed["domain"]`
   nay phủ đủ domain mới. Layer-1 keyword match kích hoạt khi formula DB dùng cùng tên domain.
2. **Layer-1 còn cần `find in doc["variables"]`.** Khi nhập formula, đảm bảo key
   `variables` chứa đúng ký hiệu biến cần tìm (vd `Z`, `X_L`, `EMF`, `cos_phi`) khớp
   với `target_variable` mà classifier sinh ra (đã thêm Z/EMF/T/cos_phi).
3. **Rebuild FAISS** sau khi sửa JSON: `python scripts/build_faiss_index.py`. Chạy
   `python tests/physics_formula.py` trước để bắt lỗi cú pháp `formula_sympy`.

### 6. Thứ tự implement (theo impact)

```
Batch 1 — P1 (9 công thức, ~450 bài mới được cover):
  F-037 inductor_energy          (+130 NL+DDT)
  F-049 vector_superposition     (+200 LD)
  F-031 solenoid_magnetic_field  (+38 DDT)
  F-034 induced_emf              (+40 DDT)
  F-043 absolute_error           (+30 THCB)
  F-044 relative_error           (+35 THCB)
  F-045 error_propagation_product(+20 THCB)
  F-021/022/023 XL,XC,Z RLC     (+100 CH)

Batch 2 — P1 AC circuits (6 công thức, ~180 bài CH còn lại):
  F-024 ac_current_rms
  F-025 ac_power_factor
  F-026 ac_active_power
  F-027 rlc_voltage_components
  F-028 resonance_frequency      (+20 CHLT)
  F-029 resonance_condition      (CHLT hoàn thiện)

Batch 3 — P2 (phần còn lại):
  F-033/035/036/038 DDT còn lại
  F-039/040/041 LC oscillation (domain=electromagnetism; cân nhắc bỏ F-040 trùng F-028)
  F-046/047/048 THCB còn lại
  F-050/051/052 electrostatics bổ sung
```

---

### 7. Review verdict (2026-05-31) — đồng bộ tên domain với codebase

Tóm tắt review file gốc (Claude web) so với codebase:

| Domain trong file gốc | Xử lý | Lý do |
|---|---|---|
| `circuits` | giữ | khớp codebase (DC) |
| `electrostatics` | giữ | khớp codebase |
| `electromagnetic_induction` | **rename → `electromagnetism`** | trùng domain codebase; tên codebase là umbrella rộng hơn (cảm ứng + năng lượng), hợp với cả DDT lẫn NL |
| `measurement_errors` | **rename → `measurement`** | trùng domain codebase |
| `lc_oscillation` | **fold → `electromagnetism`** | trùng vật lý (cuộn cảm/năng lượng từ); F-040 trùng hệt F-028 |
| `ac_circuits` | **giữ là domain MỚI** | AC (Z/X_L/X_C/cosφ) khác bản chất DC; tách tốt cho retrieval. CH+CHLT = 310 bài |

**Domain set chuẩn = 5:** `circuits`, `ac_circuits`, `electrostatics`, `electromagnetism`, `measurement`.

#### TODO đồng bộ codebase (để 32 formula này dùng được)
- [x] **Classifier:** thêm `ac_circuits` vào `_detect_domain()` — route CH/CHLT (kw: `reactance`, `impedance`, `ac`, `alternating`, `power factor`, `resonance`, `RLC`) sang `ac_circuits` thay vì `circuits`. ✅ done 2026-06-02
- [x] **LLM prompt:** cập nhật `PHYSICS_PARSE_PROMPT` (`llm/prompt_templates.py`) liệt kê đủ 5 domain — nếu không, pipeline `--use-llm` luôn emit `circuits`/`electrostatics` và Layer-1 cho domain mới không kích hoạt (chỉ FAISS cứu). ✅ done 2026-06-02 (kèm 5 few-shot examples)
- [ ] **Formula DB:** khi nhập, đặt `domain` đúng 1 trong 5 tên chuẩn; `variables` chứa ký hiệu cần tìm khớp `target_variable`.
- [ ] **Cân nhắc bỏ F-040** (dùng lại F-028) để tránh 1 công thức nằm 2 domain.
- [ ] Sau khi nhập: `python tests/physics_formula.py` → `python scripts/build_faiss_index.py`.

---

## Track 2 — Physics Pipeline: Implementation Plan

**Scope:** Build all stub files under `pipeline/type2/` into a working pipeline.  
**Deadline:** Competition active phase ends 2026-05-30. Target: functional baseline by 2026-05-24.  
**Constraint:** All LLM inference must use local open-source models ≤8B params. No closed-source API calls.

---

### 1. Pipeline Overview

```
HTTP Request
    │
    ▼  (Router classified query_type = "type2")
[3b] PhysicsParser       ← LLM extracts variables + identifies domain/formula hints
    │
    ▼
[4b] FormulaRAG          ← Hybrid retrieval: keyword match → FAISS (no LangChain)
    │
    ▼
[5b] SympySolver         ← SymPy solves by PhysicsQuestionType strategy
    │
    ▼
[6b] SelfVerifier        ← Wraps type2_validation.validate_sympy_result()
    │
    ▼
[6c] CotBuilder          ← Pure string formatting from solver steps (no LLM)
    │
    ▼
[7]  ExplainerAgent      ← LLM narrates explanation from SolverResult
    │
    ▼
[8]  ResponseBuilder     ← Pack JSON: {answer, explanation, cot, confidence}
```

**State fields used by Track 2** (defined in `pipeline/state.py` — do not redefine):

```python
# Input
question: str
query_type: str                     # "type2"

# Track 2
parsed_physics: Optional[dict]      # output of PhysicsParser
sympy_result: Optional[dict]        # output of SympySolver
cot: Optional[list[str]]            # output of CotBuilder

# Shared output
answer: Optional[str]
explanation: Optional[str]
confidence: Optional[float]
solver_result: Optional[SolverResult]
```

---

### 2. Already Implemented — Do Not Rewrite

| File | What exists |
|------|-------------|
| `pipeline/state.py` | `PipelineState` + `SolverResult` TypedDicts — complete |
| `pipeline/type2/type2_classifier.py` | `PhysicsClassifier.classify_physics()` + `PhysicsQuestionType` enum — complete |
| `pipeline/type2/type2_validation.py` | `validate_sympy_result()` + `validate_multi_target_hint()` — complete |
| `tests/physics_formula.py` | Validator script — keep as standalone CLI, refactor to `if __name__ == "__main__"`, import `load_formula_db()` from `formula_rag.py` |

---

### 3. Component Specifications

#### 3.1 PhysicsParser — `pipeline/type2/physics_parser.py` — ✅ ĐÃ HOÀN THÀNH (2026-06-02; + regex pre-pass)

**Responsibility:** Extract structured data from raw physics question text via LLM.

**Input:** `state["question"]: str`

**Output** (written to `state["parsed_physics"]`):
```python
{
    "given": {"V": 10.0, "I": 2.0},    # known variables with numeric values
    "find": "R",                         # target symbol — matches PhysicsClassifier.target_variable
    "domain": "circuits",                # "circuits" | "electrostatics"
    "formulas": ["V = I * R"],           # LLM-proposed hints, refined by FormulaRAG
    "units": {"V": "V", "I": "A"}       # units of given values (for unit conversion)
}
```

**Integration with PhysicsClassifier:** Call `PhysicsClassifier.classify_physics(question)` first. Use `domain` and `target_variable` as structured priors before LLM call — reduces hallucination.

**LLM call:** Delegate to `LLMReasoner.parse_physics_question(question)` — already implemented in `llm/llm_reasoner.py`. PhysicsParser node is a thin wrapper:

```python
def physics_parser_node(state: PipelineState) -> PipelineState:
    reasoner = get_shared_reasoner()
    classified = PhysicsClassifier().classify_physics(state["question"])
    parsed = reasoner.parse_physics_question(state["question"])
    # Override domain/find from classifier if LLM missed them
    if not parsed["find"] and classified.target_variable:
        parsed["find"] = classified.target_variable
    if parsed["domain"] == "general":
        parsed["domain"] = classified.domain
    parsed["question_type"] = classified.question_type.value
    return {**state, "parsed_physics": parsed}
```

**Fallback:** Handled inside `parse_physics_question()` — retries once with simplified prompt. On total failure returns `{"given": {}, "find": "", "domain": "general", "formulas": [], "units": {}}`. Set `confidence = 0.3` in node wrapper when `find == ""`.

**Error contract:** Wrap in `try/except`. Never raise — always return dict.

---

#### 3.2 FormulaRAG — `pipeline/type2/formula_rag.py` *(new file)* — ✅ ĐÃ HOÀN THÀNH

**Responsibility:** Retrieve the correct `formula_sympy` string from knowledge base. Two responsibilities: (1) build/load index; (2) query at inference time.

##### `load_formula_db(path)` — called at startup

Reads `data/rag/physics_formulas.json`, validates each `formula_sympy` with `sympify()`, returns only valid entries. This is the production version of the logic in `tests/physics_formula.py`.

```python
def load_formula_db(path: str = "data/rag/physics_formulas.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        docs = json.load(f)
    valid = []
    for doc in docs:
        try:
            sympify(doc["formula_sympy"].split("=")[-1].strip())
            valid.append(doc)
        except Exception:
            logger.warning(f"Invalid formula_sympy in {doc['id']}, skipping")
    return valid
```

##### Build FAISS index — `scripts/build_faiss_index.py` (one-time script)

```python
from sentence_transformers import SentenceTransformer
import faiss, pickle, numpy as np

def build_formula_index(docs: list[dict], save_dir: str = "data/formula_index"):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [
        f"{d['domain']}: {d['formula_natural']} — {' '.join(d['keywords'])}"
        for d in docs
    ]
    embeddings = model.encode(texts).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, f"{save_dir}/index.faiss")
    with open(f"{save_dir}/metadata.pkl", "wb") as f:
        pickle.dump(docs, f)
```

Run: `python scripts/build_faiss_index.py` — output saved to `data/formula_index/`.

##### `retrieve_formula(parsed, docs, index, model)` — Hybrid Retrieval

Two-layer strategy: fast exact match first, FAISS only on ambiguity or miss.

```
Layer 1 — Keyword/exact match (deterministic):
    filter docs where doc["domain"] == parsed["domain"]
                  AND parsed["find"] in doc["variables"]
    → if exactly 1 candidate → return immediately, skip FAISS

Layer 2 — FAISS semantic search (only if Layer 1 returns 0 or 2+ candidates):
    search_pool = candidates (if any) else all docs
    query = f"{domain} {find} {question}"
    embed → search top-k → return best match
```

**Fallback:** FAISS index not found or query exception → return `parsed_physics["formulas"]` as-is. Log `formula_rag_failed=True`.

**No LangChain** — call FAISS and sentence-transformers directly. LangChain abstraction is overkill for ~100 documents.

---

#### 3.3 SympySolver — `pipeline/type2/sympy_solver.py` — ✅ ĐÃ HOÀN THÀNH (full dispatch 2026-06-02: 4-type + ELECTROMAGNETIC→MULTI_STEP alias + YES_NO→resonance_solver + ERROR_CALC/MULTI_ANSWER→error_solver + vector fallback)

**Responsibility:** Solve physics equation symbolically. Zero arithmetic hallucination.

**Input:** `state["parsed_physics"]` (with `given`, `find`, `formulas`, `units`)

**Dispatch by `PhysicsQuestionType`** (from `type2_classifier`):

| Type | Strategy |
|------|----------|
| `SINGLE_FORMULA` | Parse 1 formula → substitute knowns → `solve()` for target |
| `MULTI_STEP` | Chain formulas sequentially — step N output feeds step N+1 as known |
| `CIRCUIT` | Build KVL/KCL equation system → `linsolve()` |
| `ELECTROSTATIC` | Match Coulomb / capacitance formula → `solve()` |

**Core skeleton:**
```python
from sympy import symbols, Eq, solve, sympify
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def solve_physics(parsed: dict, q_type: PhysicsQuestionType, timeout: int = 10) -> dict:
    """
    1. Declare SymPy symbols for all variables in formula
    2. Parse formula string → SymPy Eq via sympify
    3. Substitute known values from parsed["given"] (with unit conversion)
    4. Solve for parsed["find"]
    5. Return {answer, unit, steps, source}
    """
```

**Timeout:** `concurrent.futures.ThreadPoolExecutor` with `timeout` parameter (works on Windows; `signal.SIGALRM` Linux-only).

**Multi-formula:** If `formulas` has multiple entries, try each in order. First successful solve wins. Log which formula solved it.

**Output** (written to `state["sympy_result"]`):
```python
{
    "answer": "5.0",
    "unit": "Ω",
    "steps": [
        "Given: V=10V, I=2A",
        "Formula: V = I * R",
        "Substitute: 10 = 2 * R",
        "Solve: R = 10/2",
        "Result: R = 5.0 Ω"
    ],
    "raw_expr": "R = V/I",
    "source": "sympy"
}
```

**Fallback (timeout or solve failure):** `{"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}`, `confidence = 0.5`.

---

#### 3.4 SelfVerifier — wraps `pipeline/type2/type2_validation.py` — ✅ ĐÃ HOÀN THÀNH (inline trong `api/main.py`)

**Do NOT create `self_verifier.py`.** Logic already exists:
- `validate_sympy_result(value, target_variable)` → `ValidationResult`
- `validate_multi_target_hint(question)` → `bool`

SelfVerifier node in LangGraph is a thin wrapper:

```python
def self_verifier_node(state: PipelineState) -> PipelineState:
    sympy_result = state.get("sympy_result", {})
    parsed = state.get("parsed_physics", {})
    val = validate_sympy_result(
        value=sympy_result.get("answer"),
        target_variable=parsed.get("find"),
    )
    confidence = state.get("confidence", 1.0)
    if not val.is_valid:
        confidence = 0.4
        logger.warning(f"self_verify_failed: {val.errors}")
    for w in val.warnings:
        logger.info(f"self_verify_warning: {w}")
    return {**state, "confidence": confidence}
```

**Confidence rules:**
- `is_valid=True` → `confidence` unchanged
- `is_valid=False` → `confidence = 0.4`, log `self_verify_failed=True`
- Exception inside validate → `confidence` unchanged, log `self_verify_skipped=True`

**Never blocks pipeline.**

---

#### 3.5 CotBuilder — `pipeline/type2/cot_builder.py` — ✅ ĐÃ HOÀN THÀNH

**Responsibility:** Format `sympy_result["steps"]` into `cot: list[str]` for API response.

**No LLM call** — pure string formatting. Fast, deterministic, no failure mode.

**Output format:**
```python
[
    "Step 1 — Identify known quantities: V = 10V, I = 2A",
    "Step 2 — Select formula: Ohm's Law — V = I × R",
    "Step 3 — Substitute values: 10 = 2 × R",
    "Step 4 — Solve for R: R = 10 ÷ 2 = 5",
    "Step 5 — Result: R = 5.0 Ω"
]
```

**Fallback (empty solver steps):** Build minimal CoT from `parsed_physics`:
```python
["Given: ...", "Find: ...", "Unable to complete calculation — see explanation"]
```

---

#### 3.6 ExplainerAgent — `pipeline/type2/explainer.py` — ✅ ĐÃ HOÀN THÀNH

**Shared with Track 1** — receives `SolverResult` struct only. No track-specific logic here.

**LLM call:** Delegate to `LLMReasoner.explain_physics(question, answer, unit, steps)` — already implemented in `llm/llm_reasoner.py`. Node wrapper:

```python
def explainer_node_type2(state: PipelineState) -> PipelineState:
    reasoner = get_shared_reasoner()
    sr = state["solver_result"]
    explanation = reasoner.explain_physics(
        question=state["question"],
        answer=sr["answer"],
        unit=sr.get("unit", ""),
        steps=sr.get("steps", []),
    )
    return {**state, "explanation": explanation}
```

**Fallback:** Handled inside `explain_physics()` — retries once, then hardcoded `f"The answer is {answer} {unit}."`. Prompt template: `PHYSICS_EXPLANATION_PROMPT` in `llm/prompt_templates.py`.

---

#### 3.7 ResonanceSolver — `pipeline/type2/resonance_solver.py` *(new file — CHLT)* — ✅ ĐÃ HOÀN THÀNH (2026-06-02)

**Responsibility:** Answer Yes/No resonance questions for the **CHLT** prefix (20 problems, 100% gap). These do **not** use FormulaRAG or `sympy.solve()` — pure value comparison.

**Why a separate solver:** CHLT asks "does the circuit experience resonance?" → compute resonant frequency `f₀ = 1/(2π√(LC))` and compare to the driving frequency `f`. No equation to solve, no formula to retrieve.

**Trigger:** `PhysicsQuestionType.YES_NO` (already in enum). Dispatched from `sympy_solver_node` (see Integration below).

**⚠️ Note về R trong đề CHLT:** Dữ liệu thực tế cho thấy **tất cả** câu YES/NO resonance đều có R trong đề (ví dụ: `R = 45 Ω`, `R = 60 Ω`). Tuy nhiên:
- **R không dùng để kiểm tra cộng hưởng** — `f₀ = 1/(2π√(LC))` chỉ phụ thuộc L và C. Ở cộng hưởng, `X_L = X_C` → trở kháng thuần trở `Z = R`, nhưng câu hỏi Yes/No chỉ hỏi "có cộng hưởng không".
- **Parser phải extract R** (regex sẽ tự bắt được) — nhưng `solve_resonance()` **bỏ qua R** cho phép kiểm tra Yes/No.
- Nếu câu hỏi hỏi thêm về power (`P = U²/R`) hay impedance (`Z = R` tại cộng hưởng), đó là loại câu khác (SINGLE_FORMULA), không phải YES_NO.

**Entry point** — same `sympy_result` contract as other solvers:
```python
def solve_resonance(parsed: dict, question: str = "") -> dict:
    """
    Input  : parsed["given"] must contain L (H), C (F), f (Hz).
             R may also be present — intentionally ignored for Yes/No check.
    Output : {"answer": "Yes"|"No", "unit": "", "steps": [...], "source": "resonance"}
    Logic  : f0 = 1 / (2*pi*sqrt(L*C));  Yes if abs(f - f0)/f0 < TOL else No.
             TOL ~ 0.01–0.02 (relative). Tune against CHLT examples in track2_data_info.md.
    """
```

**Output example:**
```python
{
    "answer": "No",
    "unit": "",
    "steps": [
        "Given: R=60 Ω, L=0.8 H, C=5 µF, f=50 Hz",
        "Resonant frequency: f0 = 1/(2π√(LC)) = 1/(2π√(0.8×5e-6)) ≈ 79.6 Hz",
        "Compare: |50 − 79.6|/79.6 = 0.37 > 0.01 → not resonant",
        "Note: R is given but not used for resonance check (Z=R only at resonance)",
    ],
    "source": "resonance",
}
```

**Confidence:** deterministic → `1.0` (treat `"resonance"` like `"sympy"` in the confidence map).

**Fallback:** missing L/C/f after parse → `{"answer": "", "unit": "", "steps": [], "source": "llm_fallback"}` (lets LLM CoT handle it). Never raise.

**Parsing note:** CHLT `given` extraction can reuse the regex helpers in `scripts/demo_type2.py` (`_normalize_superscripts`, unit conversion) or a small local regex. Does **not** depend on the LLM parser.

---

#### 3.8 ErrorSolver — `pipeline/type2/error_solver.py` *(new file — THCB)* — ✅ ĐÃ HOÀN THÀNH (2026-06-06; error propagation F-045/046 implement: product/quotient δZ=ΣδAᵢ, sum/diff ΔZ=ΣΔAᵢ — THCB003/005/008/009 ✓)

**Responsibility:** Measurement-error problems for the **THCB** prefix (80 problems, 100% gap). Explicit formula computation — **no `sympy.solve()`**. Largest multi-answer group (23/80 use `;`).

**Trigger:** `PhysicsQuestionType.ERROR_CALC` (single value) and `PhysicsQuestionType.MULTI_ANSWER` (≥2 values). Both already in enum.

**Sub-cases** (detect from question keywords; formulas per `track2_formula_gaps.md` F-043…F-048):

| Sub-case | Formula | Example IDs |
|----------|---------|-------------|
| absolute error (instrument) | `Δx = least_count / 2` (or given directly) | THCB001 |
| relative error | `δ = Δx / x * 100` (%) | THCB002 |
| error propagation — product/quotient | `δZ = δA + δB` (Z=A·B or A/B) | THCB003 |
| error propagation — sum/diff | `ΔZ = ΔA + ΔB` (Z=A±B) | THCB009 |
| mean + random error | `x̄ = Σxᵢ/n`, `Δx̄ = Σ|xᵢ−x̄|/n` | THCB007 |
| absolute error from true value | `Δx = |x_measured − x_true|` | THCB087 |

**Entry point:**
```python
def solve_error(parsed: dict, question: str = "") -> dict:
    """
    Output (single) : {"answer": "3.57", "unit": "%", "steps": [...], "source": "error_calc"}
    Output (multi)  : {"answer": "0.6; 1.2", "unit": "cm; %", "steps": [...], "source": "error_calc"}
    """
```

**Multi-answer format (critical):** when the question asks for ≥2 quantities ("calculate absolute error AND relative error"), join with `"; "` in BOTH `answer` and `unit`, in the same order. Matches dataset convention (`Answer: 0.6; 1.2 | Unit: cm; %`).

**Confidence:** deterministic → `1.0`.

**Fallback:** unrecognized sub-case or missing data → `source="llm_fallback"`. Never raise.

---

### 4. SolverResult — Unified Interface

Before handing off to Explainer, SympySolver must populate:

```python
SolverResult(
    answer=str(sympy_result["answer"]),
    unit=sympy_result.get("unit"),
    steps=sympy_result.get("steps", []),
    fol=None,                           # Type 2 has no FOL
    source=sympy_result.get("source"),  # "sympy" | "llm_fallback"
    confidence=state["confidence"],
)
```

`source` → `confidence` baseline:
- `"sympy"` + self_verify OK → `1.0`
- `"sympy"` + self_verify failed → `0.4`
- `"resonance"` (CHLT) / `"error_calc"` (THCB) → `1.0` (deterministic, treat like `"sympy"`)
- `"llm_fallback"` → `0.5`

**Integration — dispatch in `sympy_solver_node`** (the only edit to existing solver code; one branch, ~6 lines):
```python
# pipeline/type2/sympy_solver.py — inside sympy_solver_node, before solve_physics()
#
# ⚠️ Guard: YES_NO phải kết hợp domain + given-key check trước khi gọi resonance_solver.
# Lý do: classifier có thể nhầm câu qualitative ("What is the circuit's characteristic?")
# vào YES_NO. Nếu dispatch thẳng, resonance_solver trả answer="" vì thiếu L/C/f.
# Safety gate tại đây rõ hơn là chỉ dựa vào fallback bên trong solver.
given = parsed.get("given", {})
if (q_type == PhysicsQuestionType.YES_NO
        and parsed.get("domain") == "ac_circuits"
        and all(k in given for k in ("L", "C", "f"))):
    from pipeline.type2.resonance_solver import solve_resonance
    sympy_result = solve_resonance(parsed, state.get("question", ""))
elif q_type in (PhysicsQuestionType.ERROR_CALC, PhysicsQuestionType.MULTI_ANSWER):
    from pipeline.type2.error_solver import solve_error
    sympy_result = solve_error(parsed, state.get("question", ""))
else:
    sympy_result = solve_physics(parsed, q_type)   # existing path
# existing vector_solver + llm_fallback handling continues unchanged
```
Self-verifier downgrades confidence only for numeric answers; Yes/No and multi-answer strings skip numeric validation (extend `validate_sympy_result` if needed, but do not block).

---

### 5. Implementation Tasks

#### Phase 1 — Core pipeline (ship before eval) ✅ ĐÃ HOÀN THÀNH TOÀN BỘ (T2-00…T2-09, 2026-06-02)

| Task | File | Note |
|------|------|------|
| T2-00: Build FAISS index | `scripts/build_faiss_index.py` | Prerequisite for FormulaRAG |
| T2-01: `load_formula_db()` + hybrid `retrieve_formula()` | `pipeline/type2/formula_rag.py` | Layer 1 keyword + Layer 2 FAISS |
| T2-02: `PhysicsParser` node wrapper (LLM call via `llm_reasoner.parse_physics_question()`) | `pipeline/type2/physics_parser.py` | LLM logic already in llm_reasoner |
| T2-03: `SympySolver.solve()` with 4-type dispatch + timeout | `pipeline/type2/sympy_solver.py` | ThreadPoolExecutor timeout |
| T2-04: `CotBuilder.build()` pure formatter | `pipeline/type2/cot_builder.py` | No LLM |
| T2-05: `ExplainerAgent` node wrapper (LLM call via `llm_reasoner.explain_physics()`) | `pipeline/type2/explainer.py` | LLM logic already in llm_reasoner |
| T2-06: SelfVerifier node wrapper | thin function in orchestration layer | Wraps type2_validation.py |
| T2-07: Wire LangGraph nodes for Track 2 | `api/main.py` | physics_parser→formula_rag→sympy_solver→self_verifier→cot_builder→explainer |
| T2-08: Refactor `tests/physics_formula.py` | `tests/physics_formula.py` | Add `main()`, import `load_formula_db` from formula_rag |
| T2-09: `tests/test_type2.py` — 3 circuit + 2 electrostatics | `tests/test_type2.py` | See Section 6 |

#### Phase 2 — Optional enhancements (only if time allows)

| Task | Description |
|------|-------------|
| T2-10: LLM-only fallback CoT path | When SymPy times out, LLM calculates directly with physics CoT prompt |
| T2-11: Code Agent node | LLM generates SymPy code, execute in `subprocess` sandbox with 10s timeout |
| T2-12: Populate FAISS from competition source materials | Post kick-off workshop, replace seed data |
| T2-13: QLoRA fine-tune PhysicsParser | Only if variable extraction accuracy < 70% on eval set |

#### Phase 3 — Dedicated solvers for non-RAG prefixes (CHLT + THCB) — independent work package ✅ ĐÃ HOÀN THÀNH (T2-14…T2-17, 2026-06-02; E2E verified conf=1.0)

These two prefixes do **not** use FormulaRAG/`solve()`, so they can be built in parallel with the formula-DB expansion (which covers CH/DDT/NL/LD/DT/TD). Clean boundary: two new files + one dispatch branch in `sympy_solver_node`.

| Task | File | Note |
|------|------|------|
| T2-14: `solve_resonance()` — CHLT Yes/No | `pipeline/type2/resonance_solver.py` *(new)* | §3.7. `f₀=1/(2π√(LC))`, relative-tol compare. 20 problems. |
| T2-15: `solve_error()` — THCB error calc + multi-answer | `pipeline/type2/error_solver.py` *(new)* | §3.8. Sub-cases F-043…F-048, `;`-joined multi-answer. 80 problems. |
| T2-16: Dispatch branch (YES_NO / ERROR_CALC / MULTI_ANSWER) | `pipeline/type2/sympy_solver.py` | §4 Integration snippet — ~6 lines, before `solve_physics()`. |
| T2-17: Tests — CHLT (Yes + No cases) + THCB (single + multi-answer) | `tests/test_type2.py` | ≥4 cases. Use CHLT001/002 + THCB002/087 from track2_data_info.md. |

**Enum/domain already done** (commit 2026-05-31): `YES_NO`, `ERROR_CALC`, `MULTI_ANSWER` types and `measurement` domain exist in `type2_classifier.py` — the owner only consumes them, does not edit the classifier.

---

### 6. Fallback Decision Tree

```
PhysicsParser
    ├─ JSON OK → parsed_physics populated → continue
    └─ JSON fail (2 retries) → minimal struct, confidence=0.3
                               → FormulaRAG skips to LLM-proposed formulas

FormulaRAG (Hybrid)
    ├─ Layer 1 keyword hit (1 match) → verified formula → SympySolver
    ├─ Layer 1 ambiguous (2+ matches) → Layer 2 FAISS disambiguates → SympySolver
    ├─ Layer 1 miss → Layer 2 FAISS full search → SympySolver
    └─ FAISS fail → use LLM-proposed formulas from physics_parser → SympySolver

SympySolver
    ├─ Solve OK → self_verifier → cot_builder → explainer
    ├─ Timeout (>10s) → source="llm_fallback", confidence=0.5 → cot_builder(empty) → explainer
    └─ Exception → same as timeout

SelfVerifier (type2_validation)
    ├─ is_valid=True → confidence unchanged
    ├─ is_valid=False → confidence=0.4, log warning
    └─ Exception → skip, confidence unchanged

Explainer
    ├─ LLM OK → explanation str
    ├─ Fail once → retry simplified
    └─ Fail twice → f"The answer is {answer} {unit}.", confidence=0.3
```

---

### 7. Test Cases

```python
# Circuit — Ohm's Law
{
    "question": "A circuit has voltage 12V and resistance 4Ω. Calculate the current.",
    "expected_answer": "3.0",
    "expected_unit": "A"
}

# Circuit — Parallel resistance
{
    "question": "Two resistors R1=6Ω and R2=3Ω are connected in parallel. Find total resistance.",
    "expected_answer": "2.0",
    "expected_unit": "Ω"
}

# Circuit — Power (MULTI_STEP: I from V/R, then P=I²R)
{
    "question": "A resistor has resistance 5Ω and carries current 2A. Calculate power dissipated.",
    "expected_answer": "20.0",
    "expected_unit": "W"
}

# Electrostatics — Capacitor energy
{
    "question": "A capacitor with capacitance 4F is charged to 3V. Find the energy stored.",
    "expected_answer": "18.0",
    "expected_unit": "J"
}

# Fallback test — ambiguous question, must not crash
{
    "question": "What happens when voltage increases in a circuit?",
    "assert": "response has answer and explanation, confidence > 0, no exception"
}
```

Each test asserts:
1. Response has `answer` and `explanation` (required fields — Dev Rule #3)
2. No unhandled exception
3. `confidence > 0`
4. Numeric answer within 1e-6 tolerance for deterministic cases

---

### 8. Logging Checklist

Every Type 2 request must log these fields:

```json
{
    "query_type": "type2",
    "physics_domain": "circuits",
    "physics_question_type": "single_formula",
    "formula_rag_layer": "keyword",
    "formula_rag_failed": false,
    "sympy_timeout": false,
    "self_verify_result": "ok",
    "solver_source": "sympy",
    "fallback_triggered": false,
    "confidence": 1.0
}
```

---

### 9. File Ownership

| File | Status | Owner |
|------|--------|-------|
| `pipeline/state.py` | **complete** — do not modify | shared |
| `pipeline/type2/type2_classifier.py` | **complete** — do not modify | shared |
| `pipeline/type2/type2_validation.py` | **complete** — do not modify | shared |
| `llm/llm_reasoner.py` | **Track 2 methods added** — `parse_physics_question()`, `explain_physics()` | shared |
| `llm/prompt_templates.py` | **Track 2 templates added** — `PHYSICS_PARSE_PROMPT`, `PHYSICS_EXPLANATION_PROMPT` | shared |
| `llm/inference.py` | **not needed** — logic merged into `llm_reasoner.py` | — |
| `pipeline/type2/physics_parser.py` | stub → implement (calls `llm_reasoner.parse_physics_question()`) | Member 2 |
| `pipeline/type2/formula_rag.py` | new file | Member 2 |
| `pipeline/type2/sympy_solver.py` | stub → implement | Member 2 |
| `pipeline/type2/cot_builder.py` | stub → implement | Member 2 |
| `pipeline/type2/explainer.py` | stub → implement (calls `llm_reasoner.explain_physics()`) | Member 2 |
| `scripts/build_faiss_index.py` | new file | Member 2 |
| `tests/physics_formula.py` | refactor to script with `main()` | Member 2 |
| `tests/test_type2.py` | expand stubs | Member 2 |
| `pipeline/type2/resonance_solver.py` | **new file (CHLT)** — T2-14 | Member 3 |
| `pipeline/type2/error_solver.py` | **new file (THCB)** — T2-15 | Member 3 |
| `pipeline/type2/sympy_solver.py` | **dispatch branch only** — T2-16 (coordinate with solver owner) | Member 3 |

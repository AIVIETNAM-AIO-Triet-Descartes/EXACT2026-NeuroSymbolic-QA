# Track 2 — Physics Dataset Analysis
> **File:** `Physics_Problems_Text_Only.csv`  
> **Mục đích:** SSOT mô tả cấu trúc, phân loại, và các đặc điểm kỹ thuật của dataset Type 2 — phục vụ thiết kế `physics_formulas.json`, `PhysicsClassifier`, `SympySolver`, và routing logic.

---

## 1. Tổng quan

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

## 2. Phân loại theo Prefix ID

### 2.1 LD — Lực Coulomb & Điện trường (397 bài, 29.4%)

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

### 2.2 CH — Mạch RLC xoay chiều (290 bài, 21.4%)

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

### 2.3 NL — Năng lượng điện từ (190 bài, 14.1%)

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

### 2.4 TD — Tụ điện cơ bản (177 bài, 13.1%)

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

### 2.5 DDT — Điện từ cảm ứng (130 bài, 9.6%)

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

### 2.6 THCB — Sai số đo lường (80 bài, 5.9%) ⚠️ Ngoài dự kiến

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

### 2.7 DT — Điện trường tại điểm (68 bài, 5.0%)

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

### 2.8 CHLT — Cộng hưởng RLC Yes/No (20 bài, 1.5%)

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

## 3. Ma trận tổng hợp

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

## 4. Danh sách đơn vị (units) trong dataset

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

## 5. Tác động đến Implementation

### 5.1 Routing cần bổ sung

```python
# Hiện tại (SYSTEM.md) chỉ có:
PHYSICS_KEYWORDS = {"calculate", "resistance", "voltage", ...}

# Cần thêm keywords cho các nhóm mới:
COULOMB_KEYWORDS = {"charge", "coulomb", "electric force", "q1", "q2", "placed at"}
INDUCTION_KEYWORDS = {"solenoid", "flux", "induced", "emf", "faraday", "self-inductance"}
ERROR_KEYWORDS = {"absolute error", "relative error", "least count", "uncertainty", "measured"}
RESONANCE_KEYWORDS = {"resonance", "resonant", "does the circuit experience"}
```

### 5.2 Answer-type detection

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

### 5.3 Vector solving (LD + DT — 257 bài)

SymPy cần module riêng cho vector:

```python
from sympy.vector import CoordSys3D
# Hoặc đơn giản hơn: dùng sympy.sqrt và sympy.atan2
# F_net = sqrt(F1x + F2x)² + (F1y + F2y)²)
```

Cần xác định hình học (tam giác, góc α) từ CoT — đây là phần phức tạp nhất.

### 5.4 Multi-answer format

Khi `answer` chứa `;`, response API cần format:
```json
{
  "answer": "0.6 cm; 1.2%",
  "explanation": "Absolute error = 0.6 cm. Relative error = 1.2%.",
  "cot": ["Step 1: ...", "Step 2: ..."]
}
```

### 5.5 Công thức cần có trong `physics_formulas.json`

| Nhóm | Công thức ưu tiên |
|------|------------------|
| LD/DT | Coulomb, E-field, vector superposition |
| CH | Z = √(R²+(XL-XC)²), XL=ωL, XC=1/ωC, P=UI·cosφ, cosφ=R/Z |
| NL | WC=½CU², WL=½LI², Q=C·U |
| TD | Q=C·U, W=½CU²=Q²/2C, C=ε·S/d |
| DDT | B=μ₀·n·I, EMF=ΔΦ/Δt, L=μ₀·n²·V, w=B²/2μ₀ |
| THCB | ΔR/R=ΔU/U+ΔI/I, Δ(A+B)=ΔA+ΔB, δ=Δx/x·100% |
| CHLT | f₀=1/(2π√(LC)), condition: f == f₀ |

### 5.6 PhysicsQuestionType — cần mở rộng enum

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

## 6. Mức độ khó theo nhóm (để ưu tiên implement)

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
